from __future__ import annotations

from datetime import datetime
from typing import Any


def zoom_expense_retry_wait_seconds(
    data: dict[str, Any],
    retry_seconds: int,
    *,
    now: datetime | None = None,
) -> int:
    delay = max(60, int(retry_seconds or 600))
    last_attempt = data.get("zoom_expense_report_last_error_at") or data.get("zoom_expense_report_queued_at")
    if not last_attempt:
        return 0
    try:
        age = int(((now or datetime.now()) - datetime.fromisoformat(str(last_attempt))).total_seconds())
    except Exception:
        return 0
    return max(0, delay - max(0, age))
