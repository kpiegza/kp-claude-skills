---
name: analyze-writing-style
description: Analizuje teksty uzytkownika z folderu corpus/ i generuje lub aktualizuje profile/writing-style.md - szczegolowy profil stylu pisarskiego z cytatami dowodowymi. Uzywany glownie do AKTUALIZACJI istniejacego profilu gdy uzytkownik dorzuca nowe teksty bez AI, ale takze do generowania profilu od zera. Skill prowadzi rozmowe: pyta ktore nowe pliki sa 100% manualne (bez AI), ktore w mieszane, ktore odrzucamy. Wyciaga sygnatury stylu (spojniki, dlugosc zdan, manieryzmy, anty-wzorce), proponuje aktualizacje istniejacych sekcji profilu, kazda obserwacja ma cytat dowodowy. Obsluguje tez import plikow spoza repo (z dowolnej sciezki, np. ~/Downloads/esej.docx) — sam przenosi/kopiuje do corpus/. Uzyj gdy uzytkownik mowi: "zaktualizuj profil stylu", "dorzucilem nowe teksty", "wygeneruj profil stylu", "przeanalizuj moje pisanie", "co dodalem nowego do corpus", "sprawdz nowe teksty pod katem stylu", "analiza stylu", "uaktualnij styl", "przeanalizuj plik <sciezka>", "dodaj plik <sciezka> do corpus i przeanalizuj". Takze gdy uzytkownik wrzucil nowe pliki do corpus/ albo wskazuje plik w innym folderze i prosi o ich uwzglednienie w profilu.
allowed-tools: Read, Bash(ls:*), Bash(pdftotext:*), Bash(pdfinfo:*), Bash(python3:*), Bash(find:*), Bash(mv:*), Bash(cp:*), Bash(test:*), Bash(file:*), Bash(stat:*), AskUserQuestion, Edit, Write, Grep, Glob
---

# Analiza stylu pisarskiego

Skill do generowania i aktualizacji `profile/writing-style.md` na podstawie tekstow w `corpus/`.

Cala komunikacja z uzytkownikiem po polsku.

## Co ten skill robi a czego nie

**Robi:**
- Inwentaryzuje pliki w `corpus/` i porownuje z tym co jest w aktualnym profilu
- **Importuje pliki spoza repo** (z dowolnej sciezki) do `corpus/` — domyslnie przenosi (`mv`), z mozliwoscia kopiowania (`cp`)
- Pyta uzytkownika ktore nowe pliki sa 100% manualne (bez AI)
- Wyciaga tekst z PDF (warstwowy/skan) i DOCX
- Wyciaga sygnatury stylu: spojniki, dlugosc zdan, manieryzmy, anty-wzorce, cytaty dowodowe
- Pokazuje propozycje aktualizacji profilu, uzytkownik akceptuje/odrzuca obserwacje
- Aktualizuje `profile/writing-style.md` zachowujac istniejaca strukture

**Nie robi:**
- Nie modyfikuje **zawartosci** plikow w `corpus/` (dodaje tylko nowe pliki przez import w Kroku 0b, za zgoda uzytkownika)
- Nie tworzy plikow `university-requirements/` (to oddzielna sciezka, robione recznie z dokumentow uczelnianych)
- Nie pisze profilu bez akceptacji uzytkownika dla nowych obserwacji
- Nie generuje DOCX/tekstow w stylu — to zadanie skilla `write-in-my-style`
- Nie usuwa plikow z `corpus/` (jesli importujesz `mv` ze zrodla, oryginal znika z lokalizacji zrodlowej — ale plik trafia do corpus, nigdy nie ginie)

## Krok 0: Sprawdz stan poczatkowy

```bash
# Czy istnieje juz profil?
ls profile/writing-style.md 2>/dev/null && echo "PROFIL_ISTNIEJE" || echo "BRAK_PROFILU"

# Co jest w corpus
find corpus -type f \( -name '*.pdf' -o -name '*.docx' -o -name '*.txt' -o -name '*.md' \) ! -name 'README.md' ! -name '.gitkeep' | sort
```

Decyzja:
- **PROFIL_ISTNIEJE** → tryb AKTUALIZACJI (porownujemy obecny profil z plikami w corpus, dorzucamy nowe obserwacje)
- **BRAK_PROFILU** → tryb GENEROWANIA OD ZERA (kompletny profil z podstawowymi sekcjami)

