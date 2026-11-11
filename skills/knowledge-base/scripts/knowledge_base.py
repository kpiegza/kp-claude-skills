#!/usr/bin/env python3
"""Checks the structure of the private agent knowledge base (kp:knowledge-base).

Usage:
    python3 knowledge_base.py lint [--root PATH] [--today YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ALLOWED_FIELDS = ("type", "when", "applies", "checked", "proof")
ALLOWED_TYPES = ("decision", "gotcha", "finding")
ALLOWED_PROOFS = ("tested", "read")
REQUIRED_SECTIONS = {
    "decision": ("Decyzja", "Dlaczego", "Odrzucone"),
    "gotcha": ("Objaw", "Przyczyna", "Rozwiązanie"),
    "finding": ("Pytanie", "Wniosek", "Dlaczego"),
}
STALE_TYPES = ("gotcha", "finding")
SOURCE_PREFIX = "Źródło:"
MAX_BODY_WORDS = 150
MAX_WHEN = 120
STALE_DAYS = 180
DUP_THRESHOLD = 3
FILENAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+\.md$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def default_root() -> Path:
    """Knowledge base location: $AGENT_KB_ROOT or ~/Projekty/agent-knowledge-base."""
    env = os.environ.get("AGENT_KB_ROOT")
    if env:
        return Path(env)
    return Path.home() / "Projekty" / "agent-knowledge-base"


@dataclass
class Note:
    path: Path
    meta: dict[str, str]
    body: list[str]


class NoteParseError(Exception):
    pass


@dataclass
class Issue:
    level: str
    file: str
    message: str


def parse_note(path: Path) -> Note:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        raise NoteParseError("no frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise NoteParseError("no frontmatter")
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        key, sep, value = line.partition(": ")
        if not sep:
            key, value = line.rstrip().rstrip(":"), ""
        meta[key.strip()] = value.strip()
    return Note(path=path, meta=meta, body=lines[end + 1 :])


def iter_note_paths(root: Path) -> list[Path]:
    return sorted(p for p in (root / "notes").glob("*.md") if p.is_file())


def _parse_date(value: str | None) -> date | None:
    if value is None or not DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def lint_note(note: Note, today: date) -> list[Issue]:
    rel = f"notes/{note.path.name}"
    issues: list[Issue] = []

    def error(message: str) -> None:
        issues.append(Issue("ERROR", rel, message))

    meta = note.meta
    for field in ALLOWED_FIELDS:
        if field not in meta:
            error(f"missing field: {field}")
    for field in meta:
        if field not in ALLOWED_FIELDS:
            error(f"unknown field: {field}")

    type_ = meta.get("type")
    if type_ is not None and type_ not in ALLOWED_TYPES:
        error(f"invalid type: {type_}")
    proof = meta.get("proof")
    if proof is not None and proof not in ALLOWED_PROOFS:
        error(f"invalid proof: {proof}")

    checked = _parse_date(meta.get("checked"))
    if "checked" in meta:
        if checked is None:
            error(f"invalid checked date: {meta['checked']}")
        elif checked > today:
            error(f"checked date in the future: {meta['checked']}")

    when = meta.get("when")
    if when is not None and len(when) > MAX_WHEN:
        error(f"when longer than {MAX_WHEN} chars")

    non_blank = [line for line in note.body if line.strip()]
    if not non_blank or not non_blank[0].startswith("# "):
        error("first body line must be a '# ' title")
    words = len(" ".join(note.body).split())
    if words > MAX_BODY_WORDS:
        error(f"body has {words} words (max {MAX_BODY_WORDS})")
    for label in REQUIRED_SECTIONS.get(type_ or "", ()):
        if not any(line.startswith(f"**{label}:**") for line in note.body):
            error(f"missing section: {label}")
    if proof == "read" and not any(line.startswith(SOURCE_PREFIX) for line in note.body):
        error(f"proof: read requires a '{SOURCE_PREFIX}' line")

    if type_ in STALE_TYPES and checked is not None and checked <= today:
        age = (today - checked).days
        if age > STALE_DAYS:
            issues.append(Issue("WARN", rel, f"stale: checked {age} days ago (max {STALE_DAYS})"))
    return issues


def lint_repo(root: Path, today: date) -> list[Issue]:
    issues: list[Issue] = []
    prefixes: Counter[str] = Counter()
    for path in iter_note_paths(root):
        rel = f"notes/{path.name}"
        if not FILENAME_RE.match(path.name):
            issues.append(
                Issue("ERROR", rel, "invalid filename (expected <technology>-<topic>.md, lowercase kebab-case)")
            )
        try:
            note = parse_note(path)
        except NoteParseError as exc:
            issues.append(Issue("ERROR", rel, str(exc)))
        else:
            issues.extend(lint_note(note, today))
        prefixes[path.stem.split("-", 1)[0]] += 1
    for prefix, count in sorted(prefixes.items()):
        if count > DUP_THRESHOLD:
            issues.append(
                Issue("WARN", f"notes/{prefix}-*", f"possible duplicates: {count} notes with prefix '{prefix}'")
            )
    return issues


def _print_issues(issues: list[Issue]) -> int:
    for issue in issues:
        print(f"{issue.level} {issue.file}: {issue.message}")
    errors = sum(1 for issue in issues if issue.level == "ERROR")
    print(f"{errors} errors, {len(issues) - errors} warnings")
    return errors


def cmd_lint(root: Path, today: date) -> int:
    return 1 if _print_issues(lint_repo(root, today)) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="knowledge_base.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    lint = commands.add_parser("lint", help="report structural errors and warnings")
    lint.add_argument("--root", type=Path, default=None, help="knowledge base directory")
    lint.add_argument("--today", type=date.fromisoformat, default=None, help="override today (YYYY-MM-DD)")
    args = parser.parse_args(argv)

    root = args.root or default_root()
    today = args.today or date.today()
    if args.command == "lint":
        return cmd_lint(root, today)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
