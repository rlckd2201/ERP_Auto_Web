"""Isolated read/search/render process for the amount-based approval fallback."""
from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from playwright.async_api import async_playwright

from .approval_matching import amount_variants, approval_date_range, decide, public_candidate, validate_context

ORIGIN = "https://gw.dae-seung.co.kr"
MAX_RESULTS = 100


def approval_search_url(url: str, reference_date: str) -> str:
    """Use exact day boundaries; the groupware 'month' shortcut is calendar-based."""
    base = urlsplit(url)
    params = parse_qs(base.query, keep_blank_values=True)
    if base.scheme + "://" + base.netloc != ORIGIN or base.path != "/app/approval/search" or params.get("dateType") != ["completedAt"]:
        raise RuntimeError("결재일 검색 조건을 확인하지 못했습니다.")
    start, end = approval_date_range(reference_date)
    params.update(fromDate=[f"{start}T00:00:00.000+09:00"], toDate=[f"{end}T23:59:59.000+09:00"],
                  searchTerm=["specify"], page=["0"])
    return urlunsplit((base.scheme, base.netloc, base.path, urlencode(params, doseq=True), ""))


async def wait_search_result(page, response) -> tuple[int, int]:
    if response.status != 200:
        raise RuntimeError("전자결재 검색 서버가 정상 응답하지 않았습니다.")
    payload = await response.json()
    total = payload.get("page", {}).get("total")
    items = payload.get("data")
    if not isinstance(total, int) or total < 0 or not isinstance(items, list):
        raise RuntimeError("전자결재 검색 결과 건수를 확인하지 못했습니다.")
    await page.wait_for_function("""([total, count]) => {
      const heading = document.querySelector('#content h1 .num strong');
      return heading && Number(heading.textContent.replace(/,/g, '')) === total &&
        document.querySelectorAll('table.type_normal tbody td.doc_num').length === count;
    }""", arg=[total, len(items)], timeout=15000)
    return total, len(items)


async def login(page, config):
    await page.goto(ORIGIN + "/login", wait_until="domcontentloaded")
    await page.locator("input#username").fill(config["username"])
    await page.locator("input#password").fill(config["password"])
    await page.locator("a#login_submit").click()
    await page.locator("nav#menu-container, li[data-menu='approval']").first.wait_for(timeout=20000)


async def body_text(page) -> str:
    texts = []
    viewers = page.locator('iframe[src="/contentViewer"]')
    if await viewers.count():
        body = page.frame_locator('iframe[src="/contentViewer"]').locator("body")
        await body.locator("p,table").first.wait_for(timeout=15000)
        texts.append(await body.inner_text())
    else:
        content = page.locator("form#document_content, .approval_import").first
        if await content.count():
            texts.append(await content.inner_text())
        else:
            texts.append(await page.locator("body").inner_text())
    return "\n".join(texts)


async def candidate_detail(page, row: dict) -> dict:
    await page.goto(row["result_url"], wait_until="domcontentloaded")
    selected = page.locator("table.type_normal tbody tr").filter(has=page.locator("td.doc_num", has_text=re.compile("^" + re.escape(row["doc_no"]) + "$")))
    await selected.first.wait_for()
    if await selected.count() != 1:
        raise RuntimeError("검색 결과의 문서번호를 유일하게 확인하지 못했습니다.")
    await selected.locator("td.subject a").click()
    await page.wait_for_url("**/approval/document/**", timeout=15000)
    match = re.search(r"/approval/document/(\d+)", page.url)
    if not match:
        raise RuntimeError("품의 문서 식별자를 확인하지 못했습니다.")
    row = {**row, "doc_id": match.group(1)}
    drafter = page.locator('.info[data-useractivitytype="DRAFT"]')
    await drafter.first.wait_for(timeout=15000)
    if await drafter.count() != 1:
        raise RuntimeError("품의 기안자를 유일하게 확인하지 못했습니다.")
    row["drafter_name"] = await drafter.get_attribute("data-username") or ""
    row["drafter_id"] = await drafter.get_attribute("data-userid") or ""
    row["body"] = await body_text(page)
    # Profile email identifies the account; names and organization-node IDs are not user IDs.
    await drafter.locator("a[data-userid]").click()
    mail = page.locator(".info_main .mail")
    await mail.wait_for(timeout=8000)
    address = (await mail.inner_text()).strip().lower()
    row["drafter_account"] = address.split("@")[0] if address.endswith("@dae-seung.co.kr") else ""
    await page.locator('.info_main [data-type="close"]').click()
    return row


