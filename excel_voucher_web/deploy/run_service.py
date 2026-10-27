"""Run Uvicorn in the scheduled task process, without an orphanable child."""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys


def load_environment(path: Path) -> dict[str, str]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or any(
        not re.fullmatch(r"EXCEL_VOUCHER_[A-Z0-9_]+", key) or not isinstance(value, str)
        for key, value in config.items()
    ):
        raise ValueError("Invalid finance service environment")
    for key in ("DATA_DIR", "WEB_HOST", "WEB_PORT", "WEB_PUBLIC_ORIGIN"):
        if not config.get("EXCEL_VOUCHER_" + key):
            raise ValueError("Missing service setting: " + key)
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("app-root", "config", "cert", "key"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    for path in (args.config, args.cert, args.key):
        if not path.is_file():
            raise FileNotFoundError(path)
    config = load_environment(args.config)
    os.environ.update(config)
    os.chdir(args.app_root)
    sys.path.insert(0, str(args.app_root))
    logs = Path(config["EXCEL_VOUCHER_DATA_DIR"]) / "service_logs"
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / ("web-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".log")
    with log.open("a", encoding="utf-8", buffering=1) as stream:
        with redirect_stdout(stream), redirect_stderr(stream):
            import uvicorn
            uvicorn.run("app.main:app", host=config["EXCEL_VOUCHER_WEB_HOST"],
                        port=int(config["EXCEL_VOUCHER_WEB_PORT"]),
                        ssl_certfile=str(args.cert), ssl_keyfile=str(args.key),
                        use_colors=False)


if __name__ == "__main__":
    main()
