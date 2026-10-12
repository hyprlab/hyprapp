"""The allowlist sanitizer, fed hostile and awkward HTML."""

import pytest

from hyprapp import sanitize
from hyprapp.sanitize import first_image, sanitize_html, strip_tags

BLANK = ' target="_blank" rel="noopener noreferrer"'


@pytest.mark.parametrize(
    "html, clean",
    [
        ("<script>alert(1)</script>ok", "ok"),
        ("<SCRIPT>alert(1)</SCRIPT>ok", "ok"),
        ('<img src=x onerror="alert(1)">', '<img loading="lazy" />'),
        (
            '<img src="https://e.com/a.png" alt="A" title="T" width="9">',
            '<img src="https://e.com/a.png" alt="A" title="T" loading="lazy" />',
        ),
        ('<a href="javascript:alert(1)">x</a>', f"<a{BLANK}>x</a>"),
        ('<a href="  JaVaScRiPt:alert(1)">x</a>', f"<a{BLANK}>x</a>"),
        ('<a href="data:text/html;base64,PHNjcmlwdD4=">x</a>', f"<a{BLANK}>x</a>"),
        ('<a href="vbscript:x">x</a>', f"<a{BLANK}>x</a>"),
        (
            '<a HREF="https://e.com" onclick="steal()" style="color:red">x</a>',
            f'<a href="https://e.com"{BLANK}>x</a>',
        ),
        ('<a href="//e.com/p">x</a>', f'<a href="//e.com/p"{BLANK}>x</a>'),
        ('<a href="/local">x</a>', f'<a href="/local"{BLANK}>x</a>'),
        ('<a href="#top">x</a>', f'<a href="#top"{BLANK}>x</a>'),
        ('<a href="mailto:a@b.c">x</a>', f'<a href="mailto:a@b.c"{BLANK}>x</a>'),
        ('<a href="">x</a>', f"<a{BLANK}>x</a>"),
        ("<iframe src='https://evil'><p>inner</p></iframe>after", "after"),
        ("<svg><svg></svg><script>x</script><p>in</p></svg>after", "after"),
        ("<style>body{display:none}</style>text", "text"),
        ("<noscript><img src=x></noscript>shown", "shown"),
        ("<form action='/steal'><input name=a></form>kept", "kept"),
        ("<object data=x></object>t", "t"),
        # <embed> is void, so it never closes: everything after it is dropped.
        ("<object data=x><embed src=y></object>t", ""),
        ("<embed src=y>after", ""),
        ("<video><source src=x></video><audio></audio>t", "t"),
        ("<div><span class='x'>t</span></div>", "t"),
        ("<!-- secret --><p>p</p>", "<p>p</p>"),
        (
            """<img src='https://e.com/"onerror="x'>""",
            '<img src="https://e.com/&quot;onerror=&quot;x" loading="lazy" />',
        ),
        ("a < b & c > d", "a &lt; b &amp; c &gt; d"),
        ("&lt;script&gt;alert(1)&lt;/script&gt;", "&lt;script&gt;alert(1)&lt;/script&gt;"),
        (
            "<h1>a</h1><h2>b</h2><h3>c</h3><h4>d</h4><h5>e</h5><h6>f</h6>",
            "<h3>a</h3><h3>b</h3><h3>c</h3><h4>d</h4><h4>e</h4><h4>f</h4>",
        ),
        ("line<br>break<hr></br>", "line<br />break<hr />"),
        ("<p>unclosed", "<p>unclosed"),
        ("<table><tr><td onmouseover=x>1</td></tr></table>", "<table><tr><td>1</td></tr></table>"),
        ("<blockquote cite='x'>q</blockquote>", "<blockquote>q</blockquote>"),
        ("", ""),
        (None, ""),
    ],
)
def test_sanitize(html, clean):
    assert sanitize_html(html) == clean


def test_a_parser_failure_falls_back_to_escaped_text(monkeypatch):
    def explode(self, data):
        raise ValueError("bad markup")

    monkeypatch.setattr(sanitize._Sanitizer, "feed", explode)
    assert sanitize_html("<b>bold</b> & <i>it</i>") == "bold &amp; it"


@pytest.mark.parametrize(
    "html, text",
    [
        ("<p>a</p><p>b</p>", "a b"),
        ("<p>W<span>hen</span> it</p>", "When it"),
        ("<div>x<script>var a = 1;</script>y</div>", "x y"),
        ("<style>p{}</style>z", "z"),
        ("  lots \n\n of   space  ", "lots of space"),
        ("a<br>b", "a b"),
        ("&amp; &lt;", "& <"),
        ("", ""),
        (None, ""),
    ],
)
def test_strip_tags(html, text):
    assert strip_tags(html) == text


@pytest.mark.parametrize(
    "html, src",
    [
        ('<p>x</p><img src="https://e.com/a.png"><img src="https://e.com/b.png">', "https://e.com/a.png"),
        ("<img alt='x' src=' /local.png '>", "/local.png"),
        ('<img src="javascript:alert(1)">', None),
        ("<p>no image</p>", None),
        ("", None),
        (None, None),
    ],
)
def test_first_image(html, src):
    assert first_image(html) == src
