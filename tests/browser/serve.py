"""Serve the app for the browser tests: gunicorn with the production
arguments, and Cloudflare's siteverify answered here instead of over the
network.

    python tests/browser/serve.py PORT

The answer is made at the transport, under requests, so it holds however the
app calls requests. GOOD_TOKEN passes with any secret but "wrong-secret".
"""

import json
import sys
from urllib.parse import parse_qsl

from requests.adapters import HTTPAdapter
from requests.models import Response

SITEVERIFY = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
GOOD_TOKEN = "browser-test-token"


def answer(form: dict) -> dict:
    if form.get("secret") == "wrong-secret":
        return {"success": False, "error-codes": ["invalid-input-secret"]}
    if form.get("response") != GOOD_TOKEN:
        return {"success": False, "error-codes": ["invalid-input-response"]}
    return {"success": True}


_send = HTTPAdapter.send


def send(self, request, **kwargs):
    if not request.url.startswith(SITEVERIFY):
        return _send(self, request, **kwargs)
    body = request.body.decode() if isinstance(request.body, bytes) else request.body or ""
    resp = Response()
    resp.status_code, resp.url, resp.request = 200, request.url, request
    resp.headers["Content-Type"] = "application/json"
    resp._content = json.dumps(answer(dict(parse_qsl(body)))).encode()
    return resp


def main(port: str) -> None:
    HTTPAdapter.send = send
    from gunicorn.app.wsgiapp import run

    # The Dockerfile's arguments: one worker, eight threads.
    sys.argv = [
        "gunicorn",
        "--workers",
        "1",
        "--threads",
        "8",
        "--timeout",
        "90",
        "--bind",
        f"127.0.0.1:{port}",
        "--log-level",
        "warning",
        "hyprapp:create_app()",
    ]
    run()


if __name__ == "__main__":
    main(sys.argv[1])
