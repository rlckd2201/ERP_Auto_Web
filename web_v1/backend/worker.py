from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any

from .approval_fetcher import fetch_approval_documents
from .compuzone_quote import auto_attach_compuzone_quote
from .erp_queue import write_output_print_queue, write_purchase_erp_queue, write_regular_erp_queue
from .erp_runner import build_regular_erp_payload, run_invoice_erp_input, validate_purchase_invoice_for_erp
from .config import settings
from .invoice_db import ERP_QUEUED, ERROR, PROCESSING, DONE, add_invoice_log, get_invoice, set_invoice_status, update_invoice_json
from .job_store import JobRecord, JobStore
from .mail_collector import collect_mail_once
from .output_set import build_output_set_status, run_output_set_job
from .purchase_analysis import analyze_purchase_documents

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueuedJob:
    job_id: str


class JobWorker:
    def __init__(self, store: JobStore) -> None:
        self.store = store
        self._queue: queue.Queue[QueuedJob] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, name="web-v1-job-worker", daemon=True)
        self._thread.start()

    def submit(self, job: JobRecord) -> None:
        self._queue.put(QueuedJob(job_id=job.id))

    def _run_loop(self) -> None:
        log.info("WEB v1.0 job worker started")
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._run_job(item.job_id)
            except Exception as exc:
                log.exception("Job failed outside handler: %s", item.job_id)
                self.store.set_error(item.job_id, str(exc))
                self.store.add_event(item.job_id, "error", 100, f"Unhandled worker error: {exc}")
            finally:
                self._queue.task_done()

    def _run_job(self, job_id: str) -> None:
        job = self.store.get(job_id)
        if not job:
            return
        self.store.add_event(job_id, "running", 5, "Worker started")
        try:
            if job.job_type == "demo":
                result = self._run_demo(job)
            elif job.job_type == "purchase_mail_collect":
                result = self._run_purchase_mail_collect(job)
            elif job.job_type == "purchase_analyze":
                result = self._run_purchase_analyze(job)
            elif job.job_type == "purchase_one_click":
                result = self._run_purchase_erp_input(job)
            elif job.job_type == "purchase_erp_input":
                result = self._run_purchase_erp_input(job)
            elif job.job_type == "regular_one_click":
                result = self._run_purchase_erp_input(job)
            elif job.job_type == "regular_erp_input":
                result = self._run_purchase_erp_input(job)
            elif job.job_type == "output_set":
                result = self._run_output_set(job)
            else:
                result = self._run_placeholder(job)
            self.store.set_result(job_id, result)
            if result.get("defer_completion"):
                return
            self.store.add_event(job_id, "done", 100, str(result.get("notification") or "Job completed"))
        except Exception as exc:
            self.store.set_error(job_id, str(exc))
            self.store.add_event(job_id, "error", 100, f"Job failed: {exc}")
            source_job_id = str(job.payload.get("source_job_id") or "")
            if job.job_type == "output_set" and source_job_id and self.store.get(source_job_id):
                self.store.set_error(source_job_id, str(exc))
                self.store.add_event(source_job_id, "error", 100, f"원클릭 출력 실패: {exc}")

    def _run_demo(self, job: JobRecord) -> dict[str, Any]:
        steps = [
            ("crawling", 25, "Demo crawling step"),
            ("analyzing", 50, "Demo analysis step"),
            ("erp", 75, "Demo ERP step"),
            ("printing", 90, "Demo print step"),
        ]
        delay = float(job.payload.get("delay_seconds", 0.7) or 0.7)
        for status, progress, message in steps:
            time.sleep(max(0.1, min(delay, 5.0)))
            self.store.add_event(job.id, status, progress, message)
        return {
            "job_type": job.job_type,
            "title": job.title,
            "notification": "Demo job finished. Browser notification can be shown now.",
        }

    def _run_purchase_mail_collect(self, job: JobRecord) -> dict[str, Any]:
        def progress(status: str, value: int, message: str) -> None:
            self.store.add_event(job.id, status, value, message)

        result = collect_mail_once(progress=progress)
        saved = int(result.get("saved_count") or 0)
        duplicates = int(result.get("duplicate_count") or 0)
        failed = int(result.get("failed_count") or 0)
        scanned = int(result.get("scanned_messages") or 0)
        saved_invoice_ids = [int(item) for item in result.get("saved_invoice_ids") or [] if str(item).isdigit()]
        auto_analyzed_count = 0
        for invoice_id in saved_invoice_ids:
            try:
                invoice = get_invoice(invoice_id)
                if not invoice or str(invoice.get("invoice_type") or "").strip().lower() != "purchase":
                    continue
                self.store.add_event(job.id, "analyzing", 88, f"신규 구매건 자동 분석 시작: #{invoice_id}")
                analysis = analyze_purchase_documents(invoice)
                analysis["erp_ready"] = bool(analysis.get("items"))
                update_invoice_json(
                    invoice_id,
                    analysis,
                    message="메일 수집 후 신규 구매건 자동 분석 결과가 저장되었습니다.",
                )
                auto_analyzed_count += 1
            except Exception as exc:
                failed += 1
                errors = result.setdefault("errors", [])
                if isinstance(errors, list):
                    errors.append(f"auto analysis #{invoice_id}: {exc}")
                add_invoice_log(invoice_id, f"메일 수집 후 자동 분석 실패: {exc}", level="error", job_id=job.id)
        self.store.add_event(
            job.id,
            "printing",
            92,
            f"수집 결과 정리: 메일 {scanned}건, 저장 {saved}건, 중복 {duplicates}건, 실패 {failed}건",
        )
        result["auto_analyzed_count"] = auto_analyzed_count
        result["failed_count"] = failed
        result["notification"] = f"구매 메일 수집 완료: 저장 {saved}건, 실패 {failed}건"
        return result

    def _run_purchase_analyze(self, job: JobRecord) -> dict[str, Any]:
        invoice_id = int(job.payload.get("invoice_id") or 0)
        if not invoice_id:
            raise RuntimeError("분석할 구매 건 번호가 없습니다.")
        self.store.add_event(job.id, "analyzing", 10, f"구매 분석 대상 확인: #{invoice_id}")
        invoice = get_invoice(invoice_id)
        if not invoice:
            raise RuntimeError(f"구매 건을 찾지 못했습니다: #{invoice_id}")
        if str(invoice.get("invoice_type") or "").strip().lower() != "purchase":
            raise RuntimeError(f"구매 분석 대상이 아닙니다: #{invoice_id}")

        data = invoice.get("data") if isinstance(invoice.get("data"), dict) else {}
        quote_path = str(data.get("quote_path") or invoice.get("quote_path") or "")
        tax_path = str(invoice.get("pdf_path") or "")
        if not quote_path:
            self.store.add_event(job.id, "analyzing", 14, "컴퓨존 견적서 자동첨부 시도")
            quote_result = auto_attach_compuzone_quote(
                invoice_id,
                progress=lambda message: self.store.add_event(job.id, "analyzing", 16, message),
            )
            if quote_result.get("ok"):
                invoice = get_invoice(invoice_id) or invoice
                data = invoice.get("data") if isinstance(invoice.get("data"), dict) else {}
                quote_path = str(data.get("quote_path") or invoice.get("quote_path") or "")
                self.store.add_event(job.id, "analyzing", 17, "컴퓨존 견적서 자동첨부 확인 완료")
            elif quote_result.get("reason") not in {"not compuzone", "quote already exists"}:
                self.store.add_event(job.id, "analyzing", 17, f"컴퓨존 견적서 자동첨부 보류: {quote_result.get('reason')}")
        self.store.add_event(job.id, "analyzing", 18, f"세금계산서 확인: {tax_path or '-'}")
        self.store.add_event(job.id, "analyzing", 22, f"견적서 확인: {quote_path or '-'}")
        try:
            analysis = analyze_purchase_documents(invoice)
            source = str(analysis.get("analysis_source") or "-")
            ai_attempted = bool(analysis.get("analysis_ai_attempted"))
            ai_error = str(analysis.get("analysis_ai_error") or analysis.get("analysis_warning") or "").strip()
            ai_used = "AI 사용" if analysis.get("analysis_ai_used") else ("AI 시도 후 빠른 파싱" if ai_attempted else "학습 DB/빠른 파싱")
            item_count = len(analysis.get("items") or [])
            unknown = list(analysis.get("analysis_unknown_items") or [])
            self.store.add_event(job.id, "analyzing", 52, f"구매 분석 완료: {source} / {ai_used} / 품목 {item_count}건")
            if unknown:
                self.store.add_event(job.id, "analyzing", 58, f"미학습 품목 확인: {', '.join(str(item) for item in unknown[:5])}")
            if ai_attempted and not analysis.get("analysis_ai_used"):
                self.store.add_event(job.id, "analyzing", 60, f"Gemini 분석 실패/미사용: {ai_error or '원인 미상'}")
            analysis["erp_ready"] = bool(analysis.get("items"))
            analysis["approval_fetch_status"] = "running"
            analysis["approval_fetch_error"] = ""

            note = "AI 분석 사용" if analysis.get("analysis_ai_used") else ("AI 분석 시도 후 빠른 파싱 사용" if ai_attempted else "학습 DB/빠른 파싱 사용")
            note += ", 품의결재본 백그라운드 확보 시작"
            update_invoice_json(invoice_id, analysis, message=f"구매 세금계산서/견적서 분석 결과가 저장되었습니다. ({note})")
            self.store.add_event(job.id, "printing", 88, "구매 분석 결과 DB 저장 완료")
            self._start_approval_fetch_background(invoice_id, str(analysis.get("quote_path") or quote_path))
            self.store.add_event(job.id, "printing", 92, "품의결재본 자동 확보는 백그라운드에서 계속 진행됩니다.")
            return {
                "job_type": job.job_type,
                "invoice_id": invoice_id,
                "analysis_source": analysis.get("analysis_source"),
                "analysis_ai_used": bool(analysis.get("analysis_ai_used")),
                "approval_fetch_status": analysis.get("approval_fetch_status") or "",
                "approval_pdf_paths": analysis.get("approval_pdf_paths") or [],
                "approval_fetch_error": analysis.get("approval_fetch_error") or "",
                "notification": f"구매 분석 완료: #{invoice_id}",
            }
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            add_invoice_log(invoice_id, f"구매 분석 실패: {message}", level="error", job_id=job.id)
            raise

    def _start_approval_fetch_background(self, invoice_id: int, quote_path: str) -> None:
        def _worker() -> None:
            update_invoice_json(
                invoice_id,
                {
                    "approval_fetch_status": "running",
                    "approval_fetch_error": "",
                    "approval_fetch_started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                message="품의결재본 백그라운드 자동 확보 시작",
            )
            try:
                payload = fetch_approval_documents(
                    invoice_id,
                    quote_path,
                    progress=lambda message: add_invoice_log(invoice_id, f"[품의] {message}"),
                )
                update_invoice_json(
                    invoice_id,
                    {
                        **payload,
                        "approval_fetch_status": "done",
                        "approval_fetch_error": "",
                        "approval_fetch_finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "erp_ready": True,
                    },
                    message=f"품의결재본 백그라운드 자동 확보 완료: {len(payload.get('approval_pdf_paths') or [])}건",
                )
            except Exception as exc:
                update_invoice_json(
                    invoice_id,
                    {
                        "approval_fetch_status": "error",
                        "approval_fetch_error": str(exc),
                        "approval_fetch_finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "erp_ready": True,
                    },
                    message=f"품의결재본 백그라운드 자동 확보 실패: {exc}",
                )

        threading.Thread(target=_worker, name=f"approval-fetch-{invoice_id}", daemon=True).start()

    def _run_purchase_erp_input(self, job: JobRecord) -> dict[str, Any]:
        is_regular_job = job.job_type in {"regular_one_click", "regular_erp_input"}
        expected_type = "regular" if is_regular_job else "purchase"
        label = "정기" if is_regular_job else "구매"
        requested_invoice_ids = [int(item) for item in job.payload.get("invoice_ids", []) if str(item).isdigit()]
        erp_payload_ids = [int(item) for item in job.payload.get("erp_invoice_ids", []) if str(item).isdigit()]
        invoice_ids = erp_payload_ids if job.payload.get("one_click") and erp_payload_ids else requested_invoice_ids
        ready_output_ids = [int(item) for item in job.payload.get("ready_output_invoice_ids", []) if str(item).isdigit()]
        processor = str(job.payload.get("processor") or "WEB v1.0")
        if ready_output_ids:
            preview = ", ".join(f"#{invoice_id}" for invoice_id in ready_output_ids[:5])
            suffix = "" if len(ready_output_ids) <= 5 else f" 외 {len(ready_output_ids) - 5}건"
            self.store.add_event(job.id, "printing", 10, f"기존 문서 출력 대상은 ERP 입력을 건너뜁니다: {preview}{suffix}")
        if not invoice_ids:
            raise RuntimeError(f"ERP 입력 큐에 넣을 {label} 건을 선택해야 합니다.")

        self.store.add_event(job.id, "erp", 12, f"{label} 선택 건 확인: {len(invoice_ids)}건")
        invoices: list[dict[str, Any]] = []
        for index, invoice_id in enumerate(invoice_ids, start=1):
            invoice = get_invoice(invoice_id)
            if not invoice:
                self.store.add_event(job.id, "erp", 15, f"없는 계산서 건너뜀: {invoice_id}")
                continue
            if str(invoice.get("invoice_type") or "").strip().lower() != expected_type:
                self.store.add_event(job.id, "erp", 15, f"{label} ERP 입력 대상이 아닌 계산서 건너뜀: #{invoice_id}")
                continue
            try:
                if is_regular_job:
                    build_regular_erp_payload(invoice)
                else:
                    validate_purchase_invoice_for_erp(invoice)
            except Exception as exc:
                message = str(exc) or exc.__class__.__name__
                set_invoice_status(invoice_id, ERROR, processor=processor, job_id=job.id, error=message)
                self.store.add_event(job.id, "error", 15, f"{label} ERP 입력 보류: #{invoice_id} / {message}")
                continue
            set_invoice_status(invoice_id, PROCESSING, processor=processor, job_id=job.id)
            progress = 15 + int(index / max(len(invoice_ids), 1) * 35)
            self.store.add_event(job.id, "erp", progress, f"ERP 큐 데이터 준비: #{invoice_id}")
            invoices.append(invoice)

        if not invoices:
            raise RuntimeError(f"ERP 입력 큐에 등록할 유효한 {label} 건이 없습니다.")

        queue_writer = write_regular_erp_queue if is_regular_job else write_purchase_erp_queue
        source_job_payload = {
            "one_click": bool(job.payload.get("one_click")),
            "one_click_mode": str(job.payload.get("one_click_mode") or ("regular" if is_regular_job else "purchase")),
            "output_action": str(job.payload.get("output_action") or ""),
            "printer_key": str(job.payload.get("printer_key") or ""),
            "printer_name": str(job.payload.get("printer_name") or ""),
            "processor": processor,
            "target_agent_id": str(job.payload.get("target_agent_id") or ""),
            "target_client_ip": str(job.payload.get("target_client_ip") or ""),
            "regular_auto": bool(job.payload.get("regular_auto")),
        }
        queue_path = queue_writer(
            job.id,
            invoices,
            target_agent_id=str(job.payload.get("target_agent_id") or ""),
            target_client_ip=str(job.payload.get("target_client_ip") or ""),
            source_job_payload=source_job_payload,
        )
        self.store.add_event(job.id, "erp", 72, f"ERP 큐 파일 생성: {queue_path}")

        for invoice in invoices:
            set_invoice_status(int(invoice["id"]), ERP_QUEUED, processor=processor, job_id=job.id)

        if settings.erp_execution_mode == "agent":
            target = str(job.payload.get("target_agent_id") or "")
            self.store.add_event(job.id, "erp", 78, f"ERP Agent queue ready. Target Agent: {target or '-'}")
            return {
                "job_type": job.job_type,
                "invoice_ids": [invoice["id"] for invoice in invoices],
                "queue_path": str(queue_path),
                "target_agent_id": str(job.payload.get("target_agent_id") or ""),
                "target_client_ip": str(job.payload.get("target_client_ip") or ""),
                "execution_mode": "agent",
                "defer_completion": True,
                "notification": f"ERP Agent queue ready: {len(invoices)} item(s)",
            }

        if not settings.erp_execute_enabled:
            self.store.add_event(job.id, "printing", 90, "ERP 큐 파일 생성 완료. ERP_EXECUTE_ENABLED=0 설정으로 실제 입력은 보류됩니다.")
            return {
                "job_type": job.job_type,
                "invoice_ids": [invoice["id"] for invoice in invoices],
                "queue_path": str(queue_path),
                "notification": f"ERP 큐 등록 완료: {len(invoices)}건 (실행 보류)",
            }

        successes: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for index, invoice in enumerate(invoices, start=1):
            invoice_id = int(invoice["id"])
            base_progress = 72 + int(index / max(len(invoices), 1) * 18)
            set_invoice_status(invoice_id, PROCESSING, processor=processor, job_id=job.id)
            self.store.add_event(job.id, "erp", base_progress, f"ERP 자동입력 시작: #{invoice_id}")
            try:
                result = run_invoice_erp_input(
                    invoice,
                    job_id=job.id,
                    progress=lambda message, progress_value=base_progress: self.store.add_event(
                        job.id,
                        "erp",
                        min(95, progress_value),
                        message,
                    ),
                )
                successes.append(result)
                erp_pdf_path = str(result.get("erp_pdf_path") or "").strip()
                if erp_pdf_path:
                    update_invoice_json(
                        invoice_id,
                        {"erp_pdf_path": erp_pdf_path, "erp_voucher_pdf_path": erp_pdf_path},
                        message=f"ERP 전표 PDF 경로 저장: {erp_pdf_path}",
                    )
                    refreshed_invoice = get_invoice(invoice_id)
                    if refreshed_invoice:
                        build_output_set_status(refreshed_invoice, persist=True)
                set_invoice_status(invoice_id, DONE, processor=processor, job_id=job.id, processed=True)
                self.store.add_event(job.id, "printing", min(96, base_progress + 2), f"ERP 자동입력 완료: #{invoice_id}")
            except Exception as exc:
                message = str(exc) or exc.__class__.__name__
                failures.append({"invoice_id": invoice_id, "error": message})
                set_invoice_status(invoice_id, ERROR, processor=processor, job_id=job.id, error=message)
                self.store.add_event(job.id, "error", min(96, base_progress + 2), f"ERP 자동입력 실패: #{invoice_id} / {message}")

        if failures:
            self.store.add_event(job.id, "error", 98, f"ERP 자동입력 일부 실패: 성공 {len(successes)}건, 실패 {len(failures)}건")
            raise RuntimeError(f"ERP 자동입력 실패: 성공 {len(successes)}건, 실패 {len(failures)}건")

        self.store.add_event(job.id, "printing", 98, f"ERP 자동입력 완료: {len(successes)}건")
        return {
            "job_type": job.job_type,
            "invoice_ids": [invoice["id"] for invoice in invoices],
            "queue_path": str(queue_path),
            "successes": successes,
            "notification": f"ERP 자동입력 완료: {len(successes)}건",
        }

    def _run_output_set(self, job: JobRecord) -> dict[str, Any]:
        invoice_ids = [int(item) for item in job.payload.get("invoice_ids", []) if str(item).isdigit()]
        action = str(job.payload.get("action") or "merged_pdf")
        printer_name = str(job.payload.get("printer_name") or "")
        existing_only = bool(job.payload.get("existing_only") or job.payload.get("one_click_existing_only"))
        selected_doc_keys = [
            str(key).strip()
            for key in (job.payload.get("selected_doc_keys") or [])
            if str(key).strip()
        ]
        def progress(status: str, value: int, message: str) -> None:
            self.store.add_event(job.id, status, value, message)

        self.store.add_event(job.id, "printing", 10, f"문서 세트 작업 시작: {len(invoice_ids)}건")
        prepare_action = "individual_pdf" if action == "print_individual" else action
        result = run_output_set_job(
            invoice_ids,
            action=prepare_action,
            printer_name=printer_name,
            existing_only=existing_only,
            selected_doc_keys=selected_doc_keys,
            job_id=job.id,
            progress=progress,
        )
        source_job_id = str(job.payload.get("source_job_id") or "")
        if action == "print_individual":
            if not printer_name:
                raise RuntimeError("개별 출력용 프린터가 선택되지 않았습니다.")
            target_agent_id = str(job.payload.get("target_agent_id") or "")
            target_client_ip = str(job.payload.get("target_client_ip") or "")
            if not target_agent_id or not target_client_ip:
                raise RuntimeError("담당자 PC Agent 식별 정보가 없어 프린터 출력을 요청할 수 없습니다.")
            queue_path = write_output_print_queue(
                job.id,
                list(result.get("results") or []),
                printer_name=printer_name,
                printer_key=str(job.payload.get("printer_key") or ""),
                target_agent_id=target_agent_id,
                target_client_ip=target_client_ip,
                source_job_id=source_job_id,
                regular_auto=bool(job.payload.get("regular_auto")),
            )
            result["action"] = "print_individual"
            result["queue_path"] = str(queue_path)
            result["target_agent_id"] = target_agent_id
            result["target_client_ip"] = target_client_ip
            result["printer_name"] = printer_name
            result["defer_completion"] = True
            result["notification"] = f"담당자 PC 출력 대기: {len(invoice_ids)}건"
            self.store.add_event(job.id, "printing", 90, f"담당자 PC 출력 큐 등록: {printer_name}")
            if source_job_id and self.store.get(source_job_id):
                self.store.add_event(source_job_id, "printing", 99, f"담당자 PC 출력 대기: {printer_name}")
            return result
        if source_job_id and self.store.get(source_job_id):
            source = self.store.get(source_job_id)
            merged_result = dict(source.result if source else {})
            merged_result["one_click_output"] = result
            self.store.set_result(source_job_id, merged_result)
            self.store.add_event(source_job_id, "done", 100, str(result.get("notification") or "원클릭 출력 완료"))
        return result

    def _run_placeholder(self, job: JobRecord) -> dict[str, Any]:
        self.store.add_event(job.id, "running", 15, f"Preparing {job.job_type}")
        time.sleep(0.5)
        raise RuntimeError(f"Job type '{job.job_type}' is not implemented yet")
