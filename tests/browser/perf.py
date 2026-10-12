"""Measure what a page load costs, so a change can be compared with before.

    python -m tests.browser.perf OUT.json [--image]

Starts the app as the browser tests do, with 300 records, and records:
  * the first load of / in a cold browser: requests, bytes, the time to
    DOMContentLoaded, and the time until a click on Search opens the palette
    (median of several loads)
  * server response times for /, /search and a ?partial=1 page (median, p90)
  * with --image, the size of the Docker image built from the working tree
"""
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from .conftest import ROOT, Api, Server

LOADS = 15
REQUESTS = 60

# Clicks Search as early as the page allows and notes when the palette opens.
FIRST_USE = """
window.__firstUse = null;
document.addEventListener("DOMContentLoaded", function () {
  (function attempt() {
    var button = document.getElementById("search-btn");
    var palette = document.getElementById("search-modal");
    if (button) button.click();
    if (palette && palette.open) window.__firstUse = performance.now();
    else requestAnimationFrame(attempt);
  })();
});
"""


def first_loads(browser, server, api) -> dict:
    samples = []
    for _ in range(LOADS):
        context = browser.new_context(base_url=server.url)
        context.add_cookies(api.cookies())
        page = context.new_page()
        page.add_init_script(FIRST_USE)
        responses = []
        page.on("requestfinished", lambda request: responses.append(request))
        page.goto("/", wait_until="load")
        page.wait_for_function("window.__firstUse !== null")
        page.wait_for_load_state("networkidle")
        timing = page.evaluate("""() => {
            const nav = performance.getEntriesByType("navigation")[0];
            return {dcl: nav.domContentLoadedEventEnd, load: nav.loadEventEnd, first_use: window.__firstUse};
        }""")
        sizes = [r.sizes() for r in responses]
        timing["requests"] = len(responses)
        timing["bytes"] = sum(s["responseBodySize"] + s["responseHeadersSize"] for s in sizes)
        timing["urls"] = sorted(r.url.replace(server.url, "").split("?")[0] for r in responses)
        samples.append(timing)
        context.close()
    median = lambda key: round(statistics.median(s[key] for s in samples), 1)
    return {"requests": samples[0]["requests"], "bytes": samples[0]["bytes"], "files": samples[0]["urls"],
            "dom_content_loaded_ms": median("dcl"), "load_ms": median("load"),
            "first_use_ms": median("first_use")}


def server_times(api) -> dict:
    out = {}
    for name, path, headers in [
        ("index", "/", {"Accept": "text/html"}),
        ("search", "/search?q=record", {"X-CSRF": api.token}),
        ("page_2_partial", "/?page=2&partial=1", {"Accept": "text/html"}),
    ]:
        times = []
        for _ in range(REQUESTS):
            started = time.perf_counter()
            resp = api.http.get(api.base + path, headers=headers)
            times.append((time.perf_counter() - started) * 1000)
            assert resp.ok, (path, resp.status_code)
        times.sort()
        out[name] = {"median_ms": round(statistics.median(times), 2),
                     "p90_ms": round(times[int(len(times) * 0.9)], 2), "bytes": len(resp.content)}
    return out


def image_size() -> int:
    tag = "hyprapp-perf:measure"
    subprocess.run(["docker", "build", "-q", "-t", tag, "."], cwd=ROOT, check=True, capture_output=True)
    out = subprocess.run(["docker", "image", "inspect", tag, "--format", "{{.Size}}"],
                         check=True, capture_output=True, text=True)
    return int(out.stdout.strip())


def main(out: str, with_image: bool) -> None:
    with tempfile.TemporaryDirectory() as tmp, Server(Path(tmp) / "data") as server, \
            sync_playwright() as pw:
        api = Api(server).setup()
        api.items(300)
        browser = pw.chromium.launch()
        result = {
            "git": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                  capture_output=True, text=True).stdout.strip(),
            "chromium": browser.version,
            "first_load": first_loads(browser, server, api),
            "server": server_times(api),
        }
        browser.close()
    if with_image:
        result["image_bytes"] = image_size()
    Path(out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main(sys.argv[1], "--image" in sys.argv[2:])
