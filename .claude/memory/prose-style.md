---
name: prose-style
description: "All docs, changelog, release notes and UI text: factual, plain, no marketing, no emoji; say what the app does; American spelling (color) in anything the app shows; README is a front door with a fixed shape; run tools/check-docs.py after any .md edit"
metadata:
  type: feedback
---

- **Factual, plain language.** No marketing, no slogans or ad-copy headers, no
  superlatives, no "finally", no emoji unless it carries meaning (none by
  default). Say what the app does, not what it "enables" you to do.
- Changelog lines lead with what changed and how it behaves, from the user's
  side. How it was built belongs in the commit.
- **American spelling** in any UI string, comment or release note: color,
  behavior, canceled.
- Code comments explain *why*, not *what*.
- **Documentation has a shape.** The README is the front door, 200 lines at
  most (Hylki's once reached 667 lines, one "just one paragraph" at a time).
  Where everything else goes is the table in docs/README.md; a new docs/*.md
  must be indexed there. Artwork lives in `data/repo/`, never `docs/`.
- **After touching any `.md`, run `python3 tools/check-docs.py`**; a release
  does not go out while it fails.

**Why:** Jason's rules from Vireo/Hylki (2026-08-30 onward) after drafted notes
read like ad copy ("Trust at a glance").

**How to apply:** em dashes are fine in docs and the changelog but not in
commits or GitHub replies ([[commit-style]], [[issue-replies]]).
