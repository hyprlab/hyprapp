---
name: semver-strict
description: "Strict SemVer 2.0.0 for every release; before tagging, check the commits since the last tag and WARN Jason plainly if the proposed version doesn't fit and what SemVer calls for; he decides"
metadata:
  type: feedback
---

Every release follows https://semver.org/ strictly. Before any release (beta,
stable or patch), read the commits since the last tag and **warn Jason
plainly, before tagging, if the version he asked for (or the one the recipe
would produce) does not fit.** Do not silently pick another number: say what
doesn't fit and what SemVer calls for, then let him decide.

For an app the "public API" is what an existing install depends on:
- **MAJOR:** a migration an older version can't read back, a removed feature
  or setting, a renamed or removed environment variable, a changed URL others
  link to, a changed volume path or port. Flag these even if he calls it minor.
- **MINOR:** new backward-compatible functionality (feature, setting, page,
  command, optional env var) or a deprecation. Patch resets to 0.
- **PATCH:** backward-compatible fixes only. A week with no features is a
  patch, not `1.x.0`.

**Why:** Jason asked for strict adherence (Hylki, 2026-09-24). The weekly
stable habit assumed every stable was `1.x.0`, which is only right when the
week had a feature.

**How to apply:** `tools/next-version.sh --why` computes the bump from the
Conventional Commit types ([[commit-style]]) and `tools/prepare-release.sh`
refuses a mismatch unless `FORCE_VERSION=1`. The tool can't see a `fix` that
breaks the schema, so read the commits too. Cadence: [[release-cadence]].
