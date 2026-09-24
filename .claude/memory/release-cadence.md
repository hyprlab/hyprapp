---
name: release-cadence
description: "RELEASE POLICY (from Hylki, 2026-09-24): work lands on main; 'Ship it to beta' = nightly-style X.(N+1).0-beta.K via the beta branch; 'Ship it to stable' = weekly-ish at Jason's word; patches only for urgent fixes; no catch-up betas; bare 'ship it' = ask which"
metadata:
  type: project
---

1. **Work lands on `main`.** Every user-visible change adds a line under
   `## Unreleased` in CHANGELOG.md.
2. **Beta is the gate, not a copy.** "Ship it to beta" merges main into the
   `beta` branch and publishes `X.(N+1).0-beta.K` (N = current stable minor,
   K counts up per beta), Docker `:beta`, GitHub prerelease. Whatever is on
   main, whenever Jason asks. Skill: `ship-beta`.
3. **Stable roughly weekly, only when Jason says so.** "Ship it to stable"
   promotes what the latest beta carried. If main has commits since that beta,
   ask whether to include them untested or cut a beta first. Skill:
   `ship-stable`.
4. **Patches only for urgent fixes:** crash, data loss, security, an instance
   that can't start or can't sign in. From the lazy `stable-X.Y` branch
   ([[release-branching]]); ship a beta from main alongside, so beta never
   lacks a fix stable has.
5. **No automatic catch-up beta after a stable.** The next beta after `1.N.0`
   is `1.(N+1).0-beta.1`, cut when asked.
6. **Bare "ship" / "ship it" is ambiguous: ask beta or stable.**
7. If the app has translations: string freeze between the beta that becomes
   the stable and the stable.

**Why:** Hylki shipped about twenty stables in one week (249 tags, 94 of them
betas), which left no time to test, tired users with update prompts, kept
translations behind, and made the beta a mirror of stable instead of a gate.
Urgent fixes stay fast through rule 4.

**How to apply:** versions per [[semver-strict]]; steps in docs/RELEASING.md
and [[ship-flow]]; issue replies per [[issue-replies]] (a beta fix is replied
to naming the beta, and the issue closes when the stable ships). Releases page
policy: [[releases-page-trim]].
