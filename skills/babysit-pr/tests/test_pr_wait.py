import copy
import importlib.machinery
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).parents[1] / "scripts" / "pr-wait"
LOADER = importlib.machinery.SourceFileLoader("pr_wait", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
pr_wait = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(pr_wait)


class GitLabTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        state = patch.object(pr_wait, "STATE_DIR", Path(temporary.name))
        state.start()
        self.addCleanup(state.stop)
        self.output = io.StringIO()
        stdout = redirect_stdout(self.output)
        stderr = redirect_stderr(io.StringIO())
        stdout.__enter__()
        stderr.__enter__()
        self.addCleanup(stdout.__exit__, None, None, None)
        self.addCleanup(stderr.__exit__, None, None, None)
        self.mr = {
            "state": "opened",
            "web_url": "https://gitlab.example.com/team/sub/project/-/merge_requests/42",
            "sha": "a" * 40,
            "target_branch": "release/next",
            "author": {"username": "author"},
            "detailed_merge_status": "mergeable",
            "draft": False,
            "has_conflicts": False,
            "head_pipeline": {
                "sha": "a" * 40,
                "status": "success",
                "web_url": "https://gitlab.example.com/pipeline/5",
            },
        }
        self.notes = []
        self.discussions = []

    def api(self, path, paginate=False):
        if path.endswith("?with_merge_status_recheck=true"):
            return copy.deepcopy(self.mr)
        if path == "user":
            return {"username": "agent"}
        if "/notes?" in path:
            self.assertTrue(paginate)
            return copy.deepcopy(self.notes)
        if "/discussions?" in path:
            self.assertTrue(paginate)
            return copy.deepcopy(self.discussions)
        if "/repository/branches/" in path:
            self.assertTrue(path.endswith("release%2Fnext"))
            return {"commit": {"id": "b" * 40}}
        self.fail(f"unexpected API call: {path}")

    def watcher(self, until="green", host="gitlab.example.com"):
        watcher = pr_wait.GitLabWatcher(host, "team/sub/project", 42, until, 5)
        watcher.api = self.api
        return watcher

    def assert_exit(self, watcher, code, message):
        with self.assertRaises(SystemExit) as stopped:
            watcher.poll()
        self.assertEqual(stopped.exception.code, code)
        self.assertIn(message, self.output.getvalue())

    def add_review(self):
        self.notes.append(
            {
                "id": 1,
                "body": f"Reviewed {self.mr['sha']}",
                "author": {"username": "greptile", "bot": True},
            }
        )

    def test_current_pipeline_becomes_green_after_stable_poll(self):
        watcher = self.watcher()
        watcher.poll()
        self.assert_exit(watcher, 0, "!42 green on aaaaaaa")

    def test_missing_stale_skipped_and_manual_pipelines_never_pass(self):
        for pipeline in (
            None,
            {"sha": "old", "status": "success"},
            {"sha": self.mr["sha"], "status": "skipped"},
            {"sha": self.mr["sha"], "status": "manual"},
        ):
            with self.subTest(pipeline=pipeline):
                self.mr["head_pipeline"] = pipeline
                watcher = self.watcher()
                watcher.poll()
                watcher.poll()
                self.assertNotIn("green on", self.output.getvalue())

    def test_failed_or_canceled_pipeline_needs_action(self):
        for status in ("failed", "canceled"):
            with self.subTest(status=status):
                self.mr["head_pipeline"]["status"] = status
                self.assert_exit(
                    self.watcher(), 1, "required check failed: GitLab pipeline"
                )

    def test_ready_requires_current_review(self):
        watcher = self.watcher("ready")
        watcher.poll()
        self.notes.append(
            {
                "id": 1,
                "body": "Reviewed an older commit",
                "author": {"username": "greptile"},
            }
        )
        watcher.poll()
        self.add_review()
        self.assert_exit(watcher, 0, "!42 ready on aaaaaaa")

    def test_approval_and_draft_blocks_are_not_ready(self):
        for changes in ({"detailed_merge_status": "not_approved"}, {"draft": True}):
            with self.subTest(changes=changes):
                original = copy.deepcopy(self.mr)
                self.mr.update(changes)
                self.add_review()
                watcher = self.watcher("ready")
                watcher.poll()
                self.assert_exit(watcher, 1, "GitLab merge gate blocked")
                self.mr = original

    def test_conflict_and_rebase_status_need_action(self):
        self.mr["has_conflicts"] = True
        self.assert_exit(self.watcher(), 1, "merge state is DIRTY")
        self.mr["has_conflicts"] = False
        self.mr["detailed_merge_status"] = "need_rebase"
        self.add_review()
        watcher = self.watcher("ready")
        watcher.poll()
        self.assert_exit(watcher, 1, "merge state is BEHIND")

    def test_unresolved_discussion_blocks_ready(self):
        self.add_review()
        self.discussions = [
            {
                "notes": [
                    {
                        "id": 2,
                        "body": "Please fix this",
                        "resolvable": True,
                        "resolved": False,
                        "author": {"username": "reviewer"},
                        "position": {"new_path": "app.py", "new_line": 8},
                    }
                ]
            }
        ]
        watcher = self.watcher("ready")
        watcher.poll()
        self.assert_exit(watcher, 1, "blocked by 1 unresolved threads")

    def test_any_change_reports_new_notes_and_remembers_them(self):
        watcher = self.watcher("any-change")
        watcher.poll()
        watcher.baseline = False
        self.notes.append(
            {"id": 3, "body": "A new finding", "author": {"username": "reviewer"}}
        )
        self.assert_exit(watcher, 0, "comment from reviewer: A new finding")
        restarted = self.watcher("any-change")
        restarted.poll()
        self.assertEqual(self.output.getvalue().count("comment from reviewer"), 1)

    def test_merged_and_closed_mrs_stop(self):
        for state, code, text in (
            ("merged", 0, "merged:"),
            ("closed", 1, "closed without merging:"),
        ):
            with self.subTest(state=state):
                self.mr["state"] = state
                self.assert_exit(self.watcher(), code, text)

    def test_state_is_separate_for_each_host_and_provider(self):
        first = self.watcher()
        second = self.watcher(host="other.example.com")
        github = pr_wait.Watcher("team/project", 42, "green", 5)
        self.assertEqual(len({first.path, second.path, github.path}), 3)

    def test_base_changes_report_overlap_including_renamed_files(self):
        watcher = self.watcher()
        watcher.api = Mock(
            side_effect=[
                [{"old_path": "before.py", "new_path": "after.py"}],
                {"diffs": [{"old_path": "before.py", "new_path": "before.py"}]},
            ]
        )
        self.assertEqual(watcher.base_overlap("head", "old", "new"), ["before.py"])

    def test_glab_uses_selected_host_and_parses_paginated_arrays(self):
        watcher = pr_wait.GitLabWatcher(
            "gitlab.example.com", "team/sub/project", 42, "green", 5
        )
        with patch.object(
            pr_wait, "cli", return_value=Mock(stdout='[{"id":1}]\n[{"id":2}]')
        ) as command:
            self.assertEqual(
                watcher.api(f"{watcher.endpoint}/notes", True), [{"id": 1}, {"id": 2}]
            )
        command.assert_called_once_with(
            "glab",
            [
                "api",
                "--hostname",
                "gitlab.example.com",
                "projects/team%2Fsub%2Fproject/merge_requests/42/notes",
                "--paginate",
            ],
        )

    def test_main_watches_gitlab_through_glab(self):
        self.add_review()

        def command(args, **kwargs):
            self.assertEqual(
                args[:4], ["glab", "api", "--hostname", "gitlab.example.com"]
            )
            data = self.api(args[4], "--paginate" in args)
            return Mock(returncode=0, stdout=json.dumps(data), stderr="")

        with (
            patch.object(pr_wait.subprocess, "run", side_effect=command),
            patch.object(pr_wait.sys, "argv", ["pr-wait", self.mr["web_url"]]),
            patch.object(pr_wait.time, "sleep"),
            self.assertRaises(SystemExit) as stopped,
        ):
            pr_wait.main()
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn("!42 ready on", self.output.getvalue())

    def test_authentication_failure_stops_without_reporting_green(self):
        watcher = self.watcher()
        watcher.api = Mock(side_effect=pr_wait.GhError("401 Unauthorized", False))
        with self.assertRaises(SystemExit) as stopped:
            watcher.run()
        self.assertEqual(stopped.exception.code, 1)
        self.assertIn("pr-wait stopped: 401 Unauthorized", self.output.getvalue())
        self.assertNotIn("green on", self.output.getvalue())

    def test_github_green_behavior_is_preserved(self):
        watcher = pr_wait.Watcher("owner/repo", 42, "green", 5)
        watcher.fetch_pr = Mock(
            return_value={
                "state": "OPEN",
                "url": "https://github.com/owner/repo/pull/42",
                "baseRefName": "main",
                "headRefOid": "a" * 40,
                "author": {"login": "author"},
                "viewer": "agent",
                "comments": {"nodes": []},
                "reviews": {"nodes": []},
                "reviewThreads": {"nodes": []},
                "mergeStateStatus": "CLEAN",
            }
        )
        watcher.required_checks = Mock(return_value={"test"})
        watcher.fetch_checks = Mock(
            return_value={"test": {"bucket": "pass", "link": ""}}
        )
        watcher.poll()
        self.assert_exit(watcher, 0, "#42 green on aaaaaaa")


class TargetTests(unittest.TestCase):
    def test_github_repository_urls_keep_using_gh(self):
        with patch.object(pr_wait, "gh", return_value=Mock(stdout="")) as command:
            self.assertEqual(
                pr_wait.parse_target("42", "https://github.com/owner/repo.git"),
                ("owner/repo", 42),
            )
        command.assert_called_once_with(
            ["pr", "view", "42", "-R", "owner/repo", "--json", "number"]
        )

    def test_gitlab_is_default_but_explicit_hosts_and_github_checkouts_win(self):
        with patch.object(pr_wait, "remote_url", return_value=""):
            self.assertEqual(pr_wait.provider_for("42", None, None, None), "gitlab")
        with patch.object(
            pr_wait, "remote_url", return_value="git@github.com:owner/repo.git"
        ):
            self.assertEqual(pr_wait.provider_for("42", None, None, None), "github")
            self.assertEqual(
                pr_wait.provider_for("42", "team/sub/project", None, None), "gitlab"
            )
            self.assertEqual(pr_wait.provider_for("42", None, "gitlab", None), "gitlab")
        self.assertEqual(
            pr_wait.provider_for("https://github.com/o/r/pull/42", None, None, None),
            "github",
        )
        self.assertEqual(
            pr_wait.provider_for(
                "https://gitlab.example.com/g/r/-/merge_requests/42", None, None, None
            ),
            "gitlab",
        )

    def test_gitlab_url_preserves_host_nested_path_and_iid(self):
        self.assertEqual(
            pr_wait.parse_gitlab_target(
                "https://gitlab.example.com/team/sub/project/-/merge_requests/42#note_1",
                None,
                None,
            ),
            ("gitlab.example.com", "team/sub/project", 42),
        )

    def test_numeric_target_uses_ssh_checkout(self):
        with patch.object(
            pr_wait,
            "remote_url",
            return_value="ssh://git@gitlab.example.com:2222/team/sub/project.git",
        ):
            self.assertEqual(
                pr_wait.parse_gitlab_target("!42", None, None),
                ("gitlab.example.com", "team/sub/project", 42),
            )

    def test_bad_numbers_and_mismatched_hosts_are_rejected(self):
        with redirect_stdout(io.StringIO()):
            for number in (None, "0", "nonsense"):
                with self.subTest(number=number), self.assertRaises(SystemExit):
                    pr_wait.parse_gitlab_target(number, "team/project", None)
            with self.assertRaises(SystemExit):
                pr_wait.parse_gitlab_target(
                    "https://one.example.com/team/project/-/merge_requests/42",
                    None,
                    "two.example.com",
                )


if __name__ == "__main__":
    unittest.main()
