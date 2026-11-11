from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

from helpers import import_kb, valid_note, write_note

kb = import_kb()
TODAY = date(2026, 11, 11)


def pad_to_words(body: list[str], total: int) -> list[str]:
    """Append filler words so the body has exactly `total` words."""
    missing = total - len(" ".join(body).split())
    return body + [" ".join(["słowo"] * missing)]


class LintTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "notes").mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name="postgres-queue-skip-locked.md", type_="decision", meta=None, body=None, drop=(), **kwargs):
        default_meta, default_body = valid_note(type_)
        default_meta.update(meta or {})
        for key in drop:
            default_meta.pop(key)
        return write_note(self.root, name, default_meta, default_body if body is None else body, **kwargs)

    def issues(self):
        return kb.lint_repo(self.root, TODAY)

    def assertIssue(self, level, text, issues=None):
        issues = self.issues() if issues is None else issues
        self.assertTrue(
            any(i.level == level and text in i.message for i in issues),
            f"expected {level} containing {text!r}, got {issues}",
        )

    def test_valid_notes_have_no_issues(self):
        self.write("postgres-queue-skip-locked.md", "decision")
        self.write("pgbouncer-advisory-lock.md", "gotcha")
        self.write("bun-test-vs-vitest.md", "finding")
        self.assertEqual(self.issues(), [])

    def test_missing_frontmatter(self):
        write_note(self.root, "postgres-queue-skip-locked.md", None, valid_note()[1])
        self.assertIssue("ERROR", "no frontmatter")

    def test_missing_field(self):
        self.write(drop=("when",))
        self.assertIssue("ERROR", "missing field: when")

    def test_unknown_field(self):
        self.write(meta={"tags": "x"})
        self.assertIssue("ERROR", "unknown field: tags")

    def test_invalid_type(self):
        self.write(meta={"type": "note"})
        self.assertIssue("ERROR", "invalid type: note")

    def test_invalid_proof(self):
        self.write(meta={"proof": "maybe"})
        self.assertIssue("ERROR", "invalid proof: maybe")

    def test_invalid_checked(self):
        self.write(meta={"checked": "11-11-2026"})
        self.assertIssue("ERROR", "invalid checked date: 11-11-2026")

    def test_future_checked(self):
        self.write(meta={"checked": "2026-12-01"})
        self.assertIssue("ERROR", "checked date in the future: 2026-12-01")

    def test_when_too_long(self):
        self.write(meta={"when": "a" * 121})
        self.assertIssue("ERROR", "when longer than 120 chars")

    def test_when_polish_120_chars_ok(self):
        self.write(meta={"when": "ą" * 120})
        self.assertEqual(self.issues(), [])

    def test_body_too_long(self):
        self.write(body=pad_to_words(valid_note()[1], 151))
        self.assertIssue("ERROR", "body has 151 words (max 150)")

    def test_body_150_words_ok(self):
        self.write(body=pad_to_words(valid_note()[1], 150))
        self.assertEqual(self.issues(), [])

    def test_missing_title(self):
        self.write(body=["Decyzja bez tytułu"] + valid_note()[1][1:])
        self.assertIssue("ERROR", "first body line must be a '# ' title")

    def test_missing_section(self):
        body = [line for line in valid_note("gotcha")[1] if not line.startswith("**Przyczyna:**")]
        self.write("pgbouncer-advisory-lock.md", "gotcha", body=body)
        self.assertIssue("ERROR", "missing section: Przyczyna")

    def test_read_requires_source(self):
        self.write(meta={"proof": "read"})
        self.assertIssue("ERROR", "proof: read requires a 'Źródło:' line")
        self.write(meta={"proof": "read"}, body=valid_note()[1] + ["Źródło: https://example.com"])
        self.assertEqual(self.issues(), [])

    def test_invalid_filename(self):
        self.write("Postgres_Queue.md")
        self.write("postgres.md")
        issues = self.issues()
        for name in ("Postgres_Queue.md", "postgres.md"):
            matching = [i for i in issues if i.file == f"notes/{name}" and "invalid filename" in i.message]
            self.assertEqual(len(matching), 1, issues)

    def test_stale_warning(self):
        self.write("pgbouncer-advisory-lock.md", "gotcha", meta={"checked": "2026-05-01"})
        self.write("postgres-queue-skip-locked.md", "decision", meta={"checked": "2026-05-01"})
        issues = self.issues()
        gotcha = [i for i in issues if i.file == "notes/pgbouncer-advisory-lock.md"]
        decision = [i for i in issues if i.file == "notes/postgres-queue-skip-locked.md"]
        self.assertIssue("WARN", "stale: checked 194 days ago (max 180)", gotcha)
        self.assertEqual(decision, [])

    def test_duplicate_prefix_warning(self):
        for suffix in ("a-x", "b-x", "c-x"):
            self.write(f"postgres-{suffix}.md")
        self.assertEqual(self.issues(), [])
        self.write("postgres-d-x.md")
        warnings = [i for i in self.issues() if i.level == "WARN"]
        self.assertEqual(len(warnings), 1, warnings)
        self.assertEqual(warnings[0].file, "notes/postgres-*")
        self.assertIn("possible duplicates: 4 notes with prefix 'postgres'", warnings[0].message)

    def test_crlf_and_bom(self):
        self.write(newline="\r\n", bom=True)
        self.assertEqual(self.issues(), [])

    def test_colon_in_value(self):
        path = self.write(meta={"when": "wybór: A czy B"})
        self.assertEqual(kb.parse_note(path).meta["when"], "wybór: A czy B")

    def test_ignores_non_md_and_subdirs(self):
        self.write()
        notes = self.root / "notes"
        (notes / ".DS_Store").write_bytes(b"\x00\x01")
        (notes / "img").mkdir()
        (notes / "img" / "x.png").write_bytes(b"\x89PNG")
        (notes / "sub").mkdir()
        (notes / "sub" / "x.md").write_text("broken", encoding="utf-8")
        self.assertEqual(self.issues(), [])

    def test_default_root_env(self):
        with mock.patch.dict(os.environ, {"AGENT_KB_ROOT": "/tmp/x"}):
            self.assertEqual(kb.default_root(), Path("/tmp/x"))
        with mock.patch.dict(os.environ):
            os.environ.pop("AGENT_KB_ROOT", None)
            self.assertEqual(kb.default_root(), Path.home() / "Projekty" / "agent-knowledge-base")

    def run_lint(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = kb.main(["lint", "--root", str(self.root), "--today", "2026-11-11"])
        return code, out.getvalue().splitlines()

    def test_lint_exit_codes(self):
        broken = self.write(drop=("when",))
        code, lines = self.run_lint()
        self.assertEqual(code, 1)
        self.assertEqual(lines[-1], "1 errors, 0 warnings")
        broken.unlink()
        self.write("pgbouncer-advisory-lock.md", "gotcha", meta={"checked": "2026-05-01"})
        code, lines = self.run_lint()
        self.assertEqual(code, 0)
        self.assertEqual(lines[-1], "0 errors, 1 warnings")


if __name__ == "__main__":
    unittest.main()