## Krok 0b: Import plikow spoza repo (opcjonalny)

Jesli uzytkownik wskazal plik (lub pliki) **spoza** `corpus/` — np. `~/Downloads/esej.docx`, `/Users/kpiegza/Desktop/praca.pdf`, sciezka relatywna do innego folderu — wykonaj import PRZED inwentaryzacja.

### Walidacja kazdego pliku

```bash
test -f "<sciezka>" && echo "OK_EXISTS" || echo "MISSING"
```

Akceptowane rozszerzenia: `.pdf`, `.docx`, `.txt`, `.md`. Inne → poinformuj uzytkownika i pomin.

```bash
# Wyciagniecie nazwy z basename i sprawdzenie konfliktu w corpus/
basename "<sciezka>"
test -f "corpus/<basename>" && echo "KONFLIKT" || echo "OK_FREE"
```

### Pytanie 1: kopiowac czy przeniesc?

Uzyj `AskUserQuestion` (jedno pytanie zbiorcze dla wszystkich nowych plikow):

- **Przenies (`mv`)** — oryginal znika ze zrodlowej lokalizacji. Domyslne, bo o tym mowil user.
- **Skopiuj (`cp`)** — oryginal zostaje na miejscu. Bezpieczniejsze dla plikow z iCloud/OneDrive/Dropbox albo wspoldzielonych folderow.
- **Anuluj import** — nie ruszaj plikow, zglos to uzytkownikowi i przerwij skill.

### Pytanie 2: konflikt nazwy (tylko gdy wystepuje)

Dla kazdego pliku ktorego nazwa juz jest w `corpus/`:

- **Nadpisz** — `mv -f` / `cp -f` (poprzedni plik zostanie utracony)
- **Zmien nazwe** — dodaj sufix `_v2`, `_v3`, ... (np. `esej_v2.docx`)
- **Pomin** — nie importuj, idz dalej

### Wykonanie importu

Po decyzjach:

```bash
# Przyklad: przeniesienie
mv "/Users/kpiegza/Downloads/esej.docx" "corpus/esej.docx"
# Lub kopia
cp "/Users/kpiegza/Downloads/esej.docx" "corpus/esej.docx"
```

**Pokaz uzytkownikowi dokladnie ktore komendy wykonujesz** zanim je odpalisz (lista przed wykonaniem) — `mv` jest operacja nieodwracalna z poziomu skilla.

### Po imporcie

- Wypisz uzytkownikowi co zostalo zaimportowane (lista: `<zrodlo>` → `corpus/<nazwa>`)
- Te pliki traktuj dalej jako "nowe" w Kroku 1 (inwentaryzacja), kandydaty do pytania o czystosc w Kroku 2
- Kontynuuj normalny flow skilla

## Krok 1: Inwentaryzacja

Wylistuj uzytkownikowi pliki w `corpus/` z metadanymi (rozmiar, typ, ile slow w przyblizeniu).

Dla DOCX:
```bash
python3 -c "
from docx import Document
d = Document('PATH')
words = sum(len(p.text.split()) for p in d.paragraphs)
print(f'slow~={words}')
"
```

Dla PDF — najpierw sprawdz czy jest warstwa tekstowa:
```bash
pdftotext PATH - | head -1
# jesli pusto → skan, trzeba uzyc Read tool na PDF jako obrazy
```

Jesli profil juz istnieje, **wskaz ktore pliki sa nowe** (nie wymienione w sekcji `zrodla:` we frontmatterze profilu).

## Krok 2: Pytaj o czystosc

⚠️ **KLUCZOWE pytanie:** ktore z plikow sa **100% manualne, bez AI**? Tylko takie wchodza do analizy stylu.

Uzyj `AskUserQuestion` z multiSelect dla nowych plikow:
- Opcja per plik: "100% moje, bez AI" / "Mieszane (AI + redakcja)" / "Glownie AI"
- Lub jedna lista z multiSelect ktore sa czyste

Plus opcja dla mieszanych: uzytkownik moze wskazac KONKRETNE fragmenty ktore sa jego (np. po akapicie) — wtedy do analizy bierzemy tylko te.

## Krok 3: Wyciaganie tekstu

