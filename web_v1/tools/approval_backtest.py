"""Read-only historical evaluation of the production amount fallback.

Consumes a previously exported invoice/log/PDF-identity snapshot; never opens the
operational database, writes approval associations, prints, or submits ERP jobs.
Only the search date window is adapted. Candidate parsing and decisions are the
unchanged production functions. Ground truth is used only after deciding.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit


def manual_events(record: dict) -> list[dict]:
    return [event for event in record["logs"]
            if re.match(r"품의결재본 (교체|첨부):", event["message"])]


def historical_anchor(record: dict) -> tuple[str, str]:
    """Choose the earliest actual lookup/upload, independently of its result."""
    events = manual_events(record) + [event for event in record["logs"]
        if re.match(r"(?:품의결재본 백그라운드|전자결재 품의) 자동 확보 시작", event["message"])]
    if not events:
        raise ValueError("Historical lookup/upload timestamp unavailable")
    event = min(events, key=lambda value: value["created_at"])
    return event["created_at"][:10], event["message"]


def truth_numbers(record: dict, overrides: dict) -> list[str]:
    explicit = overrides.get(str(record["invoice"]["id"]))
    if explicit:
        return explicit["doc_nos"]
    # The header document number precedes any related-document references.
    numbers = [item["doc_nos"][0] for item in record["files"] if item.get("doc_nos")]
    if len(numbers) != len(record["files"]):
        raise ValueError("A stored approval PDF has no verified document number")
    return list(dict.fromkeys(numbers))


def classify(result: dict, truth: list[str]) -> str:
    if result["status"] == "error":
        return "error"
    if result["status"] == "matched":
        return "auto_correct" if result["selected"]["doc_no"] in truth else "auto_wrong"
    if any(candidate["doc_no"] in truth for candidate in result.get("candidates", [])):
        return "review_correct_candidate"
    return "not_recovered"


def summary(results: list[dict]) -> dict:
    labels = ("auto_correct", "auto_wrong", "review_correct_candidate", "not_recovered", "error")
    counts = {label: sum(row["classification"] == label for row in results) for label in labels}
    n = len(results)
    return {"n": n, **counts,
            "auto_correct_percent": round(100 * counts["auto_correct"] / n, 2) if n else None,
            "recovered_percent": round(100 * (counts["auto_correct"] + counts["review_correct_candidate"]) / n, 2) if n else None}


async def historical_search(page, template: str, amount: str, anchor: str,
                            wait_search_result, max_results: int) -> tuple[list, bool]:
    """Replay the observed search URL with only amount/date/pagination changed."""
    base = urlsplit(template)
    if base.scheme != "https" or base.netloc != "gw.dae-seung.co.kr" or base.path != "/app/approval/search":
        raise ValueError("Unexpected search URL")
    params = parse_qs(base.query, keep_blank_values=True)
    if params.get("dateType") != ["completedAt"] or params.get("searchOption") != ["AND"]:
        raise ValueError("Search template is not completion-date body search")
    for field in ("title", "attachFileNames", "attachFileContents", "drafterName", "docNum"):
        if params.get(field) not in (None, [""]):
            raise ValueError("Unexpected extra search filter: " + field)
    from web_v1.backend.approval_matching import approval_date_range
    start, end = approval_date_range(anchor)
    params.update(docBody=[amount], fromDate=[f"{start}T00:00:00.000+09:00"],
                  toDate=[f"{end}T23:59:59.000+09:00"], searchTerm=["specify"])
    rows, expected_total = [], None
    for page_no in range(5):
        params["page"] = [str(page_no)]
        url = urlunsplit((base.scheme, base.netloc, base.path, urlencode(params, doseq=True), ""))
        async with page.expect_response(lambda response: urlsplit(response.url).path == "/api/search/approval", timeout=20000) as info:
            await page.goto(url, wait_until="domcontentloaded")
        total, _ = await wait_search_result(page, await info.value)
        if expected_total is not None and total != expected_total:
            raise RuntimeError("Search results changed while paginating")
        expected_total = total
        entries = page.locator("table.type_normal tbody tr")
        count = await entries.count()
        for index in range(count):
            row = entries.nth(index)
            async def text(selector):
                node = row.locator(selector).first
                return (await node.inner_text()).strip() if await node.count() else ""
            doc_no = await text("td.doc_num")
            if doc_no:
                rows.append({"doc_no": doc_no, "title": await text("td.subject"),
                    "form_name": await text("td.division"), "drafter_name": await text("td.writer"),
                    "approved_date": await text("td.date:last-child"), "status": await text("td.state_wrap"),
                    "result_url": page.url})
        if len(rows) >= total or count == 0 or len(rows) >= max_results:
            break
    return rows, len(rows) < expected_total


async def run(args) -> dict:
    root = args.source_root.resolve()
    os.chdir(root)
    sys.path.insert(0, str(root))
    from playwright.async_api import async_playwright
    from web_v1.backend import approval_browser as browser_code
    from web_v1.backend import approval_matching as matching
    from web_v1.backend.erp_runner import _load_legacy_module
    from web_v1.backend.config import settings

    records = json.loads(args.snapshot.read_text(encoding="utf-8"))
    cohort = [record for record in records if manual_events(record)]
    overrides = json.loads(args.truth_overrides.read_text(encoding="utf-8"))
    template = json.loads(args.search_template.read_text(encoding="utf-8"))["url"]
    # Freeze all identities and anchors before retrieving groupware candidates.
    cases = []
    for record in cohort:
        anchor, anchor_reason = historical_anchor(record)
        context = matching.invoice_context({**record["invoice"], "raw": record["raw"]}, anchor)
        matching.validate_context(context)
        cases.append({"id": context["invoice_id"], "context": context,
                      "anchor_reason": anchor_reason, "truth": truth_numbers(record, overrides)})
    legacy = _load_legacy_module()
    accounts = {value.strip().lower() for value in settings.approval_drafter_accounts.split(",") if value.strip()}
    manifest = {"cohort": "all explicit manual-upload records with current approval PDFs",
                "mode": "amount fallback only (simulate missing filename order number)",
                "anchor": f"earliest logged approval lookup or manual upload; inclusive anchor-{matching.APPROVAL_LOOKBACK_DAYS}d..anchor",
                "input_sha256": hashlib.sha256(args.snapshot.read_bytes()).hexdigest(),
                "source_sha256": {name: hashlib.sha256((root / "web_v1/backend" / name).read_bytes()).hexdigest()
                                  for name in ("approval_browser.py", "approval_matching.py")},
                "accounts": sorted(accounts), "cases": cases}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    results = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        page.set_default_timeout(12000)
        await browser_code.login(page, {"username": legacy.APPROVAL_DEFAULT_USER, "password": legacy.APPROVAL_DEFAULT_PASSWORD})
        try:
            for case in cases:
                context = case["context"]
                entry = {"id": case["id"], "reference_date": context["reference_date"],
                         "total": context["total"], "site": context["site"], "truth": case["truth"]}
                try:
                    rows_by_number, truncated = {}, False
                    for amount in matching.amount_variants(context["total"]):
                        rows, limited = await historical_search(page, template, amount, context["reference_date"],
                                                               browser_code.wait_search_result, browser_code.MAX_RESULTS)
                        truncated |= limited
                        rows_by_number.update({row["doc_no"]: row for row in rows})
                    candidates = []
                    start, end = matching.approval_date_range(context["reference_date"])
                    for row in rows_by_number.values():
                        try:
                            approved = date.fromisoformat(row["approved_date"])
                        except ValueError:
                            continue
                        if row["status"] == "완료" and start <= approved <= end:
                            candidates.append(await browser_code.candidate_detail(page, row))
                    decision = matching.decide(candidates, context, accounts, truncated=truncated)
                    # Save no body, credentials, bank details or profile personal data.
                    entry["result"] = {**decision,
                        "candidates": [matching.public_candidate(c) for c in decision["candidates"]],
                        "searched_count": len(rows_by_number), "truncated": truncated}
                    if decision.get("selected"):
                        entry["result"]["selected"] = matching.public_candidate(decision["selected"])
                    entry["assessed"] = [{**matching.public_candidate(c), "blocked": c["blocked"], "eligible": c["eligible"]}
                        for c in (matching.assess_candidate(candidate, context, accounts) for candidate in candidates)]
                    entry["search_rows"] = [{k: v for k, v in row.items() if k != "result_url"} for row in rows_by_number.values()]
                except Exception as exc:
                    entry["result"] = {"status": "error", "error_type": type(exc).__name__}
                    # Full exception can include DOM snippets. Keep a private local trace.
                    import traceback
                    (args.output / f"error_{case['id']}.txt").write_text(traceback.format_exc(), encoding="utf-8")
                entry["classification"] = classify(entry["result"], entry["truth"])
                results.append(entry)
                payload = {"summary": summary(results), "results": results}
                (args.output / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps({"id": entry["id"], "classification": entry["classification"],
                                  "completed": len(results), "total": len(cases)}), flush=True)
                await asyncio.sleep(0.5)
        finally:
            await browser.close()
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-root", "snapshot", "truth-overrides", "search-template", "output"):
        parser.add_argument("--" + name, type=lambda value: Path(value).resolve(), required=True)
    print(json.dumps(asyncio.run(run(parser.parse_args()))["summary"]))
