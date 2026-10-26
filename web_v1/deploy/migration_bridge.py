"""Temporary TLS forwarding for old bookmarks and Agents after server cutover.

This process imports no accounting backend or scheduler. Run it only after the
old backend and its watchdog/startup entry have been disabled.
"""
from __future__ import annotations

import argparse
import ssl
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import uvicorn
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, RedirectResponse, StreamingResponse

HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
               "te", "trailer", "transfer-encoding", "upgrade"}


def _validate_origin(upstream: str):
    parsed = urlsplit(upstream)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("An HTTPS backend origin without credentials/query is required")
    return parsed


def create_redirect_app(upstream: str) -> FastAPI:
    """Move clients directly when the old host cannot reach the new subnet."""
    _validate_origin(upstream)
    origin = upstream.rstrip("/")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def redirect(path: str, request: Request):
        raw_path = request.scope.get("raw_path", request.url.path.encode()).decode("ascii")
        location = origin + raw_path + ("?" + request.url.query if request.url.query else "")
        return RedirectResponse(location, status_code=307, headers={"Cache-Control": "no-store"})

    return app


def create_app(upstream: str, ca_file: Path, *, transport=None) -> FastAPI:
    parsed = _validate_origin(upstream)
    origin = upstream.rstrip("/")
    context = ssl.create_default_context(cafile=str(ca_file))

    @asynccontextmanager
    async def lifespan(app):
        async with httpx.AsyncClient(verify=context, transport=transport,
                                     timeout=httpx.Timeout(connect=10, read=None, write=60, pool=30),
                                     follow_redirects=False) as client:
            app.state.client = client
            yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def forward(path: str, request: Request):
        blocked = HOP_HEADERS | {item.strip().lower() for item in request.headers.get("connection", "").split(",") if item.strip()}
        headers = {key: value for key, value in request.headers.items() if key.lower() not in blocked | {"host"}}
        headers["host"] = parsed.netloc
        headers["x-forwarded-for"] = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")
        headers["x-forwarded-proto"] = "https"
        url = origin + request.url.path + ("?" + request.url.query if request.url.query else "")
        outgoing = app.state.client.build_request(request.method, url, headers=headers, content=await request.body())
        try:
            response = await app.state.client.send(outgoing, stream=True)
        except httpx.RequestError:
            return JSONResponse({"detail": "The migrated accounting server is temporarily unavailable."}, status_code=503)

        async def body():
            try:
                async for chunk in response.aiter_raw():
                    yield chunk
            finally:
                await response.aclose()

        result = StreamingResponse(body(), status_code=response.status_code)
        response_blocked = HOP_HEADERS | {item.strip().lower() for item in response.headers.get("connection", "").split(",") if item.strip()}
        result.raw_headers = [(key, value) for key, value in response.headers.raw if key.decode("latin-1").lower() not in response_blocked]
        result.raw_headers.append((b"x-accounting-backend", parsed.netloc.encode("ascii")))
        return result

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True)
    parser.add_argument("--ca-file", type=Path, required=True)
    parser.add_argument("--cert-file", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--redirect-only", action="store_true")
    args = parser.parse_args()
    app = create_redirect_app(args.upstream) if args.redirect_only else create_app(args.upstream, args.ca_file)
    uvicorn.run(app, host=args.host, port=args.port, ssl_certfile=str(args.cert_file), ssl_keyfile=str(args.key_file))


if __name__ == "__main__":
    main()