**DOCX** — przez python-docx:
```python
from docx import Document
doc = Document('PATH')
text = '\n\n'.join(p.text for p in doc.paragraphs if p.text.strip())
```

**PDF z warstwa tekstowa** — przez `pdftotext`:
```bash
pdftotext "PATH" -
```

**PDF-skan** — uzyj narzedzia Read na PDF (parametr `pages: "1-N"`), model zrobi OCR przez obrazy stron.

**TXT/MD** — Read.

Zapisz wyciagniety tekst do tymczasowego pliku, np. `corpus/.extracted/<nazwa>.txt` (dodaj `.extracted/` do `.gitignore` jesli nie ma), zeby nie powtarzac ekstrakcji.

## Krok 4: Analiza — co konkretnie wyciagac

Analizuj dane z perspektywy nastepujacych kategorii. **Kazda obserwacja musi miec cytat dowodowy z tekstu uzytkownika**.

### 4a. Skladnia
- Sredni i mediana dlugosci zdan (slow na zdanie)
- Najdluzsze zdanie jako przyklad
- Czy uzytkownik buduje lancuchowe konstrukcje przyczyna→skutek?
- Czy uzywa zdan zlozonych podrzednie? Z iloma podrzednikami sredio?

### 4b. Spojniki i laczniki (sygnatura)
Wyszukaj **wystapienia** charakterystycznych spojnikow uzywanych przez tego uzytkownika.

Lista do sprawdzenia (zaktualizuj jesli profil istnieje):
- "Jednakze" / "Jednak" / "Natomiast"
- "W konsekwencji" / "Dzieki temu" / "Czego skutkiem"
- "Z racji" / "Z racji faktu" / "Poniewaz" / "Jest to spowodowane"
- "Mianowicie" / "Dokladniej" / "Konkretnie" / "Czyli"
- "Co wiecej" / "Warto wspomniec" / "Warto dodac" / "Warto nadmienic"
- "Po pierwsze" / "Po drugie"
- "Oczywiscie" / "Najczesciej" / "Zazwyczaj" / "Zdecydowanie"

Wypisz frekwencje (ile razy w korpusie) i 1-3 cytaty dla najczesciej uzywanych.

### 4c. Strona i osoba
Przeanalizuj proporcje:
- Bezosobowa ("mozna", "trzeba", "zbadano")
- 1. os. lm. ("powinnismy", "weziemy")
- 1. os. lp. ("uwazam", "moge stwierdzic")
- Bierna ("zostal zbadany")

Czy sa miejsca **klamry** (wstep + podsumowanie w 1 os. lp.)?

### 4d. Manieryzmy
Szukaj:
- Pleonazmow ("Z racji faktu, ze", "tak naprawde" w akademickim)
- Awkward konstrukcji (np. niedokonczone zdania, nieuzgodnione orzeczenia)
- Powtarzania kluczowych rzeczownikow zamiast zaimkow
- Kolokwializmow w akademickim ("na ten moment", "w tym przypadku")
- Charakterystycznych czasow (terazniejszy historyczny w opisach przeszlosci)

### 4e. Anty-wzorce (czego NIE robi)
Sprawdz CZY NIE wystepuja typowe AI-frazy (jesli wystepuja u uzytkownika — to znaczy ze to nie sa anty-wzorce dla niego):
- "warto podkreslic"
- "kluczowe znaczenie ma"
- "w dzisiejszych czasach"
- "z perspektywy / z punktu widzenia"
- "stanowi narzedzie / reprezentuje ujecie"
- "wspolczesne srodowisko biznesowe charakteryzuje sie"

### 4f. Rytm akapitu
- Srednia liczba zdan w akapicie
- Czy pierwsze zdanie akapitu jest ogolne czy konkretne?
- Czy ostatnie zdanie wprowadza bridge do nastepnego watku?

## Krok 5: Propozycja aktualizacji profilu

Pokaz uzytkownikowi **kazda nowa obserwacje** wedlug schematu:

```
=== Obserwacja: <krotki tytul> ===
Kategoria: <ktora sekcja profilu>
Co dodaje: <konkretna obserwacja>
Cytat dowodowy: "<...>"
Frekwencja: <ile wystapien>
Decyzja: dodac / pominac / zmodyfikowac istniejaca obserwacje
```

