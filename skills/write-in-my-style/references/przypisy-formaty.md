# Formaty przypisow dolnych - sciagawka

Ten plik jest sciaga dla skilla `write-in-my-style`. Skill nie musi go ladowac za kazdym razem —
wczytuje go gdy potrzebuje przypomniec sobie wzor dla konkretnego typu zrodla.

Bazowy format wedlug **metodyki WZ AGH** i **praktyki licencjackiej Konrada** (sa zbiezne).

## Markdown - jak pisac przypisy w Skill 2

Pandoc-style footnotes:

```markdown
Tekst ze stwierdzeniem.[^1] Kolejne stwierdzenie.[^2]

[^1]: M. C. Layton, *Tytul ksiazki*, Gliwice 2023, s. 40.
[^2]: Ibidem, s. 45.
```

Pandoc tworzy z tego natywne przypisy dolne w DOCX, ze stylem `Footnote Text` i automatyczna numeracja.

**WAZNE:** identyfikator `[^1]` jest tylko etykieta — Pandoc renumeruje w kolejnosci wystepowania.
Mozna uzywac mnemonikow: `[^layton]`, `[^kidyba-2020]` zamiast cyfr — czytelniejsze przy pisaniu, koncowy DOCX i tak ma cyferki.

## Wzory wedle typu zrodla (AGH WZ)

### Ksiazka — jeden autor

```
M. C. Layton, *Zwinne zarzadzanie projektami dla bystrzakow. Wydanie III*, Gliwice 2023, s. 40-41.
```

Schemat: `Inicjal. Nazwisko, *Tytul kursywa* (wydanie jesli inne niz pierwsze), Miasto rok, s. X-Y.`

### Ksiazka — wielu autorow

```
M. C. Layton, S. J. Ostermiller, D. J. Kynaston, *Zwinne zarzadzanie projektami dla bystrzakow*, Gliwice 2023, s. 40-41.
```

Wszyscy autorzy, oddzieleni przecinkami.

### Praca zbiorowa pod redakcja (bez autora pojedynczego)

```
*Meritum - prawo spolek. T. 1*, A. Kidyba (red.), Warszawa 2020, wyd. Wolters Kluwer, s. 58.
```

Schemat: `*Tytul. T. X*, [Inicjal. Nazwisko (red.)], Miasto rok, wyd. Wydawnictwo, s. XX.`

### Rozdzial w pracy zbiorowej (z wyroznionym autorstwem)

```
M. Gorzycki, "Metodyki zwinne w zarzadzaniu projektami na przykladzie branzy IT", w: *Zarzadzanie projektami w dobie postepujacej cyfryzacji i zwiekszonego ryzyka*, red. nauk. A. Laskowska-Rutkowska, Warszawa: Oficyna Wydawnicza Uczelni Lazarskiego, 2022, s. 74-75.
```

Schemat: `Inicjal. Nazwisko, "Tytul rozdzialu", w: *Tytul ksiazki kursywa*, red. nauk. Inicjal. Nazwisko, Miasto: Wydawnictwo, rok, s. X-Y.`

### Artykul w czasopismie

```
E. Wrobel, *Hybrydyzacja metodyk kanban i scrum jako narzedzie dostarczania oprogramowania*, "Informatyka Ekonomiczna / Uniwersytet Ekonomiczny we Wroclawiu", 2018, nr 2 (48), s. 94.
```

Schemat: `Inicjal. Nazwisko, *Tytul artykulu kursywa*, "Tytul czasopisma", rok, nr X (Y), s. ZZ.`

**Uwaga:** wszystkie wyrazy w nazwie czasopisma z duzej litery; cudzyslowy proste typograficzne.

### Akt prawny

```
Kodeks cywilny, Art. 860, dostepne przez: https://arslege.pl/istota-umowy-spolki/k9/a6383/, dostep: 06.11.2022 r.
```

Albo gdy chodzi o ustawe:

```
Ustawa z dnia 23 kwietnia 1964 r. Kodeks cywilny, Dz. U. 1964 nr 16 poz. 93, z pozn. zm.
```

### Zrodlo internetowe — krotka forma (gdy tylko URL i data)

```
https://pmexperts.com/wszystko-co-musisz-wiedziec-o-prince2/ [dostep: 18.08.25 r.]
```

