---
name: leaving-pr-comments
description: Use whenever leaving comments on GitLab merge requests or GitHub pull requests.
---

# Leaving PR Comments

Use GitLab via `glab` by default; honor an explicit host or repository remote
and use `gh` on GitHub. Prefix every agent-authored comment left on the user's
behalf with this Markdown note:

```md
> [!NOTE]
> 🤖 **<model> responding on behalf of <user>**

Actual comment starts here.
```

Use the verified public name of the model that wrote the comment, and the
user's name or verified GitLab/GitHub login (`glab api user` or `gh api user`).

If the harness does not expose a model name, use the harness name. Do not guess.

Before posting, check the entire comment, including quoted text and
attachments, for secrets and private details.

Keep the attribution inside the note and the actual reply outside it. The
context line must start with the robot emoji. Do not add a horizontal rule,
Setext underline, heading, signature footer, or a second attribution.

Apply this format to top-level MR/PR comments, inline review comments, replies to
bots or reviewers, and written explanations used before resolving or
dismissing feedback. Do not add it to PR descriptions, commit messages, or text
the user explicitly asked to post verbatim without attribution.

Write the comment itself in a direct style:

- Lead with the conclusion.
- Cite the relevant code, behavior, check, or reproduction.
- Keep it concise and avoid filler, canned thanks, or status narration.
- Distinguish verified facts from judgment.

On GitLab, post top-level notes with `glab api --method POST
projects/:fullpath/merge_requests/<iid>/notes --input <json-file>`, with the
exact Markdown in the JSON `body` field. Use the MR's `discussions` API for
inline comments, thread replies, and resolution; reply within the existing
discussion instead of creating a new top-level note. On GitHub, use `gh`.
Keep credentials in the CLI's credential helper or environment.

Preview the final Markdown before posting so quoting and blank lines render as
shown. Read back the posted note or review and verify its body and location.
GitLab note links use `<mr-url>#note_<note-id>` when the API returns no URL.
Resolve a review thread only after its response was posted successfully.
