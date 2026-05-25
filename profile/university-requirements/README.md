# Wymogi uczelni

Tu trzymamy zasady formatowania i struktury prac wymagane przez Twoja uczelnie.

W przeciwienstwie do `corpus/` i `profile/writing-style.md` - ten folder
**jest commitowany do gita**. To nie sa dane wrazliwe, tylko publicznie
dostepne wytyczne uczelni.

## Struktura

Dla kazdego zestawu wymogow (kazdy poziom / kierunek / uczelnia) - osobny zestaw:

```
university-requirements/
├── README.md                          <- ten plik + spis zestawow ponizej
├── magisterka.md                      <- spisane reguly dla magisterki
├── magisterka-template.docx           <- szablon Worda dla magisterki
├── esej-<kierunek>.md
└── esej-<kierunek>-template.docx
```

## Co wrzucic teraz

1. **Oryginalne dokumenty wymogow od uczelni** (PDF/DOCX z zarzadzeniem dziekana,
   instrukcja pisania prac, regulamin) - wrzuc je tymczasowo do tego folderu pod
   ich oryginalna nazwa, np.:
   - `wymogi-magisterka-zrodlo.pdf`
   - `wymogi-esej-zrodlo.pdf`

   Po przerobieniu na ustrukturyzowany `.md` mozna je usunac lub zostawic dla
   referencji.

2. **Szablon DOCX z formatowaniem** dla kazdego zestawu - plik Worda z ustawionymi
   czcionkami, marginesami, stylami naglowkow i przypisow. Nazwa: `<zestaw>-template.docx`.

   Jesli nie masz pod reka, dam Ci instrukcje jak go szybko przygotowac.

## Spis zestawow wymogow

Po dodaniu kazdego zestawu, dopisz go tutaj zeby Skill 2 wiedzial co istnieje:

<!-- POCZATEK SPISU -->

- **agh-management** (`agh-management.md`) — AGH, Wydzial Zarzadzania, kierunek Zarzadzanie. Zasada: **praktyka licencjackiej Konrada (sprawdzona, zaakceptowana) > metodyka WZ (oficjalne zalecenie)**. Stosuje sie do licencjatu i magisterki.

### Oficjalne dokumenty zrodlowe w folderze:

- `thesis-writing-methodology-2021-11.pdf` — oficjalna metodyka pisania prac na **Wydziale Zarzadzania AGH** (oryginal: `metodyka_pisania_prac_dyplowych_11_2021.pdf`). Glowne zrodlo uzupelniajace.
- `guidelines.pdf` — **IGNOROWANE**. Dokument o tytule "Zalecenia dotyczace struktury i strony edytorskiej..." (oryginal: `wytyczne.pdf`) — wyglada na wytyczne **innego wydzialu lub starsza wersje** (rozni sie m.in. systemem cytowania: [n] zamiast przypisow dolnych, lustrzane marginesy, dwustronny druk). Trzymany w folderze dla referencji, ale **nie jest zrodlem decyzji** dla skilla.

<!-- KONIEC SPISU -->
