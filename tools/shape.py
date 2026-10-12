"""What tools/check-code.py measures: the functions in Python and JavaScript
files with their length and complexity, the imports between JavaScript
modules, and blocks of code repeated across files. Stdlib only."""

import ast
import re
from pathlib import Path

TYPES = {".py": "py", ".js": "js", ".css": "css", ".html": "html"}


def functions_in(path: Path) -> list[tuple[str, int, int, int]]:
    """(name, line, length, complexity) for each function in a .py or .js file."""
    return python_functions(path) if path.suffix == ".py" else js_functions(path)


# ———— Python functions ————

DECISIONS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.match_case)


def python_functions(path: Path) -> list[tuple[str, int, int, int]]:
    """(name, line, length, complexity) for every function, nested ones apart."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []

    def complexity(node) -> int:
        count = 1
        stack = list(ast.iter_child_nodes(node))
        while stack:
            child = stack.pop()
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            if isinstance(child, DECISIONS):
                count += 1
            stack.extend(ast.iter_child_nodes(child))
        return count

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = node.end_lineno - node.lineno + 1
            found.append((node.name, node.lineno, length, complexity(node)))
    return found


# ———— JavaScript functions ————

JS_START = re.compile(
    r"function\s*\*?\s*(?P<named>[\w$]*)\s*\([^)]*\)\s*\{"  # function f() {  function () {
    r"|^[ \t]*(?:async\s+)?(?P<method>[\w$]+)\s*\([^()]*\)\s*\{"  # method() {, at a line's start
    r"|(?P<arrow>\([^()]*\)|[\w$]+)\s*=>\s*\{",  # (a) => {   a => {
    re.M,
)
JS_KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return", "with"}
JS_DECISIONS = re.compile(r"\b(?:if|for|while|case|catch)\b|&&|\|\||\?\?|\?(?![.?])")


def _blank(chars: list[str], start: int, end: int) -> None:
    for k in range(start, end):
        if chars[k] != "\n":
            chars[k] = " "


def js_mask(text: str) -> str:
    """The text with strings, template literals, regex literals and comments
    blanked (newlines kept), so braces and keywords can be counted."""
    out, i, n = list(text), 0, len(text)
    last = ""
    while i < n:
        ch = text[i]
        two = text[i : i + 2]
        if two in ("//", "/*"):
            end = text.find("\n", i) if two == "//" else text.find("*/", i + 2) + 2
            end = n if end <= 1 or end == -1 else end
            _blank(out, i, end)
            i = end
            continue
        if ch in "'\"`" or (ch == "/" and last in "(,=:[!&|?{};+-*%<>~^" + "\n"):
            quote, k = ch, i + 1
            while k < n and text[k] != quote:
                k += 2 if text[k] == "\\" else 1
            _blank(out, i + 1, min(k, n))
            i = k + 1
            last = "a"
            continue
        if not ch.isspace():
            last = ch
        i += 1
    return "".join(out)


def js_functions(path: Path) -> list[tuple[str, int, int, int]]:
    masked = js_mask(path.read_text(encoding="utf-8"))
    spans = []
    for match in JS_START.finditer(masked):
        if match.group("method") in JS_KEYWORDS:
            continue
        name = (
            match.group("method")
            or match.group("named")
            or ("(arrow)" if match.group("arrow") else "(anonymous)")
        )
        start = match.end() - 1
        depth, k = 0, start
        while k < len(masked):
            depth += {"{": 1, "}": -1}.get(masked[k], 0)
            if depth == 0:
                break
            k += 1
        spans.append((name, start, k))
    found = []
    for name, start, end in spans:
        body = masked[start:end]
        # Nested functions count on their own, not toward this one.
        for _, s2, e2 in spans:
            if start < s2 and e2 <= end:
                body = body.replace(masked[s2:e2], " " * (e2 - s2), 1)
        line = masked.count("\n", 0, start) + 1
        length = masked.count("\n", start, end) + 1
        found.append((name, line, length, 1 + len(JS_DECISIONS.findall(body))))
    return found


# ———— duplication ————

IMPORT_OPEN = re.compile(r"^(?:from \S+ )?import \($")
TRIVIAL = re.compile(r"^[\s)\]}>;,{(\[]*$|^(?:import|from)\s|^</\w+>$|^\{%-?\s*end\w*\s*-?%\}$")
COMMENT = {
    "py": re.compile(r"^#"),
    "js": re.compile(r"^(//|/?\*)"),
    "html": re.compile(r"^(\{#.*#\}|<!--.*-->)$"),
    "css": re.compile(r"^/?\*"),
}


def normalized(path: Path, kind: str) -> list[tuple[int, str]]:
    """(line number, normalized text) for the lines that carry meaning."""
    text = path.read_text(encoding="utf-8")
    if kind == "css":
        text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), text, flags=re.S)
        rows, line = [], 1
        for piece in re.split(r"([;{}\n])", text):
            if piece == "\n":
                line += 1
            elif piece.strip() and piece not in ";{}" and ":" in piece:
                rows.append((line, " ".join(piece.split())))
        return rows
    rows, in_import = [], False
    for number, raw in enumerate(text.splitlines(), 1):
        line = " ".join(raw.split())
        # A parenthesized import lists one name per line; names aren't code.
        if kind == "py" and (in_import or IMPORT_OPEN.match(line)):
            in_import = not line.startswith(")")
            continue
        if line and not TRIVIAL.match(line) and not COMMENT[kind].match(line):
            rows.append((number, line))
    return rows


def duplicates(files: list[Path], window: int, focus: set[Path] | None) -> list[tuple[Path, int, Path, int]]:
    """Where the same `window` normalized lines appear twice: (path, line,
    other path, other line), one per pair of places. With focus, only pairs
    that involve one of those files."""
    seen: dict[tuple, list[tuple[Path, int]]] = {}
    for path in files:
        rows = normalized(path, TYPES[path.suffix])
        for i in range(len(rows) - window + 1):
            key = tuple(text for _, text in rows[i : i + window])
            seen.setdefault(key, []).append((path, rows[i][0]))
    found: list[tuple[Path, int, Path, int]] = []
    for (path, line), *others in (places for places in seen.values() if len(places) > 1):
        for other, other_line in others:
            if path == other and abs(line - other_line) < window:
                continue
            if focus and not ({path, other} & focus):
                continue
            # One report per pair of files and region, not one per window.
            if any(
                (p, o) == (path, other) and abs(a - line) <= window and abs(b - other_line) <= window
                for p, a, o, b in found
            ):
                continue
            found.append((path, line, other, other_line))
    return found


# ———— JavaScript imports ————

JS_IMPORT = re.compile(r"""^\s*import\s+(?:\{([^}]*)\}\s+from\s+)?["']\./([\w-]+\.js)["']""", re.M)
JS_EXPORT = re.compile(
    r"^\s*export\s+(?:async\s+)?(?:function\*?|var|let|const|class)\s+([\w$]+)|^\s*export\s*\{([^}]*)\}", re.M
)


def js_exports(path: Path) -> set[str]:
    names = set()
    for single, listed in JS_EXPORT.findall(path.read_text(encoding="utf-8")):
        names.add(single) if single else names.update(n.split(" as ")[-1].strip() for n in listed.split(","))
    return names


def js_import_problems(path: Path) -> list[str]:
    """Each import must name a module that exists and things it exports, or
    the browser refuses the whole page's modules."""
    found = []
    for names, target in JS_IMPORT.findall(path.read_text(encoding="utf-8")):
        module = path.parent / target
        if not module.exists():
            found.append(f"imports ./{target}, which does not exist")
            continue
        exported = js_exports(module)
        for name in (n.split(" as ")[0].strip() for n in names.split(",") if n.strip()):
            if name not in exported:
                found.append(f"imports {name} from ./{target}, which does not export it")
    return found
