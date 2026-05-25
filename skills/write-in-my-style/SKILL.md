---
name: write-in-my-style
description: Pisze tekst (rozdzial pracy magisterskiej, fragment licencjatu, esej, akapit, wstep, podsumowanie) w stylu uzytkownika na podstawie profile/writing-style.md, z opcjonalnym formatowaniem zgodnym z wymogami uczelnianymi (profile/university-requirements/*.md) i generowaniem DOCX. Skill pyta o tryb (dyplomowa vs esej), zestaw wymogow (gdy dyplomowa), wczytuje profil stylu, pisze tekst akapit po akapicie z weryfikacja zgodnosci ze stylem (mini-checklist), generuje markdown z przypisami dolnymi i konwertuje na DOCX zgodny z formatem uczelni. Uzyj gdy uzytkownik mowi: "napisz w moim stylu", "napisz akapit o X", "rozdzial magisterki o X", "esej o X w moim stylu", "wstep do pracy", "podsumowanie pracy", "fragment pracy o X", "wygeneruj tekst o X jak ja", "ja bym to napisal". Takze gdy uzytkownik chce napisac jakikolwiek dluzszy tekst w wlasnym stylu na potrzeby pracy akademickiej, eseju lub innego tekstu, ktory ma brzmiec jak on.
allowed-tools: Read, Bash(python3:*), Bash(pandoc:*), Bash(ls:*), Bash(open:*), AskUserQuestion, Write, Edit, Glob
---

# Pisanie w stylu uzytkownika

Skill pisze tekst akademicki (lub esej) w stylu uzytkownika, generujac markdown a nastepnie DOCX zgodny z wymogami uczelnianymi.

Komunikacja z uzytkownikiem po polsku.

## Krok 0: Sprawdz dostepnosc artefaktow

```bash
# Sprawdz czy istnieje profil stylu
ls profile/writing-style.md && echo "PROFIL_OK"

# Wylistuj dostepne zestawy wymogow
ls profile/university-requirements/*.md 2>/dev/null | grep -v README

# Sprawdz template'y DOCX
ls profile/university-requirements/*-template.docx 2>/dev/null

# Sprawdz dostepnosc narzedzi
which pandoc
python3 -c "from docx import Document"
```

Jesli brakuje `profile/writing-style.md` — przerwij i poinformuj uzytkownika ze trzeba najpierw uruchomic skill `analyze-writing-style`.

Jesli brakuje template DOCX dla wybranego zestawu wymogow — wygeneruj go:
```bash
python3 skills/write-in-my-style/scripts/build_template.py \
    profile/university-requirements/<zestaw>.md \
    profile/university-requirements/<zestaw>-template.docx
```

## Krok 1: Zbierz kontekst zadania

Pytania do uzytkownika (`AskUserQuestion`):

1. **Tryb tekstu:**
   - praca dyplomowa (licencjat / magisterka / doktorat) — z przypisami, formalna
   - esej / praca zaliczeniowa — krotsza forma, bez przypisow
   - akapit / krotki fragment — pojedynczy odcinek do wkomponowania w wiekszy tekst
   - cos innego (uzytkownik dopisze)

2. **Zestaw wymogow uczelnianych** (jesli tryb = dyplomowa, i jest wiecej niz jeden zestaw w `profile/university-requirements/`):
   - Wymien dostepne zestawy (np. `agh-management`)
   - Domyslny jeden = nie pytaj

3. **Temat / zarys** (mozna ominac pytanie jesli juz jest w prompcie):
   - Co konkretnie ma byc napisane?
   - Czy uzytkownik ma juz plan, czy mamy zaproponowac strukture?

4. **Format wynikowy** (jesli dyplomowa lub esej):
   - Tylko markdown (uzytkownik sam konwertuje)
   - Markdown + DOCX (Recommended dla dluzszych tekstow)

5. **Zrodla do cytowania** (jesli dyplomowa, na podstawie czego pisac):
   - Uzytkownik dostarczy listy zrodel (autor, tytul, miasto/rok, strony)
   - Pisz "z palca" z mockowymi przypisami, uzytkownik je zamieni — UWAGA, nie zalecane bo szkoda czasu
   - Bez przypisow w tym fragmencie

## Krok 2: Wczytaj kontekst stylu

Przed pisaniem WCZYTAJ:

1. **Zawsze:** `profile/writing-style.md`, sekcje:
   - "RDZEN STYLU" (calosc)
   - "ANTY-WZORCE"
   - "MINI-CHECKLIST"

2. **Jesli tryb = dyplomowa:** dodatkowo:
   - Sekcja "WARIANT: PRACA DYPLOMOWA" z profilu
   - Caly `profile/university-requirements/<wybrany>.md`

3. **Jesli tryb = esej:** dodatkowo:
   - Sekcja "WARIANT: ESEJ" z profilu

Po wczytaniu, **wypisz uzytkownikowi 2-3 kluczowe wytyczne stylu** ktorych zamierzasz przestrzegac (np. "Bedzie duzo 'Jednakze', 'W konsekwencji', 'Mianowicie'; przypisy dolne wedle wzoru WZ; bez 'tak naprawde' bo to tryb dyplomowa"). Daj uzytkownikowi szanse skorygowac.

## Krok 3: Plan tekstu (dla dluzszych form)

Dla tekstu >500 slow zaproponuj plan:
- Liczba akapitow
- O czym kazdy akapit
- Mozliwe podrozdzialy (jesli dyplomowa)

Uzyskaj akceptacje uzytkownika przed pisaniem. Akceptacja moze byc "OK", "zmien X", "dorzuc Y".

## Krok 4: Pisz akapit po akapicie

To jest KRYTYCZNY krok — nie generuj calego tekstu naraz. Pisz **JEDEN akapit**, weryfikuj go przez mini-checklist z profilu, pokaz uzytkownikowi.

### Procedura per akapit:

1. **Napisz akapit** trzymajac sie wytycznych z profilu:
   - Dlugie zlozone zdania (30+ slow, lancuchowe)
   - 1-2 z ulubionych spojnikow (Jednakze / W konsekwencji / Mianowicie / Z racji / Co wiecej / Warto wspomniec / Oczywiscie / Najczesciej)
   - Bezosobowa (lub klamra "ja" we wstepie/podsumowaniu)
   - Brak czarnej listy AI ("warto podkreslic", "kluczowe znaczenie ma", "stanowi", "z perspektywy", "w dzisiejszych czasach", "reprezentuje")
   - W trybie dyplomowa: BEZ "tak naprawde", BEZ "Z racji faktu, ze" (uzyj "Poniewaz"), zdania kompletne
   - W trybie esej: powyzsze manieryzmy moga zostac 1-2 razy
   - Powtarzanie kluczowych rzeczownikow zamiast zaimkow — chetnie

2. **Auto-weryfikacja mini-checkliscie**. Po napisaniu, przejdz przez kazdy punkt z `profile/writing-style.md` sekcji "MINI-CHECKLIST" — czy spelnione? Jesli nie, popraw zanim pokazesz uzytkownikowi.

3. **Pokaz akapit uzytkownikowi** wraz z krotka adnotacja co jest specyficznie "z jego stylu":
   ```
   AKAPIT N:

   [tekst akapitu]

   Sygnatury stylu w tym akapicie: <Jednakze, W konsekwencji, powtorzenie 'spolka cywilna'>
   ```

4. **Pytaj o akceptacje** dla tego akapitu zanim pisz nastepny:
   - OK, idz dalej
   - Popraw X
   - Przepisz inaczej
   - Cofnij i przemysl plan

To **wolniejsze** niz generowanie naraz, ale **trafniejsze**. Lepiej 5 akapitow zaakceptowanych niz 10 do przepisania.

### Przypisy dolne (tylko tryb dyplomowa)

Po kazdym konkretnym fakcie, cytacie lub cudzym pogladzie wstaw przypis.

Format markdown:
```markdown
Tekst ze stwierdzeniem.[^1] Kolejne stwierdzenie.[^2]

[^1]: M. C. Layton, S. J. Ostermiller, *Zwinne zarzadzanie projektami*, Gliwice 2023, s. 40-41.
[^2]: Ibidem, s. 45.
```

Wzorce dla typow zrodel — patrz `references/przypisy-formaty.md` lub odpowiedni plik wymogow uczelnianych.

## Krok 5: Zlozenie calego tekstu

Po napisaniu wszystkich akapitow:

1. **Zlozenie do jednego pliku markdown**:
   ```markdown
   # Tytul (jesli dotyczy)

   ## 1. Rozdzial pierwszy

   [akapity z przypisami inline]

   ## 1.1 Podrozdzial

   [akapity]

   [^1]: tresc przypisu 1
   [^2]: tresc przypisu 2
   ```

   Zapisz np. do `/tmp/<temat>_<timestamp>.md` lub do `output/<temat>.md` w katalogu projektu.

2. **Sprawdz spojnosc** calego tekstu:
   - Czy przejscia miedzy akapitami sa plynne?
   - Czy przypisy maja kolejna numeracje (1, 2, 3...)?
   - Czy nie ma duplikatow tej samej obserwacji w dwoch akapitach?
   - Czy klamra (jesli dyplomowa: cel w wstepie ↔ synteza w podsumowaniu) zamyka sie?

## Krok 6: Konwersja na DOCX (jesli wybrano DOCX)

```bash
# Sprawdz czy template istnieje
ls profile/university-requirements/<zestaw>-template.docx || \
    python3 skills/write-in-my-style/scripts/build_template.py \
        profile/university-requirements/<zestaw>.md \
        profile/university-requirements/<zestaw>-template.docx

# Konwersja
python3 skills/write-in-my-style/scripts/md_to_docx.py \
    <plik.md> \
    profile/university-requirements/<zestaw>-template.docx \
    <plik.docx>
```

Po sukcesie:
- Podaj sciezke do pliku DOCX
- Zaproponuj `open <plik.docx>` (na macOS) zeby otworzyc w Wordzie
- Wymien co user musi zrobic ręcznie:
  - Wkleic strone tytulowa (skill nie generuje)
  - Zweryfikowac przypisy w Wordzie (Pandoc generuje native footnotes, ale warto sprawdzic)
  - Dodac strony spis tresci, spis tabel/rysunkow jesli sa
  - Wstawic numeracje stron (Word ma to w "Insert > Page Number")

## Krok 7: Po dostarczeniu

- Spytaj uzytkownika czy tekst spelnia oczekiwania
- Jesli nie — co nie pasuje (styl? tresc? format?) i wracaj do odpowiedniego kroku
- Jesli tak — gotowe; jesli mozesz, dorzuc 1-2 wskazowki co dalej (np. "rekomenduje doprecyzowac przypis 4, bo cytujesz cudza praca bez strony")

## Czarna lista (NIGDY w generowanym tekscie)

⚠️ Te frazy/struktury **automatycznie dyskwalifikuja** akapit — przepisz przed pokazaniem.

**Frazy:**
- "warto podkreslic"
- "kluczowe znaczenie ma"
- "w dzisiejszych czasach" / "w obecnej rzeczywistosci"
- "stanowi narzedzie" / "stanowi istotny element"
- "reprezentuje [coś]"
- "z perspektywy [czegos]" / "z punktu widzenia"
- "wspolczesne srodowisko biznesowe charakteryzuje sie"
- "akcentuje", "implementuje", "wykazuje", "obejmuje" (jako AI-czasowniki — uzywaj "podkresla", "stosuje", "ma w sobie")

**Struktury:**
- Bullety w srodku tekstu eseju/dyplomowej (Konrad pisze linearnie nawet gdy temat sie prosi)
- "Z jednej strony X, z drugiej Y" (uzywaj "Jednakze" / "Natomiast")
- Akapit-formula "wstep + 3 punkty + wniosek"
- Idealnie zbalansowane zdania tej samej dlugosci
- "Nastepnie omowimy / W tym rozdziale przedstawiono" jako szablonowe otwarcia

**Dla trybu dyplomowa specyficznie:**
- "tak naprawde" (kolokwializm — uzyj "w rzeczywistosci", "w istocie", "faktycznie" lub wyrzuc)
- "Z racji faktu, ze" (pleonazm — uzyj "Poniewaz")
- Niedokonczone zdania bez orzeczenia ("Glownym z powodow [X] spadek..." → "byl spadek")

## Tryb interaktywny vs jednorazowy

**Tryb interaktywny (domyslny):** akapit-po-akapicie z weryfikacja. Wolniejsze ale bezpieczniejsze.

**Tryb jednorazowy:** uzytkownik moze poprosic "napisz caly rozdzial naraz, sprawdze potem". Wtedy:
- Generuj wszystkie akapity bez przerw
- Po napisaniu pokaz CALOSC z lista uzytych sygnatur stylu
- Uzytkownik czyta i mowi co poprawic

Jesli uzytkownik nie sprecyzowal — domyslnie tryb interaktywny dla tekstow >500 slow, jednorazowy dla krotszych (do akapitu / 1-2 akapitow).

## Praktyczne wskazowki

1. **Czytaj profile/writing-style.md za kazdym razem** — moze byc zaktualizowany od poprzedniej sesji.

2. **Nie kopiuj cytatow z profile/writing-style.md doslownie** — to byly fragmenty z wczesniejszych prac uzytkownika. Profil pokazuje jak uzytkownik PISZE, nie co pisze. Generuj NOWE zdania w tym samym stylu.

3. **Tematyka determinuje slownictwo, styl determinuje strukture.** W eseju o ekonomii nie bedzie "k.c." ani "sensu stricto". Ale Jednakze / W konsekwencji / Mianowicie — moga byc wszedzie.

4. **Jak nie wiesz, pytaj.** Lepiej zadac uzytkownikowi pytanie o detal (data dostepu do zrodla? autor jest jeden czy z wspolautorem?) niz strzelac.

5. **Mockowe przypisy oznaczaj wyraznie.** Jesli uzytkownik dal Ci pisac bez podanych zrodel, oznaczaj przypisy "**TODO: zrodlo do dodac**" zeby on wiedzial gdzie je wstawic.

6. **Zachowaj cytaty doslowne**. Jesli uzytkownik kazal zacytowac konkretne zrodlo doslownie — uzyj cudzyslowow `„..."` lub `"..."` i nie modyfikuj cytatu.

7. **Sprawdz output DOCX zanim zwrocisz uzytkownikowi.** Po `md_to_docx.py` sprawdz:
   ```bash
   python3 -c "from docx import Document; d=Document('<plik.docx>'); print(f'{len(d.paragraphs)} akapitow, {d.sections[0].left_margin.cm}cm marginesy lewe')"
   ```
   Jesli marginesy sa zle albo brak tresci — debugowanie.