Uzyj `AskUserQuestion` dla 5-10 najwazniejszych obserwacji na raz. Pominijate ktore juz sa w profilu albo sa marginalne.

### Specjalnie: rzeczy ktore podwazaja istniejacy profil

Jesli analiza pokazuje rozbieznosc z istniejacym profilem (np. profil mowi "uzywa X", a nowe teksty pokazuja ze "juz nie uzywa X albo uzywa Y") — **zapytaj uzytkownika**:
- Czy to ewolucja stylu (zaktualizujmy profil)?
- Czy to zmienna zaleznie od kontekstu (dodajmy warunek)?
- Czy to blad starego profilu (poprawmy)?

## Krok 6: Aktualizacja profilu

Po akceptacji obserwacji przez uzytkownika:

1. Wczytaj obecny `profile/writing-style.md` (lub utworz nowy ze szkielu jesli BRAK_PROFILU)
2. Aktualizuj odpowiednie sekcje przez Edit (a nie przepisuj calego pliku)
3. Zaktualizuj frontmatter:
   - `wersja:` — zwieksz numer (1.0 → 1.1)
   - `zrodla:` — dopisz nowe pliki
   - `status:` — np. "zaktualizowany YYYY-MM-DD"
4. Pokaz uzytkownikowi diff (przez Bash `git diff profile/writing-style.md`) i poproś o ostateczna akceptacje

## Szkielet profilu (gdy generujemy od zera)

Jesli BRAK_PROFILU, utworz `profile/writing-style.md` z nastepujaca struktura:

```markdown
---
nazwa: writing-style-<imie>-<nazwisko>
wersja: 1.0
zrodla:
  - <lista plikow z corpus, ktore weszly do analizy>
status: pierwszy draft - do iteracji
---

# Profil stylu pisarskiego — <Imie Nazwisko>

## Jak uzywac tego pliku

[instrukcja dla Skill 2 jak czytac profil]

## RDZEN STYLU (zawsze stosuj)

### 1. Skladnia
### 2. Spojniki i laczniki (sygnatura)
### 3. Strona i osoba
### 4. Powtarzanie rzeczownikow zamiast zaimkow
### 5. Pewnosc wypowiedzi
### 6. Manieryzmy
  6a. ZOSTAJA (zawsze) — strukturalne
  6b. CIECIA w trybie dyplomowa — puste konstrukcje
### 7. Rytm akapitu
### 8. Czas terazniejszy historyczny (jesli wystepuje)

## WARIANT: PRACA DYPLOMOWA
## WARIANT: ESEJ
## ANTY-WZORCE (czego AI uzywa, czego Ty NIE)
## MINI-CHECKLIST DLA SKILL 2

## NIEWIADOME / DO UZUPELNIENIA W KOLEJNYCH ITERACJACH
```

## Praktyczne wskazowki

1. **Cytaty sa zlote.** Bez cytatow nie ma obserwacji. Jesli nie mozesz znalezc cytatu na poparcie obserwacji — nie wpisuj jej.

2. **Roznicuj tryby.** Co innego pojawia sie w pracy dyplomowej (przypisy, gestszy jezyk), co innego w eseju (czas terazniejszy historyczny, brak przypisow). Zapisuj obserwacje do odpowiedniego wariantu.

3. **Nie generalizuj na podstawie jednego cytatu.** Jesli obserwacja ma 1 wystapienie, sklasyfikuj jako "marginalne", nie "manieryzm". Powtarzajace sie wzorce (3+ wystapien) to manieryzmy.

4. **Pytaj o ewolucje stylu.** Uzytkownik moze pisac dzisiaj inaczej niz 3 lata temu. Pytaj: "ktore teksty sa najnowsze i czy chcesz zeby profil odzwierciedlal je preferencyjnie?"

5. **Marginalia kontekstu vs styl.** Slowo "spolka" wystepuje 100 razy w eseju o prawie spolek — to nie manieryzm stylu, to tematyka. Filtruj kontekst.

6. **Czarna lista AI** — to dla **kontrastu**: jesli **nie wystepuja** u uzytkownika, sa silnym sygnalem czego skill ma unikac.

## Po zakonczeniu

- Powiedz uzytkownikowi czy plik zostal zapisany
- Podaj sciezke do zaktualizowanego profilu
- Jesli sa otwarte pytania (TODO/Niewiadome), wymien je
