"""Which CSS rules matched anything across the browser suite, for finding
dead CSS. Opt in with CSS_COVERAGE=<file>; see CssUsage."""

from pathlib import Path


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
        cdp.on(
            "CSS.styleSheetAdded",
            lambda e: sheets.__setitem__(e["header"]["styleSheetId"], e["header"].get("sourceURL", "")),
        )
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
            texts = {
                sid: cdp.send("CSS.getStyleSheetText", {"styleSheetId": sid})["text"]
                for sid, url in sheets.items()
                if "/static/" in url
            }
        except Exception:
            return
        for sid, text in texts.items():
            file = sheets[sid].split("/static/")[1].split("?")[0]
            self.rules.setdefault(file, _style_rules(text))
            self.used.update(
                (file, int(r["startOffset"])) for r in usage if r["styleSheetId"] == sid and r["used"]
            )

    def write(self):
        if self.out:
            import json

            unused = [
                f"{file}:{text.count(chr(10), 0, at) + 1}: {selector}"
                for file, (text, rules) in sorted(self.rules.items())
                for at, selector in rules
                if (file, at) not in self.used
            ]
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
