"""Static files reach the browser versioned, so a redeploy is never served
from a stale cache. The JavaScript modules import each other by relative
paths, which carry no version; the import map in base.html adds it."""
import json
import os
import re
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parent.parent / "hyprapp" / "static" / "js"
# The specifier of every import "x", import ... from "x", export ... from "x",
# and dynamic import("x").
SPECIFIER = re.compile(r"""^\s*import\s*["']([^"']+)["']"""
                       r"""|^\s*(?:import|export)\b[^;"']*?\bfrom\s*["']([^"']+)["']"""
                       r"""|\bimport\(\s*["']([^"']+)["']""", re.M)


def page(client, path):
    html = client.get(path).data.decode()
    import_map = json.loads(re.search(r'<script type="importmap">(.*?)</script>', html, re.S).group(1))
    preloads = re.findall(r'<link rel="modulepreload" href="([^"]+)">', html)
    entries = re.findall(r'<script type="module" src="([^"]+)"></script>', html)
    return import_map["imports"], preloads, entries


def versioned(name: str) -> str:
    return f"/static/js/{name}?v={int(os.path.getmtime(JS / name))}"


def imports_of(name: str) -> list[str]:
    text = (JS / name).read_text(encoding="utf-8")
    return [next(g for g in groups if g) for groups in SPECIFIER.findall(text)]


def test_every_import_is_a_relative_path_to_a_module_here():
    for module in JS.glob("*.js"):
        for spec in imports_of(module.name):
            assert re.fullmatch(r"\./[\w-]+\.js", spec), f"{module.name} imports {spec!r}"
            assert (JS / spec[2:]).exists(), f"{module.name} imports {spec}, which is missing"


@pytest.mark.parametrize("path", ["/setup", "/login"])
def test_every_module_is_mapped_to_its_versioned_url(client, csrf, path):
    if path == "/login":
        client.post("/setup", json={"username": "a@example.com", "password": "password1"},
                    headers={"X-CSRF": csrf})
        client.post("/logout", headers={"X-CSRF": csrf})
    mapping, _, _ = page(client, path)
    assert mapping == {f"/static/js/{m.name}": versioned(m.name) for m in JS.glob("*.js")}


def test_the_entry_and_its_modules_are_versioned_and_preloaded(client, csrf, admin):
    _, preloads, entries = page(client, "/")
    assert entries == [versioned("app.js")]
    reachable, queue = [], ["app.js"]
    while queue:
        name = queue.pop(0)
        if name not in reachable:
            reachable.append(name)
            queue += [spec[2:] for spec in imports_of(name)]
    assert sorted(preloads) == sorted(versioned(name) for name in reachable)
    assert "wizard.js" not in reachable


def test_the_wizard_page_loads_its_own_module(client):
    _, _, entries = page(client, "/setup")
    assert entries == [versioned("wizard.js"), versioned("app.js")]


def test_stylesheets_and_images_are_versioned(client, csrf, admin):
    html = client.get("/").data.decode()
    for url in re.findall(r'(?:href|src)="(/static/[^"]+)"', html):
        assert re.search(r"\?v=\d+$", url), url


def test_a_file_at_its_current_version_is_cached_for_a_year(client):
    url = versioned("api.js")
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "public, max-age=31536000"


@pytest.mark.parametrize("query", ["", "?v=1", "?v=nope"])
def test_any_other_static_request_is_revalidated(client, query):
    resp = client.get("/static/js/api.js" + query)
    assert resp.status_code == 200 and resp.headers["Cache-Control"] == "no-cache"
