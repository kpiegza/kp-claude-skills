#!/usr/bin/env python3
"""Helper for the kp:create-deployment-post skill (standard library only).

Subcommands (all output is one compact text block the model acts on directly):

  prepare [PR] [uwagi...]   PR facts (gh), scope candidates, PR&CR match, my recent
                            Deployments posts as style examples, next command.
                            ALWAYS exits 0 - errors are printed inside the block, because
                            the skill runs it as a `!` injection line (non-zero would abort).
  preview --pr URL [--pr URL] --subject S [--note LINE] [--dry-run]
                            Builds the HTML body (links as <a href>), runs rasp-teams
                            `send-channel Monetisation Deployments` = PREVIEW + one-time ID.
                            Sends nothing. Falls back to the clipboard when Teams is unavailable.
  confirm ID                Pass-through to teams.py confirm (only after the user said "Wyslij").
  clipboard --subject S     Copies the subject to the clipboard (pbcopy), prints it.

teams.py (monetisation-core:rasp-teams) is discovered at runtime (newest plugin.json version)
and run through `uv run --with requests`, because no system python3 here has `requests`.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
CACHE_DIR = HOME / ".cache" / "kp-deployment-post"
DEPLOY_CACHE_TTL = 24 * 3600          # style examples change slowly; a day of staleness is fine
DEPLOY_DAYS = int(os.environ.get("KP_DEPLOY_DAYS", "21"))   # measured 2026-11-03: 14 d 8 s, 21 d 22 s, 30 d 34 s
PRCR_DAYS = 14                        # PR&CR post precedes the deploy by hours..4 days in practice
TEAMS_TIMEOUT = 75                    # per call; both calls run in parallel, under the 2 min `!` limit
GH_TIMEOUT = 25
TEAMS_GLOBS = [
    str(HOME / ".claude/plugins/synced/*/monetisation-core*/skills/rasp-teams/scripts/teams.py"),
    str(HOME / ".claude/plugins/cache/rasp-monetisation/monetisation-core/*/skills/rasp-teams/scripts/teams.py"),
]
TEAM, CH_DEPLOY, CH_PRCR = "Monetisation", "Deployments", "pull request"
# Shown only when Teams is unavailable, so the model still has a style anchor.
FALLBACK_EXAMPLES = [
    "[onboarding-event-consumer] Wysyłka userActivated do idealo po przyjęciu zaproszenia",
    "[idealoAds] Node 24 w obrazie i CI das-sese-api (CVE-2026-111497)",
    "[adp-reports] Zmiana offer_ids i offer_names na tablice w eksporcie inventory do idealo",
    "[adp-javascripts] [flowplayerAdpPlugin] Pre-roll z bety startuje na iOS przy autostarcie",
]
# Path segments that are containers, not application names.
CONTAINERS = {"src", "apps", "app", "packages", "projects", "python_apps", "libs", "lib",
              "services", "javascript", "golang", "frontend", "python", "cmd", "internal",
              "pkg", "modules"}
INFRA = {".github", "k8s", "helm", "charts", "deploy", "deployment", "terraform", "docs",
         "doc", "tests", "test", "scripts", "ci", ".circleci", "config"}
PR_URL_RE = re.compile(r"https?://github\.com/([\w.-]+)/([\w.-]+)/pull/(\d+)", re.I)
JIRA_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d{1,6})\b")


# ---------------------------------------------------------------------------
# small utils
# ---------------------------------------------------------------------------

def run(cmd: list[str], timeout: int, cwd: str | None = None) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError as e:
        return 127, "", f"brak programu: {e.filename}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout po {timeout}s"


def html_to_lines(content: str) -> list[str]:
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", content or "")
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t).replace("\xa0", " ")
    return [ln.strip() for ln in t.splitlines() if ln.strip()]


def msg_text_lines(msg: dict) -> list[str]:
    body = msg.get("body") or {}
    if body.get("contentType") == "html":
        return html_to_lines(body.get("content", ""))
    return [ln.strip() for ln in (body.get("content") or "").splitlines() if ln.strip()]


def msg_author(msg: dict) -> str:
    return ((msg.get("from") or {}).get("user") or {}).get("displayName") or "?"


def msg_date(msg: dict) -> str:
    return (msg.get("createdDateTime") or "")[:10]


def shorten(s: str, n: int) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def copy_to_clipboard(text: str) -> bool:
    if not shutil.which("pbcopy"):
        return False
    try:
        subprocess.run(["pbcopy"], input=text, text=True, check=True, timeout=5)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# teams.py discovery + invocation
# ---------------------------------------------------------------------------

def plugin_version(teams_py: str) -> tuple[int, ...]:
    """Version from <plugin root>/.claude-plugin/plugin.json (root = 4 levels above teams.py).
    mtime is useless here: the synced copy is unpacked with 1980 timestamps."""
    root = Path(teams_py).resolve().parents[3]
    try:
        v = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("version", "0")
        return tuple(int(x) for x in re.findall(r"\d+", str(v))) or (0,)
    except (OSError, ValueError):
        return (0,)


def find_teams_py() -> str | None:
    override = os.environ.get("KP_TEAMS_PY")
    if override and Path(override).exists():
        return override
    cands = [p for pat in TEAMS_GLOBS for p in glob.glob(pat)]
    if not cands:
        return None
    return max(cands, key=lambda p: (plugin_version(p), os.path.getmtime(str(Path(p).resolve().parents[3]))))


def teams_cmd(teams_py: str) -> list[str] | None:
    """Command prefix that can import `requests`: uv (preferred) or a plain python3."""
    uv = shutil.which("uv") or (str(HOME / ".local/bin/uv") if (HOME / ".local/bin/uv").exists() else None)
    if uv:
        return [uv, "run", "-q", "--with", "requests", "python3", teams_py]
    rc, _, _ = run([sys.executable, "-c", "import requests"], 10)
    if rc == 0:
        return [sys.executable, teams_py]
    return None


class TeamsUnavailable(Exception):
    pass


def teams_base() -> list[str]:
    tp = find_teams_py()
    if not tp:
        raise TeamsUnavailable("nie znaleziono teams.py (plugin monetisation-core / skill rasp-teams)")
    cmd = teams_cmd(tp)
    if not cmd:
        raise TeamsUnavailable("brak `uv` (~/.local/bin/uv) i brak modulu `requests` dla python3")
    return cmd


def teams_error(stderr: str, stdout: str, rc: int) -> str:
    text = (stderr + "\n" + stdout)
    m = re.search(r"BLAD: (.*)", text)
    if m:
        return shorten(m.group(1), 200)
    if rc == 124:
        return stderr
    return shorten(text.strip().splitlines()[-1] if text.strip() else f"exit {rc}", 200)


def auth_hint(base: list[str]) -> str:
    q = " ".join(base)
    return f"zaloguj przez rasp-teams: `{q} auth start`, potem `{q} auth wait`"


def fetch_channel_json(base: list[str], channel: str, days: int) -> list[dict]:
    rc, out, err = run(base + ["read-channel", TEAM, channel, "--days", str(days), "--json",
                               "--limit", "1000", "--max-pages", "12"], TEAMS_TIMEOUT)
    if rc != 0:
        raise TeamsUnavailable(teams_error(err, out, rc))
    try:
        data = json.loads(out)
    except ValueError:
        raise TeamsUnavailable("niepoprawny JSON z teams.py")
    return [m for m in data if isinstance(m, dict) and m.get("messageType") in (None, "message")]


def deployments_cached(base: list[str], fresh: bool) -> tuple[list[dict], str]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / f"deployments-{DEPLOY_DAYS}d.json"
    if not fresh and f.exists() and time.time() - f.stat().st_mtime < DEPLOY_CACHE_TTL:
        try:
            stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime))
            return json.loads(f.read_text(encoding="utf-8")), f"z cache {stamp}"
        except ValueError:
            pass
    msgs = fetch_channel_json(base, CH_DEPLOY, DEPLOY_DAYS)
    f.write_text(json.dumps(msgs, ensure_ascii=False), encoding="utf-8")
    return msgs, "swieze"


# ---------------------------------------------------------------------------
# PR resolution (gh)
# ---------------------------------------------------------------------------

def parse_pr_arg(words: list[str]) -> tuple[list[str], list[str]]:
    """Returns (gh pr view args, leftover words = user remarks)."""
    rest = []
    pr_args: list[str] | None = None
    i = 0
    while i < len(words):
        w = words[i]
        if pr_args is None:
            m = PR_URL_RE.search(w)
            if m:
                pr_args = [m.group(0)]
                i += 1
                continue
            m = re.fullmatch(r"([\w.-]+/[\w.-]+)#(\d+)", w)
            if m:
                pr_args = [m.group(2), "-R", m.group(1)]
                i += 1
                continue
            if re.fullmatch(r"#?(\d{1,6})", w):
                pr_args = [w.lstrip("#")]
                i += 1
                continue
            if w.lower() in ("pr", "pull", "request", "#") and i + 1 < len(words) and re.fullmatch(r"#?\d{1,6}", words[i + 1]):
                pr_args = [words[i + 1].lstrip("#")]
                i += 2
                continue
        rest.append(w)
        i += 1
    return (pr_args or []), rest


def gh_pr(pr_args: list[str]) -> tuple[dict | None, str]:
    fields = "number,title,body,url,headRefName,baseRefName,state,isDraft,mergedAt,author,files"
    rc, out, err = run(["gh", "pr", "view", *pr_args, "--json", fields], GH_TIMEOUT)
    if rc != 0:
        e = shorten(err.strip() or out.strip() or f"gh exit {rc}", 240)
        hint = ""
        if "auth login" in e or "not logged" in e.lower():
            hint = " -> `gh auth login`"
        elif "no pull requests found" in e.lower():
            hint = " -> brak PR dla tego brancha; podaj numer albo URL"
        elif "-R" not in pr_args and not any(a.startswith("http") for a in pr_args):
            # bare number or no argument: gh needs the repo from cwd (git may be localized, so
            # do not match on the error text)
            hint = " -> podaj pelny URL PR (albo owner/repo#N) lub uruchom z katalogu repo"
        return None, f"BLAD gh: {e}{hint}"
    try:
        return json.loads(out), ""
    except ValueError:
        return None, "BLAD gh: niepoprawny JSON"


def scope_candidates(paths: list[str]) -> tuple[list[tuple[str, str, int]], dict[str, int]]:
    """[(scope, path_prefix, files)] sorted by count desc, plus infra/other counts."""
    counts: dict[tuple[str, str], int] = {}
    other: dict[str, int] = {}
    for p in paths:
        segs = p.split("/")
        if len(segs) == 1:
            other["(root)"] = other.get("(root)", 0) + 1
            continue
        if segs[0] in INFRA:
            other[segs[0]] = other.get(segs[0], 0) + 1
            continue
        i = 0
        while i < len(segs) - 1 and segs[i] in CONTAINERS:
            i += 1
        if i >= len(segs) - 1:            # file directly inside a container dir
            other[segs[0]] = other.get(segs[0], 0) + 1
            continue
        name = segs[i]
        key = (name.replace("_", "-"), "/".join(segs[: i + 1]))
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(((k[0], k[1], n) for k, n in counts.items()), key=lambda x: (-x[2], x[0]))
    return ranked, other


def body_digest(body: str, limit: int = 1100) -> list[str]:
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body or "")     # [text](url) -> text
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    sections: dict[str, list[str]] = {}
    cur = "_"
    for ln in body.splitlines():
        m = re.match(r"^#{1,3}\s*(.+?)\s*$", ln)
        if m:
            cur = m.group(1).strip().lower()
            sections.setdefault(cur, [])
            continue
        if ln.strip():
            sections.setdefault(cur, []).append(ln.rstrip())
    out: list[str] = []
    budget = limit
    # Notes before Changes: deploy steps (migration window, post-deploy actions) live there and
    # the skill reminds the user of them; Changes only help with phrasing.
    plan = [("task", 1, 160), ("context", 2, 300), ("notes", 3, 320), ("changes", 3, 300)]
    if not any(k in sections for k, _, _ in plan):
        plan = [("_", 6, limit)]
    for key, nlines, chars in plan:
        lines = sections.get(key) or []
        if not lines:
            continue
        txt = shorten(" ".join(lines[:nlines]), min(chars, budget))
        if not txt:
            continue
        label = key.capitalize() if key != "_" else "Opis"
        out.append(f"  {label}: {txt}")
        budget -= len(txt)
        if budget <= 40:
            break
    return out


# ---------------------------------------------------------------------------
# Teams matching + examples
# ---------------------------------------------------------------------------

def my_name() -> str:
    rc, out, _ = run(["git", "config", "user.name"], 5)
    name = out.strip() if rc == 0 else ""
    if not name:
        rc, out, _ = run(["gh", "api", "user", "--jq", ".name"], GH_TIMEOUT)
        name = out.strip() if rc == 0 else ""
    return os.environ.get("KP_TEAMS_AUTHOR", name)


def mentions_pr(msg: dict, owner: str, repo: str, number: int) -> bool:
    blob = json.dumps(msg, ensure_ascii=False).lower()
    return (f"{owner}/{repo}/pull/{number}".lower() in blob
            or f"{owner}/{repo}#{number}".lower() in blob
            or f"{repo}#{number}".lower() in blob)


def mentions_repo(msg: dict, owner: str, repo: str) -> bool:
    blob = json.dumps(msg, ensure_ascii=False).lower()
    subj = (msg.get("subject") or "").lower()
    return f"github.com/{owner}/{repo}/".lower() in blob or f"{owner}/{repo}#".lower() in blob \
        or f"[{repo.lower()}]" in subj


def note_lines(msg: dict, limit: int = 2, chars: int = 160) -> list[str]:
    out = []
    for ln in msg_text_lines(msg):
        if re.match(r"^(https?://\S+\s*)+$", ln) or "teams.microsoft.com" in ln:
            continue
        if ln.lower().startswith("[przesłane dalej]"):
            continue
        out.append(shorten(ln, chars))
        if len(out) >= limit:
            break
    return out


def pick_examples(deploy: list[dict], me: str, owner: str, repo: str, n: int = 6) -> list[str]:
    with_subject = [m for m in deploy if (m.get("subject") or "").strip()]
    with_subject.sort(key=lambda m: m.get("createdDateTime") or "", reverse=True)
    mine = [m for m in with_subject if me and me.lower() in msg_author(m).lower()]
    same = [m for m in mine if mentions_repo(m, owner, repo)]
    chosen: list[dict] = []
    for m in same[:3] + mine:
        if m not in chosen:
            chosen.append(m)
        if len(chosen) >= n:
            break
    team_tag = False
    if len(chosen) < 3:                       # not enough of my own posts: borrow team ones
        team_same = [m for m in with_subject if m not in chosen and mentions_repo(m, owner, repo)]
        team_any = [m for m in with_subject if m not in chosen]
        for m in team_same[:3] + team_any:
            if m not in chosen:
                chosen.append(m)
                team_tag = True
            if len(chosen) >= n:
                break
    lines = []
    for m in chosen:
        s = f"  «{shorten(m['subject'].strip(), 120)}»"
        notes = note_lines(m, limit=1, chars=110)
        if notes:
            s += f" | tresc: {notes[0]}"
        if team_tag and not (me and me.lower() in msg_author(m).lower()):
            s += f" ({msg_author(m)})"
        lines.append(s)
    return lines


# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------

def cmd_prepare(args) -> int:
    words = " ".join(args.words).split()
    pr_args, remarks = parse_pr_arg(words)
    pr, err = gh_pr(pr_args)
    out: list[str] = ["# Wpis deploymentowy - dane"]
    if not pr:
        out.append(err)
        out.append("Bez PR nie ma wpisu: popros uzytkownika o numer albo URL PR i uruchom "
                   f"`python3 {Path(__file__).resolve()} prepare <PR>`.")
        print("\n".join(out))
        return 0

    m = PR_URL_RE.search(pr["url"])
    owner, repo, number = (m.group(1), m.group(2), int(m.group(3))) if m else ("?", "?", pr["number"])
    src = "z argumentu" if pr_args else "z aktualnego brancha"
    state = pr["state"] + (" DRAFT" if pr.get("isDraft") else "")
    when = (pr.get("mergedAt") or "")[:10]
    out.append(f"PR: {owner}/{repo}#{number} ({src}) · {state}{' ' + when if when else ''} · "
               f"autor {(pr.get('author') or {}).get('login', '?')} · branch {pr.get('headRefName', '?')}")
    out.append(f"URL: {pr['url']}")
    out.append(f"Tytul: {pr['title']}")
    jira = JIRA_RE.findall(pr.get("headRefName") or "") or JIRA_RE.findall((pr.get("body") or "")[:400])
    if jira:
        out.append(f"Jira: {jira[0]}")
    digest = body_digest(pr.get("body") or "")
    if digest:
        out.append("Opis PR (skrot):")
        out.extend(digest)
    paths = [f.get("path", "") for f in (pr.get("files") or [])]
    ranked, other = scope_candidates(paths)
    parts = [f"{s} ({p}, {n})" for s, p, n in ranked[:4]]
    if other:
        parts.append("inne: " + ", ".join(f"{k} {v}" for k, v in sorted(other.items(), key=lambda x: -x[1])[:4]))
    out.append(f"Pliki ({len(paths)}): " + (" · ".join(parts) if parts else "-"))
    cands = [s for s, _, _ in ranked[:3]]
    # conventional-commit scope from the title, e.g. fix(adp-offer-updater): ... - paths can't see
    # it under generic dirs like src/python/adp/modes/. When it overlaps a path candidate
    # (onboarding vs onboarding-event-consumer, adp vs adp-offer-updater) the longer name wins
    # and goes first; the shorter overlapping names are dropped. The first candidate is the scope.
    t = re.match(r"^\w+\(([^)]+)\)!?:", pr["title"] or "")
    if t:
        ts = t.group(1).strip().replace("_", "-")
        overlap = [c for c in cands if ts.lower() in c.lower() or c.lower() in ts.lower()]
        best = max(overlap + [ts], key=len)
        cands = [f"{best} ({'tytul+sciezka' if overlap else 'z tytulu'})"] + [c for c in cands if c not in overlap]
    if repo not in cands:
        cands.append(f"{repo} (repo)")
    out.append("Scope - kandydaci: " + " | ".join(cands))
    if remarks:
        out.append("Uwagi uzytkownika: " + " ".join(remarks))

    out.append("")
    out.append("## Teams")
    me = my_name()
    examples: list[str] = []
    teams_note = ""
    try:
        base = teams_base()
        if args.no_teams:
            raise TeamsUnavailable("pominieto (--no-teams)")
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            f_pr = ex.submit(fetch_channel_json, base, CH_PRCR, PRCR_DAYS)
            f_dep = ex.submit(deployments_cached, base, args.fresh)
            pr_err = dep_err = ""
            try:
                prcr = f_pr.result()
            except TeamsUnavailable as e:
                prcr, pr_err = [], str(e)
            try:
                deploy, dep_src = f_dep.result()
            except TeamsUnavailable as e:
                deploy, dep_src, dep_err = [], "", str(e)
        if pr_err and dep_err:
            raise TeamsUnavailable(pr_err)
        hits = [x for x in prcr if mentions_pr(x, owner, repo, number)]
        if pr_err:
            out.append(f"PR&CR: NIEDOSTEPNE ({pr_err})")
        elif hits:
            h = sorted(hits, key=lambda x: x.get("createdDateTime") or "", reverse=True)[0]
            out.append(f"PR&CR: JEST wpis {msg_date(h)} ({msg_author(h)}) «{(h.get('subject') or '').strip()}»")
            for ln in note_lines(h):
                out.append(f"  tresc: {ln}")
        else:
            out.append(f"PR&CR ({PRCR_DAYS} dni): brak wpisu z linkiem do tego PR.")
        if dep_err:
            out.append(f"Deployments: NIEDOSTEPNE ({dep_err})")
        else:
            dup = [x for x in deploy if mentions_pr(x, owner, repo, number)]
            if dup:
                d = dup[0]
                out.append(f"Deployments: UWAGA - ten PR byl juz na Deployments {msg_date(d)} ({msg_author(d)}) "
                           f"«{(d.get('subject') or '').strip()}»")
            # the post for this very PR is already reported above, not a style example
            others = [x for x in deploy if not mentions_pr(x, owner, repo, number)]
            examples = pick_examples(others, me, owner, repo)
            out.append(f"Moje wpisy na Deployments ({DEPLOY_DAYS} dni, {dep_src}; to samo repo najpierw):")
            out.extend(examples or ["  (brak)"])
        teams_note = "Teams: OK"
    except TeamsUnavailable as e:
        reason = str(e)
        hint = ""
        if re.search(r"token|zaloguj", reason, re.I):
            try:
                hint = "; " + auth_hint(teams_base())
            except TeamsUnavailable:
                pass
        out.append(f"Teams: NIEDOSTEPNE - {reason}{hint}")
        out.append("Wzorce (wbudowane, bo Teams nie odpowiada):")
        out.extend(f"  «{s}»" for s in FALLBACK_EXAMPLES)
        teams_note = "Teams: NIEDOSTEPNE -> `preview` skopiuje temat do schowka zamiast wysylac."
    out.append(teams_note)

    out.append("")
    out.append("## Nastepny krok")
    out.append(f'python3 {Path(__file__).resolve()} preview --pr {pr["url"]} --subject "[scope] Opis"')
    print("\n".join(out))
    return 0


# ---------------------------------------------------------------------------
# preview / confirm / clipboard
# ---------------------------------------------------------------------------

def build_html(urls: list[str], note: str | None) -> str:
    parts = []
    if note:
        parts.append(f"<p>{html.escape(note.strip())}</p>")
    for u in urls:
        u = u.strip()
        parts.append(f'<p><a href="{html.escape(u, quote=True)}">{html.escape(u)}</a></p>')
    return "\n".join(parts)


def check_subject(subject: str) -> list[str]:
    warn = []
    s = subject.strip()
    if not s:
        warn.append("BLAD: pusty temat")
    if "\n" in s:
        warn.append("BLAD: temat ma kilka linii")
    if not s.startswith("["):
        warn.append("UWAGA: temat nie zaczyna sie od [scope]")
    if len(s) > 120:
        warn.append(f"UWAGA: temat ma {len(s)} znakow (wzorce: 40-100)")
    if re.match(r"^\[[^\]]+\]\s*(feat|fix|chore|refactor|ci|docs)(\(|:)", s, re.I):
        warn.append("UWAGA: temat wyglada jak tytul commita (prefiks feat/fix) - wzorce tego nie maja")
    return warn


def cmd_preview(args) -> int:
    subject = " ".join(args.subject.split())
    warns = check_subject(subject)
    for w in warns:
        print(w)
    if any(w.startswith("BLAD") for w in warns):
        return 2
    urls = []
    for u in args.pr:
        m = PR_URL_RE.search(u)
        if not m:
            print(f"BLAD: to nie jest URL PR na GitHub: {u}")
            return 2
        urls.append(m.group(0))
    body = build_html(urls, args.note)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / "post.html"
    f.write_text(body, encoding="utf-8")
    me = Path(__file__).resolve()

    def fallback(reason: str) -> int:
        ok = copy_to_clipboard(subject)
        print(f"TEAMS NIEDOSTEPNE: {reason}")
        print(f"Temat: {subject}")
        print("Tresc: " + " | ".join(([args.note] if args.note else []) + urls))
        print("Schowek: " + ("skopiowano temat (Cmd+V w polu tematu nowego watku na Deployments)"
                             if ok else "brak pbcopy - uzytkownik kopiuje recznie"))
        return 0

    try:
        base = teams_base()
    except TeamsUnavailable as e:
        return fallback(str(e))
    cmd = base + ["send-channel", TEAM, CH_DEPLOY, "--subject", subject, "--message-file", str(f), "--html"]
    if args.dry_run:
        print("DRY-RUN, komenda rasp-teams (nie uruchomiona):")
        print("  " + " ".join(repr(c) if " " in c else c for c in cmd))
        print("HTML:")
        print(body)
        return 0
    rc, out, err = run(cmd, TEAMS_TIMEOUT)
    if rc != 0:
        reason = teams_error(err, out, rc)
        if re.search(r"token|zaloguj", reason, re.I):
            reason += "; " + auth_hint(base)
        return fallback(reason)
    print(out.rstrip())
    m = re.search(r"ID zapisu: ([0-9a-f]+)", out)
    if m:
        print(f"PO ZGODZIE UZYTKOWNIKA (wybor 'Wyslij'): python3 {me} confirm {m.group(1)}")
    else:
        print("UWAGA: brak ID zapisu w podgladzie - nie wysylaj; pokaz uzytkownikowi powyzszy wynik.")
    return 0


def cmd_confirm(args) -> int:
    try:
        base = teams_base()
    except TeamsUnavailable as e:
        print(f"BLAD: {e}")
        return 1
    rc, out, err = run(base + ["confirm", args.write_id], TEAMS_TIMEOUT)
    sys.stdout.write(out)
    sys.stderr.write(err)
    return rc


def cmd_clipboard(args) -> int:
    subject = " ".join(args.subject.split())
    ok = copy_to_clipboard(subject)
    print(f"Temat: {subject}")
    print("Schowek: " + ("skopiowano" if ok else "brak pbcopy - uzytkownik kopiuje recznie"))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="dane do wpisu (zawsze exit 0)")
    p.add_argument("words", nargs="*", help="numer PR, URL, owner/repo#N, albo nic (aktualny branch) + uwagi")
    p.add_argument("--fresh", action="store_true", help="pomin cache Deployments")
    p.add_argument("--no-teams", action="store_true", help="tylko gh, bez Teams")
    p.set_defaults(fn=cmd_prepare)
    p = sub.add_parser("preview", help="podglad wpisu na Deployments (nic nie wysyla)")
    p.add_argument("--pr", action="append", required=True, help="URL PR (mozna kilka razy)")
    p.add_argument("--subject", required=True)
    p.add_argument("--note", help="dodatkowa linia tresci przed linkiem")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_preview)
    p = sub.add_parser("confirm", help="wysylka przygotowanego wpisu (tylko po zgodzie uzytkownika)")
    p.add_argument("write_id")
    p.set_defaults(fn=cmd_confirm)
    p = sub.add_parser("clipboard", help="skopiuj temat do schowka")
    p.add_argument("--subject", required=True)
    p.set_defaults(fn=cmd_clipboard)
    args = ap.parse_args()
    try:
        return args.fn(args)
    except Exception as e:  # never let `prepare` abort the skill
        print(f"BLAD skryptu: {type(e).__name__}: {e}")
        return 0 if args.cmd == "prepare" else 1


if __name__ == "__main__":
    sys.exit(main())
