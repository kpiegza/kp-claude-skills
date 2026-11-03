#!/usr/bin/env python3
"""Collects the Jira context of a PR into one markdown file.

Finds the task key (branch name first, then PR title, then PR body), fetches the
task and its parent with comments (the parent lists the sibling sub-tasks) and
lists documentation links found in both. Jira is read only through an existing
`jira.py` CLI from an installed Claude Code plugin (or $KP_JIRA_SCRIPT).

    python3 task_context.py --branch "$BRANCH" --title "$TITLE" --body-file body.md --out task.md

Exit codes: 0 ok, 2 no jira.py found, 3 Jira unreachable, 4 no task key found.
"""

import argparse
import glob
import os
import re
import subprocess
import sys

KEY = re.compile(r"\b([A-Z][A-Z0-9]{1,15}-\d{1,6})\b")
NOT_JIRA = ("CVE-", "UTF-", "ISO-", "RFC-", "SHA-", "TLS-", "HTTP-")
LINK = re.compile(r"https?://[^\s\]|)>\"']*(?:confluence|wiki|docs\.google|notion)[^\s\]|)>\"']*", re.I)
TIMEOUT = 45


def find_jira_script():
    env = os.environ.get("KP_JIRA_SCRIPT")
    if env and os.path.isfile(env):
        return env
    root = os.path.expanduser("~/.claude/plugins")
    candidates = [
        p for p in glob.glob(os.path.join(root, "**", "scripts", "jira.py"), recursive=True)
        if "/.trash/" not in p and "/temp_" not in p
    ]
    # the synced copy is the one the running Claude Code session loads
    return max(candidates, key=lambda p: ("/synced/" in p, os.path.getmtime(p))) if candidates else None


def keys_in(text):
    found = []
    for key in KEY.findall((text or "").upper()):
        if not key.startswith(NOT_JIRA) and key not in found:
            found.append(key)
    return found


def fetch(script, key):
    try:
        res = subprocess.run(
            [sys.executable, script, "issue", key, "--comments"],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, f"timeout after {TIMEOUT}s"
    text = (res.stdout or "") + (res.stderr or "")
    if res.returncode != 0 or "Cannot connect to Jira" in text:
        return None, text.strip().splitlines()[-1] if text.strip() else f"exit {res.returncode}"
    return text.strip(), None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--branch", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--body-file")
    ap.add_argument("--key", help="task key to use instead of detecting one")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    body = open(args.body_file).read() if args.body_file else ""
    ordered = [args.key.upper()] if args.key else []
    for source in (args.branch, args.title, body):
        for key in keys_in(source):
            if key not in ordered:
                ordered.append(key)
    if not ordered:
        print("no task key in branch, title or body", file=sys.stderr)
        sys.exit(4)

    script = find_jira_script()
    if not script:
        print("no jira.py found under ~/.claude/plugins (set KP_JIRA_SCRIPT)", file=sys.stderr)
        sys.exit(2)

    primary = ordered[0]
    task, err = fetch(script, primary)
    if task is None:
        print(f"Jira unreachable for {primary}: {err}", file=sys.stderr)
        sys.exit(3)

    out = [f"# Task context for {primary}", "", "## Task", "", task, ""]
    parent_match = re.search(r"^Parent:\s+([A-Z][A-Z0-9]+-\d+)", task, re.M)
    parent_text = ""
    if parent_match:
        parent_text, perr = fetch(script, parent_match.group(1))
        out += [f"## Parent {parent_match.group(1)} (goal, agreements in comments, sibling sub-tasks)", ""]
        out += [parent_text or f"(not fetched: {perr})", ""]

    mentioned = [k for k in ordered[1:] if not parent_match or k != parent_match.group(1)]
    if mentioned:
        out += ["## Other keys mentioned in the branch, title or PR body", ""]
        out += [f"- {k}" for k in mentioned] + [""]

    links = sorted(set(LINK.findall(task + "\n" + (parent_text or "") + "\n" + body)))
    if links:
        out += ["## Documentation links (not fetched)", ""] + [f"- {u}" for u in links] + [""]

    with open(args.out, "w") as fh:
        fh.write("\n".join(out))
    print(f"task context: {args.out} (task {primary}" + (f", parent {parent_match.group(1)}" if parent_match else "") + ")")


if __name__ == "__main__":
    main()
