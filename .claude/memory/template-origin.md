---
name: template-origin
description: "This app started from the Hyprapp template at @TEMPLATE_DIR@ (Hyprfeed's UI + Hylki's conventions). Generic improvements (auth, shell, tools, hooks, docs checker) are worth offering back to the template"
metadata:
  type: project
---

Hyprapp was created from the Hyprlab Flask template at `@TEMPLATE_DIR@`
with `tools/init-project.sh`. The template combines Hyprfeed's interface and
Flask machinery with Hylki's conventions (SemVer, beta and stable channels, no
AI attribution, Conventional Commits, the documentation shape).

**How to apply:** when a change here improves something generic (the shell,
accounts, admin, the design system, `tools/`, the git hooks, the Claude hooks
or skills), mention that it could also go into the template, so the next app
starts with it. Don't edit the template without being asked.
