from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from .erp_runner import _load_legacy_module
from .purchase_analysis import purchase_approval_dir


Progress = Callable[[str], None]


def _check_playwright_runtime() -> None:
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", "import greenlet; import playwright.async_api"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=20,
    )
    if proc.returncode != 0:
        output = (proc.stdout or "").strip()
        raise RuntimeError(
            "품의결재본 자동 확보에 필요한 greenlet/Playwright 런타임이 깨져 있습니다. "
            "운영서버에서 install_operating_server.ps1을 다시 실행하거나 "
            "`python -m pip install --force-reinstall --no-cache-dir greenlet playwright` 후 "
            "`python -m playwright install chromium`을 실행하세요. "
            f"진단: {output}"
        )


def fetch_approval_documents(invoice_id: int, quote_path: str, progress: Progress | None = None) -> dict[str, Any]:
    quote = Path(str(quote_path or ""))
    if not quote.exists():
        raise RuntimeError("품의결재본 자동 확보를 위한 견적서 파일을 찾지 못했습니다.")
    _check_playwright_runtime()

    legacy = _load_legacy_module()
    helper_source = str(getattr(legacy, "APPROVAL_HELPER_SOURCE", "") or "")
    if not helper_source:
        raise RuntimeError("담당자용 품의결재본 헬퍼 소스를 찾지 못했습니다.")

    output_dir = purchase_approval_dir(invoice_id)
    helper_path = ""
    cfg_path = ""
    result_path = ""
    try:
        helper_fd, helper_path = tempfile.mkstemp(prefix="approval_helper_", suffix=".py")
        os.close(helper_fd)
        cfg_fd, cfg_path = tempfile.mkstemp(prefix="approval_cfg_", suffix=".json")
        os.close(cfg_fd)
        result_fd, result_path = tempfile.mkstemp(prefix="approval_result_", suffix=".json")
        os.close(result_fd)

        Path(helper_path).write_text(helper_source, encoding="utf-8")
        cfg = {
            "quote_path": str(quote),
            "output_dir": str(output_dir),
            "username": str(getattr(legacy, "APPROVAL_DEFAULT_USER", "") or ""),
            "password": str(getattr(legacy, "APPROVAL_DEFAULT_PASSWORD", "") or ""),
            "headless": True,
            "result_path": result_path,
        }
        Path(cfg_path).write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

        creationflags = 0x08000000 if os.name == "nt" else 0
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.Popen(
            [sys.executable, "-X", "utf8", helper_path, cfg_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=creationflags,
            env=env,
        )

        saved: list[str] = []
        order_number = ""
        result_line = ""
        output_tail: list[str] = []
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            output_tail.append(line)
            output_tail = output_tail[-40:]
            if line.startswith("LOG:"):
                if progress:
                    progress(line[4:].strip())
            elif line.startswith("ORDER:"):
                order_number = line[6:].strip()
                if progress:
                    progress(f"품의 주문번호 확인: {order_number}")
            elif line.startswith("FILE:"):
                saved_path = line[5:].strip()
                saved.append(saved_path)
                if progress:
                    progress(f"품의결재본 저장 감지: {saved_path}")
            elif line.startswith("RESULT_JSON:"):
                result_line = line[len("RESULT_JSON:") :].strip()
            else:
                if progress:
                    progress(line)

        rc = proc.wait(timeout=5)
        if rc != 0:
            tail = " / ".join(output_tail[-12:])
            raise RuntimeError(f"품의결재본 다운로드 헬퍼가 비정상 종료되었습니다. rc={rc}. 마지막 로그: {tail}")

        payload: dict[str, Any] = {}
        if result_path and Path(result_path).exists():
            payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
        elif result_line:
            payload = json.loads(result_line)

        saved = payload.get("saved", saved) or saved
        order_number = payload.get("order_number", order_number) or order_number
        saved = [str(path) for path in saved if path and Path(path).exists()]
        if not saved:
            raise RuntimeError("품의결재본 PDF를 찾지 못했습니다.")
        return {
            "approval_pdf_paths": saved,
            "approval_order_number": order_number,
        }
    finally:
        for temp_path in (helper_path, cfg_path, result_path):
            try:
                if temp_path and Path(temp_path).exists():
                    Path(temp_path).unlink()
            except Exception:
                pass
