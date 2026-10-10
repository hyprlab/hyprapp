---
name: release-notes-style
description: "STANDING RULE for every GitHub release body: short headed lists (New features / Changes / Fixes / Translations), one terse line each with its issue, no What's changed commit list, only a Full changelog compare link, no stray bold, @ only for contributors"
metadata:
  type: feedback
---

Every release body (beta and stable) follows this shape exactly:

```
### New features:

- Recipients from LDAP directories - (#12)
- Drag files onto the window - (#15)

### Changes:

- Settings pages laid out in sections across the full width
- A failed Add user reopens with what was typed

### Fixes:

- messages stuck on "Loading…" - (#18)
- plain-text messages arriving empty - (#21)

### Translations:

- Polish by [Name](https://github.com/login)

---

**Full changelog:** [v1.41.1...v1.42.0](https://github.com/hyprlab/<repo>/compare/v1.41.1...v1.42.0)
```

- Each line is a short noun phrase, a few words, never a sentence or a
  paragraph. Condense the CHANGELOG section; don't paste it. Features start
  capitalized; fixes are lower-case and name the bug that is gone.
- The issue goes at the end as ` - (#N)` when there is one.
- Omit a heading with nothing under it.
- **No "What's changed" commit list**: the compare link carries the same
  commits. The compare link is the only line after the `---`.
- No bold anywhere except the `Full changelog:` label. No intro, no summary
  paragraph, no closing line.
- An @ only for people whose code, art or translation is in the release
  ([[contributor-credit]]); reporters are never tagged. Translators are
  credited as a link on their name under Translations.

**Why:** Jason, 2026-10-10: the notes had drifted back to "word salad"; with
this many commits a week, the commit list is overkill, and the short form is
legible.

**How to apply:** `tools/release-notes.sh` prints the headings and the link;
rewrite its lines into this form in the notes file before `gh release create`
([[ship-flow]], [[prose-style]]). The CHANGELOG itself (rendered in About)
keeps its full sentences.