### Zrodlo internetowe — rozszerzona forma (z autorem i tytulem)

```
P. Skurzynski, *Spolka cywilna - czym jest i jak ja zalozyc? Spolka cywilna - na czym polega?*, 2022 r., dostepne przez: https://www.doradzamy.to/artykuly/co-to-jest-spolka-cywilna-i-w-jaki-sposob-mozna-zalozyc-spolke-cywilna, dostep: 31.10.2022 r.
```

## Skroty laczace (po wstawieniu pierwszego przypisu)

### Ibidem — to samo zrodlo co poprzednie

Jesli ten sam fragment (ta sama strona):
```markdown
[^2]: Ibidem.
```

Jesli to samo zrodlo, inna strona:
```markdown
[^2]: Ibidem, s. 45.
```

### op. cit. — powtorne cytowanie pozniej

Gdy odsylasz do zrodla cytowanego wczesniej (nie ostatni przypis), uzywasz skroconej formy tytulu + `op. cit.`:

```markdown
[^7]: M. C. Layton, *Zwinne zarzadzanie projektami...*, op. cit., s. 50.
```

Skrocenie tytulu: wyrzuc czesc po pierwszych kilku slowach (zostawiajac mysl glowna), dodaj wielokropek.

### Tamze — alternatywa Ibidem w niektorych stylach

Konrad uzywa **Ibidem** (po lacinie), nie **Tamze** (po polsku). Trzymaj sie **Ibidem**.

## Cytaty doslowne

Gdy cytujemy doslownie cudzy tekst, **wymagany** jest cudzyslow + przypis dolny z dokladna strona:

```markdown
Wspólnicy spolki cywilnej "zobowiazuja sie dazyc do osiagniecia wspolnego celu gospodarczego"[^1].

[^1]: *Kodeks cywilny*, Art. 860 § 1.
```

Cudzyslowy:
- Polskie typograficzne: otwierajacy dolny `„` + zamykajacy gorny `"` → `„cytat"`
- Lub proste typograficzne: `"cytat"` — uzywaj konsekwentnie w calej pracy

## Cytaty blokowe (dluzsze niz 3-4 linijki)

Wciecie z obu stron, mniejsza czcionka. W markdown:

```markdown
Konrad w swoim eseju zauwazyl:

> "Z racji faktu, ze spolka cywilna opiera sie na wspolnej pracy jej czlonkow oraz niektore procedury tej wspolpracy nie sa doglebnie wyjasniane w kodeksie cywilnym, wspolnicy musza darzyc sie szczegolnym zaufaniem."[^3]

W konsekwencji tego, zaufanie staje sie filarem dzialalnosci.

[^3]: K. Piegza, *Spolka Cywilna*, AGH WZ 2022, s. 2.
```

Pandoc konwertuje `>` na cytat blokowy w DOCX.

## Tabela: kiedy uzywac ktorego formatu

| Sytuacja | Forma |
|---------|-------|
| Pierwszy raz cytujesz zrodlo X | Pelny format wedlug typu zrodla |
| Cytujesz X ponownie, **bezposrednio po** | `Ibidem.` lub `Ibidem, s. YY.` |
| Cytujesz X ponownie, **pozniej** (nie zaraz po) | Inicjal. Nazwisko, *Tytul skrocony...*, op. cit., s. XX. |
| Cytujesz konkretna ustawe / kodeks | Pelna nazwa + artykul + paragraf |
| Cytujesz strone WWW bez autora | URL + [dostep: data] |

## Najczestsze bledy do uniknac

- **Przecinki**: po nazwisku autora, przed miastem, przed rokiem, przed `s.`
- **Kropka na koncu przypisu** — tak, kazdy przypis konczy sie kropka
- **Spacja po skrocie**: `s. 40` (twarda spacja) zeby `s.` i `40` nie rozeszly sie na koncu wiersza
- **Kursywa tytulu**: nie zakurwa `_underscores_` ani `''` — uzywaj markdown `*tytul*`
- **Wielokrotne autorzy**: wszystkie inicjaly + nazwiska, oddzielone przecinkami; tylko ostatni bez przecinka
- **Data dostepu**: format `DD.MM.YYYY r.` lub `DD.MM.YY r.` (konsekwentnie w calej pracy)
