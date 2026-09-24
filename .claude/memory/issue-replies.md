---
name: issue-replies
description: "GitHub issue/PR replies: start with '*Agentic reply:*' + blank line; done-replies are 1-2 sentences naming the version; no thanks; asks as a numbered list; no em dashes; beta fixes stay open until stable; reply after the image is pushed"
metadata:
  type: feedback
---

- **Every reply to an issue or PR begins with `*Agentic reply:*`** (italics),
  then a blank line, then the reply, so readers know an agent wrote it.
- A reply saying something is done is **one or two sentences**: what changed,
  from the user's side, and which version carries it. Internals belong in the
  commit and the changelog.
- **Do not thank the user.** Plain, brief, human-sounding.
- **Anything the user must do is a numbered list**, one request per item
  (export a log, try X, check a setting), so the reply clearly expects action.
- **No em dashes** in any GitHub comment, review or discussion reply.
- A fix in a **beta**: name the beta version, say it reaches stable with the
  next weekly release, and leave the issue open until that stable ships.
- A fix in a **stable**: reply once the image is pushed, with the update
  command as its own paragraph, then close.
- If Jason says he will answer an issue himself, leave it alone and open.

```
*Agentic reply:*

Fixed in 1.4.0: the sign-in page now returns you to the page you asked for.

Update with `docker compose pull && docker compose up -d`.
```

**Why:** Jason wants replies that read like a person wrote them, short and not
effusive or technical, and wants readers told up front an agent wrote them
(Hylki, 2026-09-22/23).

**How to apply:** credit for contributed work is separate and still applies
([[contributor-credit]]); it just isn't a thank-you line. Only replies that ask
for something or explain a decline run longer.
