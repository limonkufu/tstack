# tstack

The agent skills I use every day, cleaned up so anyone can use them. They work
in Claude Code and Codex. Some use [T3 Code](https://github.com/pingdotgg/t3code)
features when they are available and fall back to native tools when they are
not.

This fork tracks [t3dotgg/tstack](https://github.com/t3dotgg/tstack) while keeping
the GitLab defaults and two-member council described below.

## Skills

| Skill | Say | What it does |
|---|---|---|
| `full-send` | "full send" | Takes a change to a merged PR with nobody watching: proves it, reviews it, files it, babysits it, merges it. |
| `full-stop` | "full stop" | Same as `full-send`, but stops when the PR is ready for you to merge. |
| `council` | "council" | Gets review from Claude and GPT Sol, and loops until they agree. |
| `sol-loop` | "sol loop" | Reviews a change with GPT Sol in a loop until both agents agree. |
| `file-pr` | "file an MR" or "file a PR" | Files a short MR or PR that leads with the problem, not an inventory of changes. |
| `takeover` | "take over" | Finishes someone else's PR, branch, or agent thread, and keeps their credit. |
| `babysit-pr` | "babysit" | Watches a PR through CI and review bots, and fixes the real findings. |
| `modernize` | "modernize" | Rebases an old PR and decides if it should still exist. |
| `leaving-pr-comments` | (automatic) | Formats comments that an agent posts on your behalf. |

GitLab merge requests via `glab` are the default across these workflows.
An explicit URL, repository remote, or user instruction selects the host;
GitHub repositories continue to use `gh`. Existing skill names and "PR"
triggers also work for GitLab MRs.

Some skills call others. Install the ones they need too:

- `full-send` uses `sol-loop`, `file-pr`, and `babysit-pr`.
- `full-stop` uses `full-send`.
- `takeover` uses `modernize`, `file-pr`, `babysit-pr`, and `leaving-pr-comments`.
- `file-pr`, `babysit-pr`, and `modernize` use `leaving-pr-comments`.

## Install

```bash
git clone https://github.com/limonkufu/tstack
git -C tstack remote add upstream https://github.com/t3dotgg/tstack
cp -R tstack/skills/* ~/.claude/skills/   # Claude Code
cp -R tstack/skills/* ~/.codex/skills/    # Codex
```

## Upstream updates

`origin` points to this fork; `upstream` points to the original repository.
From a clean checkout, fetch and review upstream changes before merging them:

```bash
git fetch upstream
git log --oneline HEAD..upstream/main
git merge upstream/main
git push origin main
```

Resolve any conflicts while preserving this fork's customizations, then run
the relevant checks before pushing. Recopy the skills after an update to use
the new versions in Claude Code or Codex.

## Requirements

- An authenticated [GitLab CLI](https://gitlab.com/gitlab-org/cli) (`glab`) for
  the default GitLab workflows, including nested groups and self-managed hosts.
- An authenticated [GitHub CLI](https://cli.github.com) (`gh`) when working
  with GitHub repositories.
- `python3` for `babysit-pr`'s `pr-wait` script.
- `council` and `sol-loop` need subagents on other providers' models. T3 Code
  does this with `delegate_task`. Otherwise you need a harness that can run
  those models.

## Make them yours

These are starting points. Edit them. Put personal settings, like which models
sit on your council, in your `CLAUDE.md` or `AGENTS.md`, so you can update the
skills without losing them.

## License

[MIT](LICENSE)
