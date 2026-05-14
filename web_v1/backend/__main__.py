from __future__ import annotations

import asyncio
import sys

import uvicorn

from .config import settings


def main() -> None:
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    ssl_kwargs = {}
    if settings.ssl_cert_file and settings.ssl_key_file:
        ssl_kwargs = {
            "ssl_certfile": str(settings.ssl_cert_file),
            "ssl_keyfile": str(settings.ssl_key_file),
        }
    uvicorn.run(
        "web_v1.backend.app:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=settings.app_env == "development",
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
