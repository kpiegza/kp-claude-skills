#!/usr/bin/env python3
"""
Generuje reference DOCX uzywany jako template'u dla Pandoc.

Reference DOCX zawiera ustawione style (Normal, Heading 1-3, Footnote Text) i marginesy
dla danego zestawu wymogow uczelnianych. Pandoc kopiuje te style przy generowaniu
docelowego DOCX.

Uzycie:
    python3 build_template.py <sciezka-do-wymogow.md> <sciezka-wyjsciowa.docx>

Przyklad:
    python3 build_template.py \\
        ../../../profile/university-requirements/agh-management.md \\
        ../../../profile/university-requirements/agh-management-template.docx

Skrypt jest celowo prosty: parsuje markdown wymogow zeby wyciagnac kluczowe wartosci
(marginesy, czcionka, rozmiary naglowkow). Jesli nie znajdzie wartosci - uzywa domyslnych
zgodnych z metodyka WZ AGH.
"""
import sys
import re
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION


# Domyslne wartosci (AGH WZ wedle praktyki licencjackiej Konrada)
DEFAULTS = {
    'font_name': 'Times New Roman',
    'body_font_size': 12,
    'line_spacing': 1.5,
    'first_line_indent_cm': 1.27,
    'margin_left_cm': 3.5,
    'margin_right_cm': 2.5,
    'margin_top_cm': 2.5,
    'margin_bottom_cm': 2.5,
    'h1_size': 18,
    'h2_size': 14,
    'h3_size': 12,
    'footnote_size': 10,
    'caption_size': 10,
}


def parse_wymogi(md_path: Path) -> dict:
    """Wyciaga kluczowe parametry formatowania z markdownowego pliku wymogow."""
    cfg = dict(DEFAULTS)
    if not md_path.exists():
        print(f"OSTRZEZENIE: plik {md_path} nie istnieje, uzywam domyslnych wartosci AGH WZ")
        return cfg

    text = md_path.read_text(encoding='utf-8')

    def find_cm(pattern: str, default: float) -> float:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(',', '.'))
        return default

    def find_pt(pattern: str, default: int) -> int:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        return default

    cfg['margin_left_cm'] = find_cm(r'lewy[:\s]+\*?\*?(\d+[,.]?\d*)\s*cm', DEFAULTS['margin_left_cm'])
    cfg['margin_right_cm'] = find_cm(r'prawy[:\s]+\*?\*?(\d+[,.]?\d*)\s*cm', DEFAULTS['margin_right_cm'])
    cfg['margin_top_cm'] = find_cm(r'gorny[:\s]+\*?\*?(\d+[,.]?\d*)\s*cm', DEFAULTS['margin_top_cm'])
    cfg['margin_bottom_cm'] = find_cm(r'dolny[:\s]+\*?\*?(\d+[,.]?\d*)\s*cm', DEFAULTS['margin_bottom_cm'])
    cfg['first_line_indent_cm'] = find_cm(r'wciecie[^:]*:\s*\*?\*?(\d+[,.]?\d*)\s*cm', DEFAULTS['first_line_indent_cm'])

    h1 = re.search(r'H1[^|]*\|\s*\*?\*?(\d+)\s*pt', text)
    if h1:
        cfg['h1_size'] = int(h1.group(1))
    h2 = re.search(r'H2[^|]*\|\s*\*?\*?(\d+)\s*pt', text)
    if h2:
        cfg['h2_size'] = int(h2.group(1))
    h3 = re.search(r'H3[^|]*\|\s*\*?\*?(\d+)\s*pt', text)
    if h3:
        cfg['h3_size'] = int(h3.group(1))

    return cfg


def build(cfg: dict, out_path: Path) -> None:
    doc = Document()

    # Marginesy
    section = doc.sections[0]
    section.left_margin = Cm(cfg['margin_left_cm'])
    section.right_margin = Cm(cfg['margin_right_cm'])
    section.top_margin = Cm(cfg['margin_top_cm'])
    section.bottom_margin = Cm(cfg['margin_bottom_cm'])

    # Style: Normal (tekst glowny)
    normal = doc.styles['Normal']
    normal.font.name = cfg['font_name']
    normal.font.size = Pt(cfg['body_font_size'])
    pf = normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.line_spacing = cfg['line_spacing']
    pf.first_line_indent = Cm(cfg['first_line_indent_cm'])
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)

    # Heading 1 - rozdzial
    h1 = doc.styles['Heading 1']
    h1.font.name = cfg['font_name']
    h1.font.size = Pt(cfg['h1_size'])
    h1.font.bold = True
    h1.font.color.rgb = RGBColor(0, 0, 0)
    h1.paragraph_format.space_before = Pt(20)
    h1.paragraph_format.space_after = Pt(6)
    h1.paragraph_format.first_line_indent = Cm(0)
    h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Heading 2
    h2 = doc.styles['Heading 2']
    h2.font.name = cfg['font_name']
    h2.font.size = Pt(cfg['h2_size'])
    h2.font.bold = True
    h2.font.color.rgb = RGBColor(0, 0, 0)
    h2.paragraph_format.space_before = Pt(12)
    h2.paragraph_format.space_after = Pt(6)
    h2.paragraph_format.first_line_indent = Cm(0)
    h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Heading 3
    h3 = doc.styles['Heading 3']
    h3.font.name = cfg['font_name']
    h3.font.size = Pt(cfg['h3_size'])
    h3.font.bold = True
    h3.font.color.rgb = RGBColor(0, 0, 0)
    h3.paragraph_format.space_before = Pt(12)
    h3.paragraph_format.space_after = Pt(6)
    h3.paragraph_format.first_line_indent = Cm(0)
    h3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Footnote Text
    try:
        fn = doc.styles['Footnote Text']
        fn.font.name = cfg['font_name']
        fn.font.size = Pt(cfg['footnote_size'])
        fn.paragraph_format.line_spacing = 1.0
        fn.paragraph_format.first_line_indent = Cm(0)
    except KeyError:
        pass  # niektore wersje docx nie maja tego stylu domyslnie

    # Caption (dla tabel/rysunkow)
    try:
        cap = doc.styles['Caption']
        cap.font.name = cfg['font_name']
        cap.font.size = Pt(cfg['caption_size'])
        cap.font.italic = False
    except KeyError:
        pass

    # Wstaw przykladowy paragraf zeby template mial cos w srodku
    # (Pandoc tego nie kopiuje do docelowego DOCX, ale jest pomocny przy debugowaniu szablonu)
    doc.add_paragraph("Template - przykladowy akapit tekstu glownego w stylu Normal.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    print(f"Template zapisany: {out_path}")
    print(f"Konfiguracja:")
    for k, v in cfg.items():
        print(f"  {k}: {v}")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    md_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    cfg = parse_wymogi(md_path)
    build(cfg, out_path)


if __name__ == '__main__':
    main()
