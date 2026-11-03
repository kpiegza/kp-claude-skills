#!/usr/bin/env python3
"""Mechanical context pack for a code review (no LLM).

For the code changed between two git refs it collects what a reviewer usually
has to look up outside the diff: usages of changed symbols and keys in other
files (with the enclosing function), signatures of called functions defined in
the repo, sibling files (other workflows, env overlays, files of the same kind)
with the changed keys, the CLAUDE.md chain, and versions of imported packages.

Run from the repository root:
    python3 context_pack.py --base origin/main --head refs/kp-review/1234 --out pack.md
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict

SKIP_FILE = re.compile(
    r"(^|/)(node_modules|dist|build|coverage|\.next|vendor)/"
    r"|\.(lock|snap|svg|png|jpe?g|gif|ico|pdf|min\.js|map)$"
    r"|(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|poetry\.lock|uv\.lock)$"
)
CHANGELOG = re.compile(r"(^|/)(CHANGELOG|CHANGES|HISTORY)[^/]*$", re.I)
CONFIG_EXT = (".yml", ".yaml", ".json", ".toml", ".ini", ".env", ".properties", ".tf")
STOP = set("""
constructor async await return function const this then catch push map filter reduce
length toString describe expect test mock jest spyOn beforeEach afterEach should
log warn error info debug get set has find keys values entries default export import
from require module exports string number boolean object null undefined true false
self None True False print len list dict str int float type value data result item
items name id key args kwargs props state config options params name version true
resolve reject promise process console window document event events message payload
""".split())

DEF_PATTERNS = [
    re.compile(r"\b(?:function|class|interface|type|enum)\s+([A-Za-z_]\w{3,})"),
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w{3,})"),
    re.compile(
        r"^\s*(?:(?:export|public|private|protected|static|async|override|readonly)\s+)*"
        r"([A-Za-z_]\w{3,})\s*(?:<[^>()]*>)?\s*\([^)]*\)?\s*(?::[^=]*)?\{?\s*$"
    ),
    re.compile(r"(?:export\s+)?const\s+([A-Za-z_]\w{3,})\s*=\s*(?:async\s*)?\("),
]
CONTROL = {"if", "for", "while", "switch", "catch", "return", "elif", "with", "else"}
STRING_KEY = re.compile(r"['\"`]([a-z][a-z0-9_-]*(?:\.[a-z0-9_*#-]+){1,})['\"`]")
CONSTANT = re.compile(r"\b([A-Z][A-Z0-9]*_[A-Z0-9_]{2,})\b")
YAML_KEY = re.compile(r"^\s*-?\s*([A-Za-z_][\w.-]{2,})\s*:")
SQL_COL = re.compile(r"(?:ADD|DROP|ALTER|RENAME)\s+COLUMN\s+\"?(\w+)\"?", re.I)
SQL_TABLE = re.compile(r"(?:ALTER|CREATE)\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\"?(\w+)\"?", re.I)
CALL = re.compile(r"\.([A-Za-z_]\w{3,})\s*(?:<[^>()]*>)?\(")
TS_IMPORT = re.compile(r"""from\s+['"]([^'"./][^'"]*)['"]|require\(\s*['"]([^'"./][^'"]*)['"]\s*\)""")
PY_IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_]\w*)")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@\s*(.*)$")


