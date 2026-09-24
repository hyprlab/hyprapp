---
name: no-publish-until-asked
description: "Never push to GitHub or Docker Hub, create a release, or comment on/close issues until Jason says \"ship it\" or asks for that exact action; commit locally and say what is ready"
metadata:
  type: feedback
---

Do not `git push`, `docker push`, `gh release create`, or reply to or close
issues and pull requests on your own initiative. Local commits and rebuilding
Jason's local container are fine. Publishing happens only when Jason says
"ship it" (see [[release-cadence]]) or explicitly asks for that action.

**Why:** Jason tests every change on the running app before it becomes public.
Earlier Hyprfeed sessions pushed every change at once, and in Hylki a README
edit was pushed to main because "update the README on GitHub" seemed to imply
it; Jason had it reverted with a force-push.

**How to apply:** after a change, commit locally, rebuild the local container
([[test-loop]]), and say what is ready to ship. A request to change something
"on GitHub" does not authorize pushing main: ask how, or offer to push that
one commit separately. When he says ship, push everything pending as part of
the release ([[ship-flow]]).
