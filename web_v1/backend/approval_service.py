"""One background approval lookup per invoice, independent of ERP/output jobs."""
from __future__ import annotations

import threading
import time
import uuid
from datetime import date, datetime
from pathlib import Path

from .approval_fetcher import ApprovalLookupResult, fetch_amount_documents, fetch_approval_documents
from .approval_matching import invoice_context
from .invoice_db import add_invoice_log, get_invoice, update_approval_lookup

_lock = threading.Lock()
_active: set[int] = set()


def validate_choice(invoice: dict, doc_id: str, search_id: str) -> dict:
    data = invoice.get("data") or {}
    context = data.get("approval_search_context") or {}
    if (data.get("approval_fetch_status") != "review" or not search_id
            or data.get("approval_search_id") != search_id
            or data.get("approval_search_truncated")):
        raise ValueError("품의 검색 결과가 바뀌었거나 전체 후보를 확인하지 못했습니다. 품의 다시 찾기를 눌러 주세요.")
    fresh = invoice_context(invoice, date.today().isoformat())
    if context.get("fingerprint") != fresh["fingerprint"] or context.get("reference_date") != fresh["reference_date"]:
        raise ValueError("금액·사업장·견적서 또는 검색 기준일이 바뀌었습니다. 품의를 다시 찾아 주세요.")
    if not doc_id.isdigit() or not any(str(c.get("doc_id")) == doc_id for c in data.get("approval_candidates") or []):
        raise ValueError("현재 검색 결과에 없는 품의는 연결할 수 없습니다.")
    return fresh


def start_approval_lookup(invoice_id: int, quote_path: str = "", *, doc_id: str = "", search_id: str = "", requested_by: str = "") -> bool:
    with _lock:
        if invoice_id in _active:
            return False
        invoice = get_invoice(invoice_id)
        if not invoice or invoice.get("invoice_type") != "purchase":
            raise ValueError("구매 내역을 찾지 못했습니다.")
        data = invoice.get("data") or {}
        if any(Path(str(p)).is_file() for p in data.get("approval_pdf_paths") or []):
            return False
        if data.get("approval_fetch_status") == "running":
            try:
                if (datetime.now() - datetime.fromisoformat(data["approval_fetch_started_at"])).total_seconds() < 300:
                    return False
            except (ValueError, KeyError):
                pass
        quote = str(quote_path or data.get("quote_path") or "")
        if not quote or not Path(quote).is_file():
            raise ValueError("견적서 파일이 없습니다. 먼저 견적서를 등록·분석해 주세요.")
        context = validate_choice(invoice, doc_id, search_id) if doc_id else invoice_context(invoice, date.today().isoformat())
        run_id = uuid.uuid4().hex
        if not update_approval_lookup(invoice_id, context, {
                "approval_fetch_status": "running", "approval_fetch_error": "",
                "approval_fetch_started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "approval_search_id": run_id, "approval_candidates": [], "approval_search_context": context,
                "approval_search_truncated": False, "approval_requested_by": requested_by}):
            raise ValueError("구매 내역이 변경되었습니다. 새로고침 후 다시 시도해 주세요.")
        _active.add(invoice_id)

    def work():
        try:
            add_invoice_log(invoice_id, "전자결재 품의 검색 시작" + (f" · 선택 문서 {doc_id} 재검증 · 요청자 {requested_by}" if doc_id else ""))
            payload = (fetch_amount_documents(context, selected_doc_id=doc_id) if doc_id else
                fetch_approval_documents(invoice_id, quote, progress=lambda message: add_invoice_log(invoice_id, f"[품의] {message}")))
            payload.update(approval_fetch_status="done", approval_fetch_error="", approval_candidates=[])
            message = f"품의 확보 완료: {len(payload.get('approval_pdf_paths') or [])}건"
        except ApprovalLookupResult as exc:
            result = exc.result
            payload = {"approval_fetch_status": "review" if result.get("status") == "review" else "error",
                       "approval_fetch_error": str(exc), "approval_candidates": result.get("candidates") or [],
                       "approval_search_context": result.get("context") or context,
                       "approval_search_truncated": bool(result.get("truncated"))}
            message = str(exc)
        except Exception as exc:
            payload = {"approval_fetch_status": "error", "approval_fetch_error": str(exc), "approval_candidates": []}
            message = f"품의 확보 실패: {exc}"
        try:
            payload["approval_fetch_finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if update_approval_lookup(invoice_id, context, payload, expected_search_id=run_id):
                add_invoice_log(invoice_id, message)
            else:
                # A changed quote/amount or manually attached approval wins over stale background work.
                update_approval_lookup(invoice_id, None, {"approval_fetch_status": "error",
                    "approval_fetch_error": "검색 중 구매 내역이 변경되어 결과를 연결하지 않았습니다. 품의를 다시 찾아 주세요.",
                    "approval_candidates": [], "approval_fetch_finished_at": payload["approval_fetch_finished_at"]}, expected_search_id=run_id)
                add_invoice_log(invoice_id, "품의 검색 결과 폐기: 검색 중 구매 내역 또는 품의 연결이 변경됨")
        finally:
            with _lock:
                _active.discard(invoice_id)

    try:
        threading.Thread(target=work, name=f"approval-fetch-{invoice_id}", daemon=True).start()
    except Exception:
        with _lock:
            _active.discard(invoice_id)
        raise
    return True
