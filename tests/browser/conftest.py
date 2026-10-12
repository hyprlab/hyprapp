"""Browser test fixtures.

Every test gets its own server (gunicorn, as in production, see serve.py) on
a free port with an empty data directory, so tests share nothing. Data is
arranged over HTTP with `Api`, the way the client itself talks to the server;
the browser is only used for what a person would do.

A page fails its test if any uncaught JavaScript error happens on it.
"""
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

from .serve import GOOD_TOKEN

playwright_api = pytest.importorskip("playwright.sync_api")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DESKTOP = {"width": 1280, "height": 800}
PHONE = {"width": 390, "height": 844}
CSRF_RE = re.compile(r'name="csrf" content="([^"]+)"')

ADMIN = {"username": "admin@example.com", "password": "password1", "name": "Ada"}


def pytest_collection_modifyitems(items):
    for item in items:
        if HERE in Path(item.fspath).parents:
            item.add_marker(pytest.mark.browser)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Server:
    """The app in a gunicorn process of its own, with an empty data directory."""

    def __init__(self, data_dir: Path, **env):
        self.data_dir = data_dir
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.env = {"DATA_DIR": str(data_dir), "SECRET_KEY": "browser-tests",
                    "WORKER_MINUTES": "0", **env}

    def __enter__(self):
        import os
        env = {**os.environ, **self.env}
        env.pop("WERKZEUG_RUN_MAIN", None)
        self.proc = subprocess.Popen([sys.executable, str(HERE / "serve.py"), str(self.port)],
                                     cwd=ROOT, env=env)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if requests.get(self.url + "/healthz", timeout=1).ok:
                    return self
            except requests.RequestException:
                pass
            if self.proc.poll() is not None:
                raise RuntimeError("the test server exited")
            time.sleep(0.05)
        raise RuntimeError("the test server did not come up")

    def __exit__(self, *exc):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


class Api:
    """An HTTP client with its own session, for arranging data."""

    def __init__(self, server: Server):
        self.base = server.url
        self.http = requests.Session()
        self.token = CSRF_RE.search(self.http.get(self.base + "/login").text).group(1)

    def post(self, path: str, body: dict | None = None) -> dict:
        resp = self.http.post(self.base + path, json=body or {}, headers={"X-CSRF": self.token})
        assert resp.ok, f"{path}: {resp.status_code} {resp.text[:200]}"
        return resp.json()

    def get(self, path: str) -> dict:
        resp = self.http.get(self.base + path, headers={"X-CSRF": self.token})
        assert resp.ok, f"{path}: {resp.status_code}"
        return resp.json()

    def setup(self, **fields) -> "Api":
        self.post("/setup", {**ADMIN, "registration_open": True, "worker_minutes": 15, **fields})
        return self

    def login(self, username: str, password: str) -> "Api":
        resp = self.http.post(self.base + "/login", data={"_csrf": self.token, "username": username,
                                                          "password": password},
                              allow_redirects=False)
        assert resp.status_code == 302, resp.status_code
        return self

    def item(self, title: str, body: str = "", **flags) -> dict:
        item = self.post("/items", {"title": title, "body": body})["item"]
        if flags:
            item = self.post(f"/items/{item['id']}", flags)["item"]
        return item

    def items(self, count: int, prefix: str = "Record") -> list[dict]:
        return [self.item(f"{prefix} {n:03d}") for n in range(count)]

    def cookies(self) -> list[dict]:
        return [{"name": c.name, "value": c.value, "url": self.base} for c in self.http.cookies]


FAKE_TURNSTILE = (HERE / "fake_turnstile.js").read_text()


@pytest.fixture(scope="session")
def playwright():
    with playwright_api.sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(playwright):
    browser = playwright.chromium.launch()
    yield browser
    browser.close()


@pytest.fixture()
def server(tmp_path):
    with Server(tmp_path / "data") as running:
        yield running


@pytest.fixture()
def api(server) -> Api:
    """The admin, set up through the wizard and signed in over HTTP."""
    return Api(server).setup()