async def search_rows(page, amount: str) -> tuple[list[dict], bool]:
    await page.goto(ORIGIN + "/app/approval", wait_until="domcontentloaded")
    await page.locator("#btn_DetailSearch").click()
    form = page.locator("#approvalDetailSearch")
    await form.wait_for()
    await form.locator(".wrap_select_list .btn_select").click()
    await form.locator("#completedAt").click()
    await form.locator('[data-term="month"]').click()
    for field in ("title", "attachFileNames", "attachFileContents"):
        await form.locator(f"input#{field}").uncheck()
    await form.locator("input#docBody").check()
    await form.locator("#searchOptionAND").check()
    await form.locator("#stext").fill(amount)
    async with page.expect_response(lambda r: urlsplit(r.url).path == "/api/search/approval", timeout=20000) as response_info:
        await page.locator('.layer_approval_search a[title="검색"]').click()
    response = await response_info.value
    total, _ = await wait_search_result(page, response)
    await page.wait_for_url("**/approval/search?**", timeout=15000)
    exact_url = approval_search_url(page.url, date.today().isoformat())
    async with page.expect_response(lambda r: urlsplit(r.url).path == "/api/search/approval", timeout=20000) as response_info:
        await page.goto(exact_url, wait_until="domcontentloaded")
    total, _ = await wait_search_result(page, await response_info.value)
    await page.locator("table.type_normal, p.data_null").first.wait_for(timeout=15000)
    base = urlsplit(page.url)
    params = parse_qs(base.query)
    if params.get("dateType") != ["completedAt"]:
        raise RuntimeError("결재일 검색 조건이 반영되지 않았습니다.")
    # The UI explicitly selected completion date; do not silently use draft dates.
    rows, consumed = [], 0
    for page_no in range(5):
        if page_no:
            params["page"] = [str(page_no)]
            async with page.expect_response(lambda r: urlsplit(r.url).path == "/api/search/approval", timeout=20000) as response_info:
                await page.goto(urlunsplit((base.scheme, base.netloc, base.path, urlencode(params, doseq=True), base.fragment)), wait_until="domcontentloaded")
            response = await response_info.value
            new_total, _ = await wait_search_result(page, response)
            if new_total != total:
                raise RuntimeError("검색 중 품의 목록이 변경되었습니다. 다시 검색해 주세요.")
            await page.locator("table.type_normal").wait_for(timeout=15000)
        locator = page.locator("table.type_normal tbody tr")
        count = await locator.count()
        for index in range(count):
            row = locator.nth(index)
            async def text(selector):
                node = row.locator(selector).first
                return (await node.inner_text()).strip() if await node.count() else ""
            doc_no = await text("td.doc_num")
            if not doc_no:
                continue
            rows.append({"doc_no": doc_no, "title": await text("td.subject"), "form_name": await text("td.division"),
                         "drafter_name": await text("td.writer"), "approved_date": await text("td.date:last-child"),
                         "status": await text("td.state_wrap"), "result_url": page.url})
            consumed += 1
        if consumed >= total or count == 0 or consumed >= MAX_RESULTS:
            break
    return rows, consumed < total


