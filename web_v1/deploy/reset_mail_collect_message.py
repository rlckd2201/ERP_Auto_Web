from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path


def normalized_key(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("message-id:"):
        return text
    if not text.startswith("<"):
        text = f"<{text}>"
    return f"message-id:{text}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clear selected mail collector success/failure state for a controlled retry."
    )
    parser.add_argument(
        "--state-path",
        default=r"C:\ERP_DB\purchase_mail_collect_state.json",
    )
    parser.add_argument("--message-id", action="append", required=True)
    parser.add_argument(
        "--result-path",
        default=r"C:\Doc_center\mail_retry_reset_result.json",
    )
    args = parser.parse_args()

    state_path = Path(args.state_path)
    if not state_path.is_file():
        raise FileNotFoundError(state_path)

    keys = {normalized_key(value) for value in args.message_id}
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    removed: dict[str, list[str]] = {"processed": [], "failures": []}
    for section_name in removed:
        section = state.get(section_name)
        if not isinstance(section, dict):
            continue
        for key in sorted(keys):
            if key in section:
                section.pop(key, None)
                removed[section_name].append(key)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = state_path.with_name(f"{state_path.stem}.before_retry_{stamp}{state_path.suffix}")
    shutil.copy2(state_path, backup_path)
    temp_path = state_path.with_suffix(state_path.suffix + ".retry.tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(state_path)

    result = {
        "ok": True,
        "state_path": str(state_path),
        "backup_path": str(backup_path),
        "requested_keys": sorted(keys),
        "removed": removed,
    }
    result_path = Path(args.result_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
