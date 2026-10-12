"""The route inventory: every URL, its methods and its endpoint.

A URL is part of what an install depends on (bookmarks, the client, a proxy's
rules), so it never changes by accident. The snapshot is
tests/snapshots/routes.txt.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = Path(__file__).resolve().parent / "snapshots" / "routes.txt"
URL_FOR = re.compile(r"""url_for\(\s*['"]([\w.]+)['"]""")


def current_routes(app) -> list[tuple[str, str, str]]:
    return sorted(
        (rule.rule, ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"})), rule.endpoint)
        for rule in app.url_map.iter_rules()
    )


def snapshot_routes() -> list[tuple[str, str, str]]:
    lines = [ln for ln in SNAPSHOT.read_text().splitlines() if ln and not ln.startswith("#")]
    return sorted(tuple(ln.split(" ")) for ln in lines)


def test_urls_and_methods_are_unchanged(app):
    assert [r[:2] for r in current_routes(app)] == [r[:2] for r in snapshot_routes()]


def test_endpoints_match_the_snapshot(app):
    assert current_routes(app) == snapshot_routes()


def test_every_url_for_names_a_real_endpoint(app):
    """A renamed endpoint must take every caller with it."""
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
    package = Path(app.root_path)
    sources = [*package.rglob("*.py"), *package.rglob("*.html")]
    named = {(src.relative_to(ROOT), name)
             for src in sources for name in URL_FOR.findall(src.read_text(encoding="utf-8"))}
    assert named, "no url_for() calls found; the scan is broken"
    missing = sorted((str(src), name) for src, name in named if name not in endpoints)
    assert not missing
