---
name: file-pr
description: File a concise GitLab merge request or GitHub pull request. Use when the user asks to file, open, or create an MR or PR.
---

# File PR

Use GitLab via `glab` by default. An explicit URL, repository remote, or user
instruction selects the host; use `gh` for GitHub. Keep the existing skill name
and treat "PR" below as either host's review request. Do not send a GitHub
repository to GitLab. Use the selected CLI's credential helper; never put
credentials in commands, files, or URLs.

Before filing, check whether a PR for this branch already exists. Review the
diff locally against the actual target branch to make sure its contents match
the goal.

On GitLab, use `glab mr list --source-branch <branch> --output json` to find
an existing MR, and `glab mr view <iid> --output json` to read it. Use
`glab repo view --output json` to discover the project's default branch when
the user has not specified a target. Support nested groups and self-managed
hosts with `--repo <host/group/subgroup/project>` or a full repository URL.

PR titles usually become commit messages, so follow the repository's title
conventions. Look at recently merged PRs and Git history for examples. Prefer a
concise, human-readable title that explains why the change matters:

BAD

> ❌ perf(server): negotiate permessage-deflate on the websocket

GOOD

> ✅ perf(server): cut websocket frame size by 70%+ with gzipping

Open the description with a simple explanation of the problem based on the
user's original prompt, then briefly explain the solution. Do not lead with an
implementation inventory:

BAD

> ❌ Removed implicit workspace carry-over from every "new thread" entry point (cmd+n / cmd+shift+o, sidebar v1/v2 buttons, command palette). New threads inherit only the project from context; branch, worktree, and env mode always come from the configured defaults. Deleted buildContextualThreadOptions, startNewThreadInProjectFromContext, and the v1 sidebar's seed-context machinery.

GOOD

> ✅ My "new worktree" default was ignored when starting new threads on existing worktrees. Super unintuitive. Now your preferences always apply.

End the description with the public model name and harness that made the
changes, for example `Created with <model> in <harness>.` Include subagent
models that wrote part of the change. Use the model name the harness reports.
If model identity is unavailable, name the harness without guessing a model.

Before submission, check the title, description, quotes, and attachments for
secrets and private details.

Open a real MR rather than a draft so review bots run. Write the exact
description to a temporary file, then create or update it with:

```bash
glab mr create --source-branch <branch> --target-branch <base> --title <title> --description-file <file> --yes
glab mr update <iid> --title <title> --description-file <file>
```

On older `glab` versions without `--description-file`, use `glab api` with
`--input <json-file>` to create or update `projects/:fullpath/merge_requests`.
Use a JSON serializer for the body and include the IID on updates. Verify the
resulting URL, branches, title, and description by reading the MR back.

On GitHub, use `gh pr create --body-file <file>` or `gh pr edit --body-file <file>`.
If `gh pr create` fails because the GraphQL rate limit is used up, open it
through REST with
`gh api repos/<owner>/<repo>/pulls -f title=... -f head=... -f base=... -F body=@<file>`.
If the user also asked to babysit it, continue with the `babysit-pr` skill.

Do not post a follow-up PR comment unless it serves the user's request. When a
comment is needed, use the `leaving-pr-comments` skill.