def git(*args, check=True):
    res = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and res.returncode not in (0, 1):
        sys.exit(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout


def show(ref, path):
    res = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else None


def parse_diff(base, head):
    """Returns {path: {"added": [...], "removed": [...], "contexts": [...]}}."""
    out = git("diff", "-U0", "--no-color", "--no-ext-diff", base, head)
    files, cur = OrderedDict(), None
    for line in out.splitlines():
        if line.startswith("diff --git "):
            cur = None
        elif line.startswith("+++ "):
            path = line[4:].removeprefix("b/") if line[4:] != "/dev/null" else None
            if path and not SKIP_FILE.search(path):
                cur = files.setdefault(path, {"added": [], "removed": [], "contexts": [], "starts": []})
            else:
                cur = None
        elif cur is None:
            continue
        elif line.startswith("@@"):
            m = HUNK.match(line)
            if m:
                cur["starts"].append(int(m.group(1)))
                if m.group(2):
                    cur["contexts"].append(m.group(2))
        elif line.startswith("+") and not line.startswith("+++"):
            cur["added"].append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            cur["removed"].append(line[1:])
    return files


TEST_FILE = re.compile(r"(\.spec\.|\.test\.|(^|/)tests?/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)__tests__/|(^|/)e2e/)")
_FILE_CACHE = {}


def file_lines(ref, path):
    key = (ref, path)
    if key not in _FILE_CACHE:
        _FILE_CACHE[key] = (show(ref, path) or "").splitlines()
    return _FILE_CACHE[key]


def enclosing(ref, path, lineno):
    """Name and line of the nearest definition above `lineno` (1-based)."""
    lines = file_lines(ref, path)
    for i in range(min(lineno, len(lines)) - 1, max(lineno - 300, 0) - 1, -1):
        names = definitions(lines[i])
        if names:
            return names[0], i + 1
    return None


COMMENT = re.compile(r"^\s*(\*|//|#|/\*|<!--|--)")


def definitions(line):
    stripped = line.strip()
    if not stripped or COMMENT.match(line) or stripped.split("(")[0].strip() in CONTROL:
        return []
    names = []
    for pat in DEF_PATTERNS:
        for name in pat.findall(line):
            if name not in CONTROL and name not in STOP:
                names.append(name)
    return names


def collect_identifiers(head, files, limit):
    ranked = OrderedDict()  # name -> kind
    sources = {}

    def add(name, kind, path):
        if len(name) < 4 or name in STOP:
            return
        sources.setdefault(name, set()).add(path)
        ranked.setdefault(name, kind)

    for path, f in files.items():
        for start in f["starts"]:
            found = enclosing(head, path, max(start, 1))
            if found:
                add(found[0], "symbol", path)
    for path, f in files.items():
        changed = f["added"] + f["removed"]
        for line in changed:
            for name in definitions(line):
                add(name, "symbol", path)
        for ctx in f["contexts"]:
            for name in definitions(ctx):
                add(name, "symbol", path)
    for path, f in files.items():
        changed = f["added"] + f["removed"]
        for line in changed:
            for key in STRING_KEY.findall(line):
                add(key, "key", path)
            for col in SQL_COL.findall(line) + SQL_TABLE.findall(line):
                add(col, "db", path)
    for path, f in files.items():
        for line in f["added"] + f["removed"]:
            for const in CONSTANT.findall(line):
                add(const, "constant", path)
    production = [(n, k) for n, k in ranked.items() if any(not TEST_FILE.search(p) for p in sources[n])]
    return production[:limit]


def grep_usages(head, name, exclude, per_name):
    pathspec = ["--", "."] + [f":(exclude){p}" for p in exclude]
    out = git("grep", "-n", "-I", "-w", "-F", "-e", name, head, *pathspec)
    hits = []
    prefix = f"{head}:"
    for line in out.splitlines():
        if line.startswith(prefix):
            line = line[len(prefix):]
        m = re.match(r"^(.+?):(\d+):(.*)$", line)
        if not m or SKIP_FILE.search(m.group(1)) or CHANGELOG.search(m.group(1)):
            continue
        hits.append((m.group(1), int(m.group(2)), m.group(3).strip()))
    files_seen = OrderedDict()
    for hit in hits:
        files_seen.setdefault(hit[0], []).append(hit)
    def is_call(hit):
        return f"{name}(" in hit[2] and not COMMENT.match(hit[2])

    def file_rank(item):
        path, group = item
        return (bool(TEST_FILE.search(path)), path.endswith(".md"), not any(is_call(h) for h in group))

    # code call sites first, then other code, docs, tests; one hit per file
    ordered = sorted(files_seen.items(), key=file_rank)
    shown = []
    for path, group in ordered[:per_name]:
        calls = [h for h in group if is_call(h)]
        code = [h for h in group if not COMMENT.match(h[2])]
        p, num, text = (calls or code or group)[0]
        found = enclosing(head, p, num - 1) if num > 1 else None
        shown.append((p, num, text, f"{found[0]}() at {found[1]}" if found else ""))
    return shown, len(hits), len(files_seen)


LANG = {".ts": "js", ".tsx": "js", ".js": "js", ".mjs": "js", ".py": "py"}


def called_names(files, limit):
    names = OrderedDict()
    for path, f in files.items():
        lang = LANG.get(os.path.splitext(path)[1])
        if not lang or TEST_FILE.search(path):
            continue
        for line in f["added"]:
            for name in CALL.findall(line):
                if name not in STOP:
                    names.setdefault((name, lang), None)
    return list(names)[:limit]


def signatures(head, name, lang):
    pattern = (
        rf"^[[:space:]]*(export[[:space:]]+)?((public|private|protected|static|async|override)[[:space:]]+)*"
        rf"{name}[[:space:]]*(<[^>()]*>)?[[:space:]]*\("
        rf"|^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+{name}[[:space:]]*\("
    )
    globs = ["*.py"] if lang == "py" else ["*.ts", "*.tsx", "*.js", "*.mjs"]
    out = git("grep", "-n", "-I", "-E", "-e", pattern, head, "--", *globs)
    defs = []
    for line in out.splitlines():
        line = line.removeprefix(f"{head}:")
        m = re.match(r"^(.+?):(\d+):(.*)$", line)
        if m and not SKIP_FILE.search(m.group(1)) and ".spec." not in m.group(1) and "/test" not in m.group(1):
            defs.append((m.group(1), int(m.group(2)), m.group(3).strip()))
    return defs


def siblings(head, path, all_paths):
    base, dirname = os.path.basename(path), os.path.dirname(path)
    # same file name elsewhere (env overlays, other apps) only matters for config
    same_name = [p for p in all_paths if os.path.basename(p) == base and p != path] if is_config(path) else []
    parts = base.split(".")
    compound = "." + ".".join(parts[1:]) if len(parts) > 2 else None
    same_kind = []
    if compound:
        same_kind = [p for p in all_paths if p.endswith(compound) and p != path]
    if path.endswith(CONFIG_EXT) or "/workflows/" in path or os.path.basename(dirname) in ("overlays", "env"):
        in_dir = [
            p for p in all_paths
            if os.path.dirname(p) == dirname and p != path and p.endswith(os.path.splitext(path)[1])
        ]
        same_kind += in_dir
    seen = OrderedDict((p, None) for p in same_name + same_kind if not SKIP_FILE.search(p))
    return list(seen)


def is_config(path):
    return (
        path.endswith(CONFIG_EXT)
        or "/workflows/" in path
        or os.path.basename(path) in ("Dockerfile", "Chart.yaml", "values.yaml", "kustomization.yaml")
    )


def key_variants(keys):
    """NODE_VERSION also matches node-version and node_version (case-insensitive)."""
    out = OrderedDict()
    for k in keys:
        for v in (k, k.replace("_", "-"), k.replace("-", "_")):
            out.setdefault(v, None)
    return list(out)


def changed_keys(f):
    keys = OrderedDict()
    for line in f["added"] + f["removed"]:
        m = YAML_KEY.match(line)
        if m:
            keys.setdefault(m.group(1), None)
        for c in CONSTANT.findall(line):
            keys.setdefault(c, None)
    return [k for k in keys if k not in STOP][:12]


def package_versions(head, files):
    imports = OrderedDict()
    for path, f in files.items():
        src = show(head, path) or ""
        if path.endswith((".ts", ".tsx", ".js", ".mjs")):
            for a, b in TS_IMPORT.findall(src):
                spec = a or b
                name = "/".join(spec.split("/")[:2]) if spec.startswith("@") else spec.split("/")[0]
                imports.setdefault((name, "js"), path)
        elif path.endswith(".py"):
            for name in PY_IMPORT.findall(src):
                imports.setdefault((name, "py"), path)
    rows = []
    for (name, lang), path in imports.items():
        found = lookup_version(head, name, lang, path)
        if found:
            rows.append((name, *found))
    return rows


def lookup_version(head, name, lang, path):
    d = os.path.dirname(path)
    manifests = ["package.json"] if lang == "js" else ["pyproject.toml", "requirements.txt"]
    while True:
        for manifest in manifests:
            mpath = os.path.join(d, manifest) if d else manifest
            text = show(head, mpath)
            if not text:
                continue
            if manifest == "package.json":
                try:
                    pkg = json.loads(text)
                except ValueError:
                    continue
                for section in ("dependencies", "devDependencies", "peerDependencies"):
                    if name in pkg.get(section, {}):
                        return pkg[section][name], mpath
            else:
                m = re.search(rf"^\s*['\"]?{re.escape(name)}(?:\[[^\]]*\])?\s*([<>=~^!][^'\",\s]*)", text, re.M | re.I)
                if m:
                    return m.group(1), mpath
        if not d:
            return None
        d = os.path.dirname(d)


def rule_files(head, files, all_paths):
    wanted = set()
    for path in files:
        d = os.path.dirname(path)
        while True:
            for name in ("CLAUDE.md", "AGENTS.md"):
                p = os.path.join(d, name) if d else name
                if p in all_paths:
                    wanted.add(p)
            if not d:
                break
            d = os.path.dirname(d)
    return sorted(wanted, key=lambda p: (p.count("/"), p))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="base ref, e.g. origin/main")
    ap.add_argument("--head", required=True, help="head ref or sha of the PR")
    ap.add_argument("--out", help="output markdown file (default: stdout)")
    ap.add_argument("--max-identifiers", type=int, default=30)
    ap.add_argument("--per-identifier", type=int, default=5)
    ap.add_argument("--max-files-per-identifier", type=int, default=25,
                    help="skip identifiers used in more files than this (too generic)")
    ap.add_argument("--max-lines", type=int, default=450)
    args = ap.parse_args()

    base = git("merge-base", args.base, args.head).strip() or args.base
    head = args.head
    files = parse_diff(base, head)
    all_paths = set(git("ls-tree", "-r", "--name-only", head).splitlines())
    changed = list(files)
    out = [f"# Context pack: {args.base}...{head}", ""]

    out += [f"## Changed files ({len(changed)})", ""]
    out += [f"- `{p}` (+{len(f['added'])} -{len(f['removed'])})" for p, f in files.items()]

    out += ["", "## Rules and docs (CLAUDE.md / AGENTS.md chain)", ""]
    rules = rule_files(head, files, all_paths)
    out += [f"- `{p}`" for p in rules] or ["- none"]

    out += ["", "## Usages outside the diff", "",
            "Format: `file:line` [enclosing function] code. Changed files are excluded.", ""]
    for name, kind in collect_identifiers(head, files, args.max_identifiers):
        shown, total, nfiles = grep_usages(head, name, changed, args.per_identifier)
        if not shown or nfiles > args.max_files_per_identifier:
            continue
        out.append(f"### `{name}` ({kind}) — {total} hits in {nfiles} files")
        for path, num, text, func in shown:
            where = f" [{func[:80]}]" if func else ""
            out.append(f"- `{path}:{num}`{where} `{text[:140]}`")
        if nfiles > len(shown):
            out.append(f"- … {nfiles - len(shown)} more files")
        out.append("")

    out += ["## Signatures of called functions defined in the repo", ""]
    for name, lang in called_names(files, 20):
        defs = signatures(head, name, lang)
        if 0 < len(defs) <= 3:
            for path, num, text in defs:
                out.append(f"- `{name}` → `{path}:{num}` `{text[:160]}`")
    out.append("")

    out += ["## Sibling files (same name elsewhere, same kind, same config dir)", ""]
    for path, f in files.items():
        if TEST_FILE.search(path) or path.endswith(".md"):
            continue
        config = is_config(path)
        sibs = [s for s in siblings(head, path, all_paths) if not TEST_FILE.search(s)]
        if not sibs:
            continue
        keys = changed_keys(f) if config else []
        rows = []  # (has_match, line)
        for sib in sibs:
            if sib in files:
                rows.append((True, f"- `{sib}` (also changed in this PR)"))
                continue
            lines = []
            if os.path.basename(path) == "Dockerfile":
                lines = [f"`{i}: {t.strip()[:100]}`" for i, t in enumerate(file_lines(head, sib), 1) if t.startswith("FROM ")][:2]
            elif keys:
                for i, text in enumerate(file_lines(head, sib), 1):
                    if any(re.search(rf"\b{re.escape(k)}\b", text, re.I) for k in key_variants(keys)):
                        lines.append(f"`{i}: {text.strip()[:100]}`")
                    if len(lines) >= 3:
                        break
            rows.append((bool(lines), f"- `{sib}`" + (" — " + "; ".join(lines) if lines else "")))
        # siblings that share a changed key first; plain names only while the list stays short
        limit = 8 if config else 5
        matched = [r for m, r in rows if m]
        plain = [r for m, r in rows if not m]
        shown = matched[:limit] + (plain[: limit - len(matched)] if len(rows) <= limit or not keys else [])
        if not shown:
            continue
        out.append(f"### `{path}`" + (f" — changed keys: {', '.join(keys)}" if keys else ""))
        out += shown
        if len(rows) > len(shown):
            out.append(f"- … {len(rows) - len(shown)} more files of the same kind")
        out.append("")

    out += ["## Versions of imported packages", ""]
    rows = package_versions(head, files)
    out += [f"- `{name}` {ver} ({where})" for name, ver, where in rows] or ["- none found"]

    if len(out) > args.max_lines:
        out = out[: args.max_lines] + ["", f"… truncated to {args.max_lines} lines (--max-lines)"]
    text = "\n".join(out) + "\n"
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
        print(f"context pack: {args.out} ({len(out)} lines)")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