class CssUsage:
    """Which CSS rules matched anything, across the suite. Opt in with
    CSS_COVERAGE=<file>: a first signal for finding dead CSS, never proof, since
    a rule used only before a reload is not seen."""

    def __init__(self, out: str | None):
        self.out, self.used, self.rules = out, set(), {}

    def watch(self, page):
        if not self.out:
            return None
        cdp = page.context.new_cdp_session(page)
        sheets = {}
        cdp.on("CSS.styleSheetAdded", lambda e: sheets.__setitem__(
            e["header"]["styleSheetId"], e["header"].get("sourceURL", "")))
        cdp.send("DOM.enable")
        cdp.send("CSS.enable")
        cdp.send("CSS.startRuleUsageTracking")
        return cdp, sheets

    def collect(self, watched):
        if not watched:
            return
        cdp, sheets = watched
        try:
            usage = cdp.send("CSS.stopRuleUsageTracking")["ruleUsage"]
            texts = {sid: cdp.send("CSS.getStyleSheetText", {"styleSheetId": sid})["text"]
                     for sid, url in sheets.items() if "/static/" in url}
        except Exception:
            return
        for sid, text in texts.items():
            file = sheets[sid].split("/static/")[1].split("?")[0]
            self.rules.setdefault(file, _style_rules(text))
            self.used.update((file, int(r["startOffset"])) for r in usage
                             if r["styleSheetId"] == sid and r["used"])

    def write(self):
        if self.out:
            import json
            unused = [f"{file}:{text.count(chr(10), 0, at) + 1}: {selector}"
                      for file, (text, rules) in sorted(self.rules.items())
                      for at, selector in rules if (file, at) not in self.used]
            total = sum(len(rules) for _, rules in self.rules.values())
            Path(self.out).write_text(json.dumps({"rules": total, "unused": unused}, indent=1))


def _style_rules(text: str) -> tuple[str, list[tuple[int, str]]]:
    """(offset, selector) for every style rule, skipping comments, @keyframes
    and @font-face, descending into @media."""
    import re
    rules, i, depth_skip = [], 0, []
    clean = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group()), text, flags=re.S)
    while i < len(clean):
        brace = clean.find("{", i)
        close = clean.find("}", i)
        if brace == -1 or (close != -1 and close < brace):
            if close == -1:
                break
            if depth_skip:
                depth_skip.pop()
            i = close + 1
            continue
        head = clean[i:brace]
        start = i + len(head) - len(head.lstrip())
        selector = " ".join(head.split())
        if selector.startswith(("@media", "@supports")):
            depth_skip.append(False)
            i = brace + 1
            continue
        end = clean.find("}", brace)
        if selector.startswith(("@keyframes", "@font-face")):
            nested = 1
            j = brace + 1
            while nested and j < len(clean):
                nested += {"{": 1, "}": -1}.get(clean[j], 0)
                j += 1
            i = j
            continue
        rules.append((start, selector))
        i = end + 1
    return text, rules


@pytest.fixture(scope="session")
def css_usage():
    import os
    usage = CssUsage(os.environ.get("CSS_COVERAGE"))
    yield usage
    usage.write()


@pytest.fixture()
def new_page(browser, server, css_usage):
    """Make a page, optionally signed in as an Api's session.

    With stub_cloudflare, Cloudflare's widget script is replaced by
    fake_turnstile.js. It is off by default because routing any request turns
    off the browser's HTTP cache, and a reload that refetches the font lays
    the page out late.
    """
    contexts, errors, watched = [], [], []

    def make(api: Api | None = None, viewport=None, color_scheme="light", stub_cloudflare=False,
             **options):
        context = browser.new_context(base_url=server.url, viewport=viewport or DESKTOP,
                                      color_scheme=color_scheme, **options)
        context.set_default_timeout(5000)
        if stub_cloudflare:
            context.route("https://challenges.cloudflare.com/**", lambda route: route.fulfill(
                status=200, content_type="text/javascript",
                body=FAKE_TURNSTILE.replace("GOOD_TOKEN", GOOD_TOKEN)))
        if api is not None:
            context.add_cookies(api.cookies())
        page = context.new_page()
        page.on("pageerror", lambda err: errors.append(f"{page.url}: {err}"))
        watched.append(css_usage.watch(page))
        contexts.append(context)
        return page

    yield make
    for item in watched:
        css_usage.collect(item)
    for context in contexts:
        context.close()
    assert not errors, "JavaScript errors:\n" + "\n".join(errors)


@pytest.fixture()
def page(new_page, api):
    """The admin's browser, on the desktop, at the app."""
    page = new_page(api)
    page.goto("/")
    return page


def card(page, title):
    """A record's card or row."""
    return page.locator("[data-item]", has_text=title)


def open_record(page, title):
    """Open a record's sheet by clicking it, and wait until it shows."""
    card(page, title).click()
    playwright_api.expect(page.locator("#sheet-title")).to_have_text(title)


def wait_for_reload(page, action):
    """Run an action that reloads the page, and wait until the new one has run its scripts."""
    with page.expect_navigation(wait_until="load"):
        action()
