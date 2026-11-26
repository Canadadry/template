"""Unit tests for the progress.md hook: progress_check.py, and
progress_check.sh driving it from git. Host only: the git tests make their
own repository in a temporary directory. Run: make test-template"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK_PY = ROOT / "scripts" / "progress_check.py"
CHECK_SH = ROOT / "scripts" / "progress_check.sh"

BASE = """\
- [ ] 1 Phase 1 — First
  - [x] 1.1 Step one
  - [x] 1.2 Step two
  - [ ] 1.3 Step three
- [ ] 2 Phase 2 — Second
  - [ ] 2.1 Step four
"""


def check(old, new):
    """Return (exit code, stderr) of progress_check.py on two texts."""
    with tempfile.TemporaryDirectory() as tmp:
        new_path = Path(tmp) / "new"
        new_path.write_text(new)
        old_arg = "-"
        if old is not None:
            old_path = Path(tmp) / "old"
            old_path.write_text(old)
            old_arg = str(old_path)
        result = subprocess.run(
            [sys.executable, str(CHECK_PY), old_arg, str(new_path)],
            capture_output=True, text=True,
        )
        return result.returncode, result.stderr


class FileTest(unittest.TestCase):
    def test_numbered_list_is_accepted(self):
        self.assertEqual(check(None, BASE)[0], 0)

    def test_missing_number_is_refused(self):
        code, err = check(None, "- [ ] 1 Phase\n  - [ ] Step one\n")
        self.assertEqual(code, 1)
        self.assertIn("<number>", err)

    def test_wrong_number_is_refused(self):
        code, err = check(None, "- [ ] 1 Phase\n  - [ ] 1.1 A\n  - [ ] 1.3 B\n")
        self.assertEqual(code, 1)
        self.assertIn("should be numbered 1.2", err)

    def test_child_number_must_extend_its_parent(self):
        code, err = check(None, "- [ ] 1 Phase\n- [ ] 2 Phase\n  - [ ] 1.1 A\n")
        self.assertEqual(code, 1)
        self.assertIn("should be numbered 2.1", err)

    def test_hole_is_refused(self):
        code, err = check(None, "- [ ] 1 P\n  - [ ] 1.1 A\n  - [x] 1.2 B\n")
        self.assertEqual(code, 1)
        self.assertIn("1.2 is [x] while 1.1, before it, is [ ]", err)

    def test_hole_across_phases_is_refused(self):
        code, _ = check(None, "- [ ] 1 P\n  - [ ] 1.1 A\n- [ ] 2 Q\n  - [x] 2.1 B\n")
        self.assertEqual(code, 1)

    def test_parent_done_with_open_child_is_refused(self):
        code, err = check(None, "- [x] 1 P\n  - [ ] 1.1 A\n")
        self.assertEqual(code, 1)
        self.assertIn("1 is [x] while one of its children is [ ]", err)


class ChangeTest(unittest.TestCase):
    def test_tick_next_item_is_accepted(self):
        self.assertEqual(check(BASE, BASE.replace("[ ] 1.3", "[x] 1.3"))[0], 0)

    def test_tick_with_a_hole_is_refused(self):
        self.assertEqual(check(BASE, BASE.replace("[ ] 2.1", "[x] 2.1"))[0], 1)

    def test_fix_inserted_where_we_are_shifts_the_open_items(self):
        new = BASE.replace(
            "  - [ ] 1.3 Step three\n",
            "  - [x] 1.3 Fix of 1.2\n  - [ ] 1.4 Step three\n",
        )
        self.assertEqual(check(BASE, new), (0, ""))

    def test_new_line_before_an_existing_x_is_refused(self):
        new = BASE.replace(
            "  - [x] 1.1 Step one\n  - [x] 1.2 Step two\n",
            "  - [x] 1.1 Step one\n  - [x] 1.2 Fix\n  - [x] 1.3 Step two\n",
        ).replace("1.3 Step three", "1.4 Step three")
        code, err = check(BASE, new)
        self.assertEqual(code, 1)
        self.assertIn("[x] line changed", err)

    def test_renaming_an_open_item_is_refused(self):
        new = BASE.replace("[x] 1.2 Step two\n  - [ ] 1.3 Step three", "[x] 1.2 Step two\n  - [x] 1.3 Other")
        code, err = check(BASE, new)
        self.assertEqual(code, 1)
        self.assertIn("removed, renamed or moved", err)

    def test_untick_is_refused(self):
        self.assertEqual(check(BASE, BASE.replace("[x] 1.2", "[ ] 1.2"))[0], 1)

    def test_no_new_tick_is_refused(self):
        code, err = check(BASE, BASE)
        self.assertEqual(code, 1)
        self.assertIn("ticks no new [x]", err)


class HookTest(unittest.TestCase):
    """progress_check.sh run as git's prepare-commit-msg hook."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.stage(BASE)
        self.git("commit", "-q", "-m", "base")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, env=self.env, check=True)

    def stage(self, text):
        Path(self.repo, "progress.md").write_text(text)
        self.git("add", "progress.md")

    def hook(self):
        return subprocess.run(
            ["sh", str(CHECK_SH), ".git/COMMIT_EDITMSG", "message"],
            cwd=self.repo, env=self.env, capture_output=True, text=True,
        ).returncode

    def test_a_tick_is_accepted(self):
        self.stage(BASE.replace("[ ] 1.3", "[x] 1.3"))
        self.assertEqual(self.hook(), 0)

    def test_a_hole_is_refused(self):
        self.stage(BASE.replace("[ ] 2.1", "[x] 2.1"))
        self.assertEqual(self.hook(), 1)

    def test_deleting_with_open_items_is_refused(self):
        self.git("rm", "-q", "progress.md")
        self.assertEqual(self.hook(), 1)


if __name__ == "__main__":
    unittest.main()
