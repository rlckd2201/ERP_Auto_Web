"""Exercise the deployed loop factory in an isolated HTTPS server on Windows."""
import argparse
import ast
import asyncio
import json
import socket
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import requests
import uvicorn


def verify(native_host, certificate, private_key):
    if sys.platform != "win32":
        raise RuntimeError("Run with the Windows production Python/Uvicorn runtime")
    tree = ast.parse(Path(native_host).read_text(encoding="utf-8-sig"))
    call = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "uvicorn"
        and node.func.attr == "run"
    )
    expression = compile(
        ast.Expression(next(item.value for item in call.keywords if item.arg == "loop")),
        "native-host-loop",
        "eval",
    )
    loop_setting = eval(expression, {"sys": sys})
    assert loop_setting == "asyncio:SelectorEventLoop"
    assert eval(expression, {"sys": SimpleNamespace(platform="linux")}) == "auto"
    factory = uvicorn.Config("fixture", loop=loop_setting).get_loop_factory()
    loop = factory()
    assert isinstance(loop, asyncio.SelectorEventLoop)
    expected_name = type(loop).__name__
    loop.close()

    async def app(scope, receive, send):
        body = type(asyncio.get_running_loop()).__name__.encode()
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": body})

    server = uvicorn.Server(uvicorn.Config(
        app, host="127.0.0.1", port=0, loop=loop_setting, lifespan="off",
        ssl_certfile=str(certificate), ssl_keyfile=str(private_key),
        log_level="error", timeout_graceful_shutdown=1, timeout_keep_alive=1,
    ))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 12
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline, "Fixture startup failed"
            time.sleep(0.05)
        port = server.servers[0].sockets[0].getsockname()[1]
        statuses = []
        for _ in range(12):
            # End a connection before completing its TLS handshake, then require
            # the next certificate-validated HTTPS request to succeed.
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                pass
            with requests.get(
                f"https://127.0.0.1:{port}/", verify=str(certificate), timeout=3,
            ) as response:
                assert response.status_code == 200 and response.text == expected_name
                statuses.append(response.status_code)
        return {"uvicorn": uvicorn.__version__, "loop": expected_name,
                "interrupted_handshakes": 12, "subsequent_https_requests": statuses,
                "non_windows_policy": "auto"}
    finally:
        # Bound cleanup of the intentionally interrupted fixture connections.
        server.should_exit = True
        thread.join(timeout=8)
        assert not thread.is_alive(), "Fixture did not stop"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-host", required=True, type=Path)
    parser.add_argument("--certificate", required=True, type=Path)
    parser.add_argument("--private-key", required=True, type=Path)
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.native_host, arguments.certificate, arguments.private_key)))
