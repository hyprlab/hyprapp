---
name: design-system
description: "The Hyprlab Flask UI (from Hyprfeed's 'electric editorial'): Inter only, embedded; one accent (volt yellow #FFD60A light / #F7DF1E dark by default) spent only on the mark, new markers and active states; sidebar shell; two-pane settings window (rail + section, list-then-section on phones); no frontend framework. Reuse components from docs/DESIGN.md"
metadata:
  type: project
---

The interface every Hyprlab Flask app starts from, taken from Hyprfeed and
kept in `static/css/app.css`. Full reference: docs/DESIGN.md.

Decisions to preserve when editing:
- **Inter Variable only**, embedded woff2 in `static/fonts`; no external
  requests (Turnstile is the one exception, when enabled).
- **One accent, spent sparingly:** the brand mark, new-item markers, and
  active states. Rebrand by changing `--accent`, `--accent-ink`,
  `--accent-glow` in both themes and the mark in `partials/mark.html` +
  `static/img/logo.svg`. Nothing else hardcodes a brand color.
- Light and dark via `data-theme` on `<html>`, resolved by an inline `<head>`
  script before first paint; the preference is a column on the user.
- **The shell:** sidebar with pinned head and foot (only the middle scrolls),
  sticky blurred topbar, drawer under 900px.
- **Settings is a two-pane window** (Jason asked for it 2026-09-24, replacing
  Hyprfeed's tabs across the top): a rail of sections styled like the main
  sidebar, About pinned at the rail's foot, the chosen section on the right
  under its own title. Fixed size, panes scroll inside. On phones it is full
  screen: the list first, a section slides in with Back, Escape goes back
  before it closes. Sections are declared once in `settings_sections`.
- **List rows are a CSS grid:** a marker that hides keeps its cell
  (`visibility: hidden`, not `display: none`) or the columns shift.
- The sheet rises from below and leaves through the top toward the toast
  under the topbar; backdrop clicks are detected by comparing the pointer with
  the dialog's box, and only when the press also started outside.
- `html:has(dialog[open]) { overflow: hidden }` keeps the page from scrolling
  behind any dialog.
- No frontend framework, no build step; hand-written CSS and one `app.js`.

- **A reload keeps your place** (Jason, 2026-09-24, "default behavior"):
  the open dialog comes back after a refresh with its state (settings
  section + scroll, record draft, search query, the open record). Generic
  in app.js ("Dialogs survive a reload"): every `<dialog id>` by default,
  `dialogMemory` for state, `data-restore="off"` to opt out; only on a
  reload (Navigation Timing type), sessionStorage per tab.

**Interface rules (from Hylki and Hyprfeed):** errors are always shown; a
success toast only when the result isn't already visible. Undo instead of
"Are you sure?" when recoverable. Optimistic toggles roll back on failure.
Every screen has a URL. American spelling ([[prose-style]]).
