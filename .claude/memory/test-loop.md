---
name: test-loop
description: "After EVERY code change, unprompted: run pytest, rebuild + restart the local container (tools/redeploy.sh) so Jason can try it; verify UI with Playwright (T3 preview tools time out here); screenshots to fresh filenames; kill processes by PID, never pkill -f"
metadata:
  type: feedback
---

**Standing order:** after every code change, run the tests and rebuild and
restart the local container (`tools/redeploy.sh`) without being asked, so
Jason can try it immediately. It publishes nothing ([[no-publish-until-asked]]).
Exception: he says otherwise, or a restart would lose someone's in-progress
state; then say the build is ready and let him swap it.

Before saying something works: rebuild, load the page, and check it. For the
UI, drive the running app with Playwright (headless Chromium: viewport,
`color_scheme`, screenshot). If Playwright looks for browsers in an AppImage
cache, set `PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright`.

Gotchas that cost time before:
- The T3 Code `preview_*` tools timed out or failed on this machine; use
  Playwright.
- Re-reading an image at a path already read shows the **old** picture. Give
  every screenshot a fresh name (`shot-$(date +%s).png`); if a screenshot
  contradicts the logs, sample pixels with ImageMagick before believing it.
- `pkill -f <pattern>` / `pgrep -f … | xargs kill` match the Bash tool's own
  shell and kill it while the target survives. Read the PID with
  `pgrep -af '<pattern>'`, then `kill <pid>`. The project's guard hook blocks
  `pkill -f`.
- Flask without debug caches Jinja templates: restart after template edits,
  and confirm with a curl for a string only the new template has.
- A process started with `nohup … &` from the Bash tool can die when a later
  tool call is interrupted. For anything long-lived outside Docker, use
  `systemd-run --user --collect --unit=<name>-$(date +%s) -p KillMode=process`.

**Why:** Jason's test loop (Vireo 2026-08-27/28): he wants to see each change
running, quickly, not a description of it.
