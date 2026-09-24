# Memory index

- [No publishing until asked](no-publish-until-asked.md) — no push, release, docker push or issue reply until Jason says "ship it"
- [No AI attribution](no-ai-attribution.md) — STANDING RULE: Claude is never a contributor on any commit, tag, PR or release
- [Commit style](commit-style.md) — Conventional Commits, one-line body paragraphs, <=100 words, no em dashes
- [Strict SemVer](semver-strict.md) — warn Jason before tagging if the version doesn't fit the commits
- [Release cadence](release-cadence.md) — main -> beta (nightly-style) -> stable (weekly, on request); bare "ship it" = ask which
- [Ship flow](ship-flow.md) — prepare-release, push, release-notes, gh release, publish-image; CHANGELOG is the single record
- [Release branching](release-branching.md) — lazy stable-X.Y from the last tag for urgent patches only
- [Releases page trim](releases-page-trim.md) — newest per X.Y + current beta; confirm the first time per project
- [Issue replies](issue-replies.md) — "*Agentic reply:*", 1-2 sentences, no thanks, numbered asks
- [Contributor credit](contributor-credit.md) — noreply Co-Authored-By; @ only for code/art/translation contributors
- [Prose style](prose-style.md) — factual, no marketing or emoji, American spelling, docs shape, check-docs
- [Test loop](test-loop.md) — after every change: pytest + tools/redeploy.sh; Playwright; kill by PID
- [House hosting](house-hosting.md) — host 8000 is Portainer; apps map 8090+ -> 8000 (809x full, new apps 8100+); Docker Hub hyprlab/<app>
- [Design system](design-system.md) — Hyprfeed's UI: Inter, scarce accent, sidebar shell, fixed-height settings
- [Flask stack](flask-stack.md) — 1 gunicorn worker + threads, SQLite WAL, _migrate(), session CSRF, first account is admin
- [Template origin](template-origin.md) — started from the template at @TEMPLATE_DIR@; offer generic improvements back
