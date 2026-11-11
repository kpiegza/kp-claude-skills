"""Shared helpers for the knowledge_base.py tests."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPTS_DIR / "knowledge_base.py"
PLUGIN_ROOT = Path(__file__).resolve().parents[3]

_BODIES = {
    "decision": [
        "# Kolejka w Postgresie, nie SQS",
        "**Decyzja:** tabela jobs z FOR UPDATE SKIP LOCKED.",
        "**Dlaczego:** zadanie powstaje w tej samej transakcji co zmiana domenowa.",
        "**Odrzucone:** SQS (druga infrastruktura); Redis Streams (trwałość).",
        "**Wrócić, gdy:** ponad 200 zadań na sekundę.",
    ],
    "gotcha": [
        "# Advisory lock znika za PgBouncerem",
        "**Objaw:** dwie migracje naraz mimo pg_advisory_lock.",
        "**Przyczyna:** lock sesyjny, a pool_mode=transaction zmienia połączenia.",
        "**Rozwiązanie:** pg_advisory_xact_lock w jednej transakcji.",
        "**Ślepy trop:** server_reset_query nie pomaga.",
    ],
    "finding": [
        "# bun test szybszy, ale nie dla nas",
        "**Pytanie:** czy migracja z Vitest skróci CI?",
        "**Wniosek:** nie migrować; zysk 40 s na 9 minut.",
        "**Dlaczego:** brak odpowiednika vi.mock z hoistingiem.",
        "**Nie dotyczy:** nowych pakietów bez mocków modułów.",
    ],
}


def import_kb():
    """Import knowledge_base.py from the skill's scripts directory."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import knowledge_base

    return knowledge_base


def valid_note(type_: str = "decision") -> tuple[dict[str, str], list[str]]:
    """Frontmatter and body of a note of the given type that passes lint."""
    meta = {
        "type": type_,
        "when": "przykładowa sytuacja, w której warto przeczytać tę notatkę",
        "applies": "PostgreSQL 16",
        "checked": "2026-11-01",
        "proof": "tested",
    }
    return meta, list(_BODIES[type_])


def write_note(
    root: Path,
    name: str,
    meta: dict[str, str] | None,
    body: list[str],
    newline: str = "\n",
    bom: bool = False,
) -> Path:
    """Write a note to root/notes/name; meta=None writes no frontmatter."""
    notes = root / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if meta is not None:
        lines.append("---")
        lines.extend(f"{key}: {value}" for key, value in meta.items())
        lines.append("---")
    lines.extend(body)
    data = (newline.join(lines) + newline).encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path = notes / name
    path.write_bytes(data)
    return path
