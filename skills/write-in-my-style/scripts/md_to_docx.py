#!/usr/bin/env python3
"""
Konwertuje markdown na DOCX przez Pandoc, uzywajac reference DOCX jako szablonu stylow.

Markdown wspiera:
- Naglowki (# = H1, ## = H2, ### = H3)
- Kursywa (*tekst* lub _tekst_) i bold (**tekst**)
- Przypisy dolne — Pandoc-style:
    Treść z przypisem.[^1]

    [^1]: Tresc przypisu.
  Pandoc konwertuje je natywnie na footnotes DOCX.
- Cytaty blokowe (> tekst)
- Listy (- lub 1.)

Uzycie:
    python3 md_to_docx.py <markdown> <template.docx> <output.docx>

Przyklad:
    python3 md_to_docx.py output.md \\
        ../../../profile/university-requirements/agh-management-template.docx \\
        rozdzial_1.docx

Jesli template nie istnieje, najpierw uruchom build_template.py.
"""
import sys
import subprocess
from pathlib import Path


def check_pandoc() -> bool:
    try:
        r = subprocess.run(['pandoc', '--version'], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def convert(md_path: Path, template_path: Path, out_path: Path) -> None:
    if not check_pandoc():
        print("BLAD: Pandoc nie jest zainstalowany. Zainstaluj: brew install pandoc", file=sys.stderr)
        sys.exit(1)
    if not md_path.exists():
        print(f"BLAD: plik markdown nie istnieje: {md_path}", file=sys.stderr)
        sys.exit(1)
    if not template_path.exists():
        print(f"BLAD: template DOCX nie istnieje: {template_path}", file=sys.stderr)
        print(f"   Uruchom najpierw: python3 build_template.py <wymogi.md> {template_path}", file=sys.stderr)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        'pandoc',
        str(md_path),
        '-o', str(out_path),
        '--reference-doc', str(template_path),
        '--from', 'markdown+footnotes',
        '--to', 'docx',
    ]
    print(f"Uruchamiam: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Pandoc bla:\n{r.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: {out_path}")


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    convert(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))


if __name__ == '__main__':
    main()