async def render_pdf(page, selected: dict, config: dict) -> str:
    output = Path(config["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    await page.goto(f"{ORIGIN}/app/approval/document/{selected['doc_id']}/popup/print", wait_until="domcontentloaded")
    await page.locator("form#document_content, div.approval_import").first.wait_for(timeout=15000)
    # Require the verified amount in the print view; a login/error page must never be saved as approval.
    text = await body_text(page)
    normalized = re.sub(r"[,\s]", "", text)
    if str(config["context"]["total"]) not in normalized:
        raise RuntimeError("품의 인쇄 화면에서 검증한 금액을 확인하지 못했습니다.")
    document_text = await page.locator("form#document_content, div.approval_import").first.inner_text()
    if re.sub(r"\s", "", selected["doc_no"]) not in re.sub(r"\s", "", document_text):
        raise RuntimeError("품의 인쇄 화면의 문서번호가 선택한 문서와 다릅니다.")
    target = output / f"approval_{config['context']['invoice_id']}_{selected['doc_id']}.pdf"
    await page.pdf(path=str(target), format="A4", print_background=True,
                   margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"})
    return str(target)


async def run(config: dict) -> dict:
    context = config["context"]
    validate_context(context)
    accounts = {value.lower() for value in config["accounts"]}
    if not accounts:
        raise RuntimeError("금액 보조 검색의 전산팀 기안자 계정 목록이 설정되지 않았습니다.")
    if context["reference_date"] != date.today().isoformat():
        raise RuntimeError("품의 검색 기준일이 바뀌었습니다. 오늘 기준으로 품의를 다시 검색해 주세요.")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        page.set_default_timeout(12000)
        try:
            await login(page, config)
            rows_by_number, truncated = {}, False
            for amount in amount_variants(context["total"]):
                rows, limited = await search_rows(page, amount)
                truncated |= limited
                for row in rows:
                    rows_by_number[row["doc_no"]] = row
            candidates = []
            start, end = approval_date_range(context["reference_date"])
            for row in rows_by_number.values():
                # Cheap filters before opening/profile-reading every search hit.
                try:
                    approved = date.fromisoformat(row["approved_date"])
                except ValueError:
                    continue
                if row["status"] != "완료" or not start <= approved <= end:
                    continue
                if config.get("drafter_names") and row["drafter_name"] not in config["drafter_names"]:
                    continue
                candidates.append(await candidate_detail(page, row))
            result = decide(candidates, context, accounts, truncated=truncated)
            chosen_id = str(config.get("selected_doc_id") or "")
            if chosen_id:
                chosen = next((c for c in result["candidates"] if c["doc_id"] == chosen_id), None)
                if not chosen or truncated:
                    raise RuntimeError("선택한 품의가 현재 검색 조건과 일치하지 않습니다. 다시 검색해 주세요.")
                result.update(status="matched", selected=chosen)
            if result["status"] == "matched":
                selected = result["selected"]
                if not config.get("preview"):
                    result["saved"] = [await render_pdf(page, selected, config)]
                result["selected"] = public_candidate(selected)
            result["candidates"] = [public_candidate(c) for c in result["candidates"]]
            result.update(search_mode="body_amount", reference_date=context["reference_date"], searched_count=len(rows_by_number), truncated=truncated)
            return result
        finally:
            await browser.close()


if __name__ == "__main__":
    config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        result = asyncio.run(run(config))
    except Exception as exc:
        # Full traceback remains in server diagnostics, never in a user-facing result.
        import traceback
        traceback.print_exc()
        reason = str(exc) if isinstance(exc, (RuntimeError, ValueError)) and not re.search(r"Traceback|https?://|password|username", str(exc), re.I) else "전자결재 화면 확인 중 오류 또는 시간 초과가 발생했습니다. 잠시 후 품의 다시 찾기를 눌러 주세요."
        result = {"status": "error", "reason": "금액 보조 검색 실패: " + reason[:240]}
    Path(config["result_path"]).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
