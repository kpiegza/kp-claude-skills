from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from helpers import PLUGIN_ROOT, import_kb, valid_note, write_note

kb = import_kb()
NOW = datetime(2026, 11, 11, 10, 0, 0)
TODAY = date(2026, 11, 11)
HOOKS_JSON = PLUGIN_ROOT / "hooks" / "hooks.json"


def payload(file_path, session_id="s1", cwd="/p"):
    return json.dumps(
        {"session_id": session_id, "cwd": cwd, "tool_name": "Read", "tool_input": {"file_path": str(file_path)}}
    )


class ReadsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "notes").mkdir()
        self.log = self.root / ".reads.log"

    def tearDown(self):
        self._tmp.cleanup()

    def run_main(self, argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(out), redirect_stderr(err):
            code = kb.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_logs_note_read(self):
        note = write_note(self.root, "x-y.md", *valid_note())
        self.assertTrue(kb.log_read(payload(note), self.root, NOW))
        self.assertEqual(self.log.read_text(encoding="utf-8"), "2026-11-11T10:00:00\tx-y\ts1\t/p\n")

    def test_ignores_non_note_paths(self):
        (self.root / "notes" / "sub").mkdir()
        candidates = [
            self.root / "INDEX.md",
            self.root / "notes" / "sub" / "a-b.md",
            self.root / "notes" / "x.png",
            Path("/etc/hosts"),
        ]
        for path in candidates:
            self.assertFalse(kb.log_read(payload(path), self.root, NOW), path)
        self.assertFalse(self.log.exists())

    def test_malformed_payload(self):
        for raw in ("not json", "{}", '{"tool_input": null}', "[]"):
            self.assertFalse(kb.log_read(raw, self.root, NOW), raw)
        self.assertFalse(self.log.exists())

    def test_log_read_cli_always_zero(self):
        stdin = payload("/nonexistent/kb/notes/x-y.md")
        code, out, err = self.run_main(["log-read", "--root", "/nonexistent/kb"], stdin)
        self.assertEqual((code, out, err), (0, "", ""))

    def write_stats_fixture(self):
        for name in ("a-x.md", "b-x.md", "c-x.md"):
            write_note(self.root, name, *valid_note())
        self.log.write_text(
            "2026-11-10T09:00:00\ta-x\ts1\t/p\n"
            "2026-11-10T09:05:00\ta-x\ts1\t/p\n"
            "2026-10-01T12:00:00\ta-x\ts2\t/q\n"
            "2026-08-03T12:00:00\tb-x\ts3\t/p\n"
            "garbage line\n",
            encoding="utf-8",
        )

    def test_stats_counts_distinct_sessions(self):
        self.write_stats_fixture()
        stats = kb.read_stats(self.root, TODAY, days=90)
        self.assertEqual(stats, [("a-x", 2, "2026-11-01"), ("b-x", 0, "2026-11-01"), ("c-x", 0, "2026-11-01")])

    def test_stats_cli_output(self):
        self.write_stats_fixture()
        code, out, _ = self.run_main(["stats", "--root", str(self.root), "--today", "2026-11-11"])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], "2\ta-x\t2026-11-01")
        self.assertEqual(lines[-1], "3 notes, 2 with 0 sessions in the last 90 days")

    def test_stats_missing_root(self):
        code, _, err = self.run_main(["stats", "--root", "/nonexistent/kb"])
        self.assertEqual(code, 2)
        self.assertIn("knowledge base not found: /nonexistent/kb", err)

    def hook(self):
        config = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        entry = config["hooks"]["PostToolUse"][0]
        return entry["matcher"], entry["hooks"][0]["command"]

    def test_hooks_json_points_to_script(self):
        matcher, command = self.hook()
        self.assertEqual(matcher, "Read")
        script = command.replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN_ROOT)).split('"')[1]
        self.assertTrue(Path(script).is_file(), script)

    def test_hook_command_end_to_end(self):
        note = write_note(self.root, "x-y.md", *valid_note())
        _, command = self.hook()
        env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT), "AGENT_KB_ROOT": str(self.root)}
        result = subprocess.run(["sh", "-c", command], input=payload(note), env=env, capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stdout), (0, ""), result.stderr)
        self.assertEqual(len(self.log.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
