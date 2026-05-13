---
name: code-review
description: Interaktywny code review pull requesta. Najpierw pyta o poziom surowosci (lagodny / normalny / surowy), zakres uwag (krytyczne / +srednie / wszystko) i cel (komentarze na GitHub vs poprawki lokalnie). Pokazuje co sie zmienilo w PR, uruchamia rownolegla analize wieloagentowa (na wzor `/code-review:code-review`), a nastepnie prowadzi krok-po-kroku przez kazde znalezisko pytajac czy dodac komentarz / naprawic / pominac. Uzyj gdy uzytkownik mowi: "zrob code review", "przejrzyj PR", "zreviewuj PR", "code review #1234", "review PR 1234", "code review tego brancha", "przegladnij zmiany w PR", "ile bugow w PR", "skomentuj PR". Takze gdy uzytkownik prosi o ocene zmian w pull requescie lub chce zostawic uwagi reviewerskie.
allowed-tools: Bash(git:*), Bash(gh:*), AskUserQuestion, Read, Grep, Glob, Edit, Agent
---

# Code Review

Interaktywny code review pull requesta z konfigurowalna surowoscia, filtrowaniem severity i wyborem czy postowac komentarze na GitHub czy poprawiac kod lokalnie.

Cala komunikacja z uzytkownikiem po polsku.

## Krok 1: Identyfikacja PR

Mozliwe wejscia:
- Numer PR podany w wiadomosci (np. "1234", "#1234", "PR 1234")
- URL PR (np. `https://github.com/owner/repo/pull/1234`)
- Brak argumentu — uzyj PR z aktualnego brancha

```bash
# PR dla aktualnego brancha
gh pr list --head "$(git branch --show-current)" --json number,title,url,headRefOid,baseRefName --jq '.[0]'

# PR po numerze
gh pr view {pr_number} --json number,title,url,headRefOid,baseRefName,author
```

Jesli nie ma PR ani argumentu, poinformuj uzytkownika i zakoncz. Nie zgaduj numeru.

Zapisz: `pr_number`, `pr_title`, `commit_sha` (headRefOid), `base_branch`, `owner/repo`:
```bash
gh repo view --json nameWithOwner --jq '.nameWithOwner'
```

## Krok 2: Konfiguracja review (zapytaj uzytkownika)

Uzyj **`AskUserQuestion`** zeby zebrac trzy odpowiedzi w jednej tabelce z trzema pytaniami:

1. **Poziom surowosci** — jak ostro Claude ma analizowac kod
2. **Zakres uwag** — ktore severity raportowac
3. **Cel review** — co zrobic ze znaleziskami

### Poziom surowosci

| Opcja | Threshold confidence | Zachowanie |
|---|---|---|
| Lagodny | >= 90 | Tylko pewniaki — zglaszamy tylko gdy agent jest absolutnie pewny |
| Normalny (default) | >= 75 | Wysokie confidence — odpowiada zachowaniu /code-review:code-review (ich prog to 80) |
| Surowy | >= 50 | Agresywne grillowanie — agenty maja byc krytyczne, raportujemy nawet srednio-pewne znaleziska |

Threshold zostanie uzyty w kroku 5 do filtrowania.

### Zakres uwag (severity filter)

| Opcja | Co raportujemy |
|---|---|
| Tylko krytyczne | Bug / Security / Broken functionality |
| Krytyczne + srednie (default) | Powyzsze + Architektura / Wydajnosc / CLAUDE.md violations |
| Wszystko | Powyzsze + Style / Nitpicki / Sugestie |

Severity zostanie sklasyfikowana przez agentow w kroku 4 i uzyta do filtrowania w kroku 5.

### Cel review

| Opcja | Konsekwencja |
|---|---|
| Komentarze na GitHub | Dla kazdego zatwierdzonego znaleziska postujemy inline comment przez `gh api .../pulls/{pr}/comments` (per plik, per linia) |
| Poprawki lokalnie | Dla kazdego zatwierdzonego znaleziska edytujemy kod lokalnie (jak `kp:address-review-comments`). Po skonczeniu uzytkownik sam commit'uje. |

Zapisz wybory: `strictness_threshold`, `severity_filter`, `goal`.

## Krok 3: Streszczenie zmian w PR

Zanim odpalisz analize, pokaz uzytkownikowi krotkie streszczenie co jest w PR — zeby wiedzial co bedzie reviewowane.

```bash
# Lista plikow
gh pr view {pr_number} --json files --jq '.files[] | "\(.path) (+\(.additions) -\(.deletions))"'

# Diff (full)
gh pr diff {pr_number}
```

Wygeneruj streszczenie w formacie:

```
### PR #{number}: {title}
**Autor:** @{author}
**Base:** {base_branch} ← **Head:** {commit_sha:0:7}

**Zmienione pliki ({count}):**
- path/to/file.ts (+12 -3) — krotki opis czego dotyczy
- path/to/other.tsx (+5 -1) — krotki opis

**Zakres zmian:** 1-2 zdania o tym co PR robi — wyciagniete z diff/opisu PR.
```

Nie pytaj uzytkownika o akceptacje — to tylko informacja, lecimy dalej.

## Krok 4: Rownolegla analiza wieloagentowa

Spawn piec agentow rownolegle (jeden `Agent` tool call z wieloma sub-agentami w tej samej wiadomosci). Wzorzec na `/code-review:code-review`, ale z dwoma zmianami:

1. Agenty **nie postuja niczego na GitHub** — zwracaja findings jako ustrukturyzowany JSON
2. Kazde znalezisko **klasyfikuja po severity** zeby pozniej dalo sie filtrowac

Sciezki CLAUDE.md do uzycia w prompcie (zbierz wczesniej):
```bash
# Root CLAUDE.md
ls CLAUDE.md 2>/dev/null

# CLAUDE.md w katalogach zmienionych plikow
gh pr view {pr_number} --json files --jq '.files[].path' | xargs -I {} dirname {} | sort -u | while read dir; do
  while [ "$dir" != "." ] && [ "$dir" != "/" ]; do
    [ -f "$dir/CLAUDE.md" ] && echo "$dir/CLAUDE.md"
    dir=$(dirname "$dir")
  done
done | sort -u
```

### Prompty dla agentow

Kazdy agent dostaje ten sam **wspolny kontekst**:
```
PR #{number}: {title}
Repo: {owner}/{repo}
Commit SHA: {commit_sha}
Strictness: {strictness} (lagodny/normalny/surowy)
Relevant CLAUDE.md files: {lista sciezek}

Diff:
{pelny diff}
```

Plus jedna z **piec specjalizowanych ról**:

**Agent #1 — CLAUDE.md compliance**
> Sprawdz czy zmiany w tym PR sa zgodne z relevantnymi plikami CLAUDE.md. Pamietaj ze CLAUDE.md to wskazowki dla Claude'a piszacego kod, wiec nie wszystkie instrukcje sa zawsze relevantne. Skup sie na konkretnych naruszeniach, nie na ogolnych zasadach.

**Agent #2 — Shallow bug scan**
> Przeczytaj zmiany w PR i zrob plytkie skanowanie pod katem oczywistych bugow. Skup sie tylko na zmianach, nie czytaj zbednego kontekstu. Skup sie na duzych bugach, pomijaj drobne i nitpicki. Ignoruj prawdopodobne false-positivy.

**Agent #3 — Git history context**
> Przeczytaj `git blame` i historie zmienionych plikow zeby zidentyfikowac potencjalne bugi w kontekscie historycznym. Sprawdz czy zmiany nie cofaja wczesniej naprawionych problemow.

**Agent #4 — Previous PRs touching these files**
> Sprawdz wczesniejsze PR-y dotykajace tych samych plikow (przez `gh pr list --search "{path}"` lub historie git). Zobacz komentarze na tamtych PR-ach — czy zgloszone uwagi tez moga dotyczyc tego PR-a.

**Agent #5 — In-code comment compliance**
> Przeczytaj komentarze w kodzie zmienionych plikow. Upewnij sie ze zmiany w PR sa zgodne z wskazowkami z komentarzy (TODO, FIXME, "do not modify", uwagi reviewerow z przeszlosci).

### Format outputu kazdego agenta

Wymagaj od kazdego agenta JSON-a na koncu:

```json
{
  "findings": [
    {
      "title": "Krotki tytul (max 80 znakow)",
      "description": "Co jest nie tak i dlaczego. Jesli to naruszenie CLAUDE.md, zacytuj fragment.",
      "file": "path/to/file.ts",
      "line_start": 42,
      "line_end": 45,
      "side": "RIGHT",
      "severity": "critical | medium | minor",
      "category": "bug | security | architecture | performance | claude-md | history | style | nitpick",
      "suggestion": "Jak konkretnie to naprawic (opcjonalne, ale przydatne).",
      "agent": "claude-md | bugs | history | prev-prs | comments"
    }
  ]
}
```

Severity rubric (do dac agentom w prompcie):
- **critical** — bug ktory zlamie funkcjonalnosc, podatnosc bezpieczenstwa, broken functionality
- **medium** — problem architektoniczny, wydajnosciowy, naruszenie CLAUDE.md ktore wplywa na quality
- **minor** — drobnostka, nitpick, kwestia stylu

## Krok 5: Scoring confidence + filtrowanie

Dla **kazdego** znaleziska zwroconego w kroku 4, spawn rownolegly Haiku agent ktory ocenia confidence (0-100). To powtorzenie wzorca z `/code-review:code-review`.

Prompt scoringowy (verbatim — przekaz do agenta):

```
Ocen confidence ze ponizsze znalezisko z code review to prawdziwy problem, a nie false positive.

PR: {pr_number}
Plik: {file}:{line_start}-{line_end}
Znalezisko: {title}
Opis: {description}
Kategoria: {category}
Relevant CLAUDE.md: {paths}

Diff dotyczacych linii:
{diff_hunk}

Rubric:
- 0: Zupelnie nie pewny. False positive ktory nie wytrzymuje krytyki, lub pre-existing issue.
- 25: Slabo pewny. Moze byc realnym problemem, ale moze byc tez false-positive. Jesli stylistyczne — nie wskazane w CLAUDE.md.
- 50: Umiarkowanie pewny. Realne, ale moze byc nitpick lub nie wystepuje czesto.
- 75: Bardzo pewny. Realne, wplywa na funkcjonalnosc, lub bezposrednio wskazane w CLAUDE.md.
- 100: Absolutnie pewny. Definitywnie problem, wystepuje czesto, evidence to potwierdza.

Zwroc JSON: { "confidence": <0-100>, "reasoning": "<krotki powod>" }
```

### Filtrowanie

Zastosuj **dwa filtry**:

1. **Strictness threshold** (z kroku 2): odrzuc findings z `confidence < threshold`
   - Lagodny: >= 90
   - Normalny: >= 75
   - Surowy: >= 50

2. **Severity filter** (z kroku 2):
   - Tylko krytyczne: zostaw tylko `severity == critical`
   - Krytyczne + srednie: zostaw `critical` i `medium`
   - Wszystko: zostaw wszystko

### Deduplikacja

Jesli kilka agentow zglasza ten sam problem w tym samym pliku/linii (np. agent CLAUDE.md i agent bugs trafili na to samo), polacz w jeden finding — zachowaj najwyzsze confidence i polacz `agent` jako liste.

### Sortowanie

Posortuj findings: najpierw `critical`, potem `medium`, potem `minor`. W obrebie severity — po `confidence` malejaco.

Jesli po filtrowaniu **zero findings** — powiedz uzytkownikowi: "Nie znaleziono zadnych problemow przy wybranych ustawieniach. PR wyglada czysto." i zakoncz.

## Krok 6: Iteracja po znaleziskach

Dla **kazdego** znaleziska po kolei:

### 6a. Prezentacja

Pokaz uzytkownikowi:

```
### Znalezisko [N/total] — [SEVERITY] — confidence [X]%
**Plik:** {file}:{line_start}-{line_end}
**Kategoria:** {category}
**Zglosil:** {agent(s)}

**Problem:** {description}

**Sugestia:** {suggestion lub "—"}

**Diff context:**
\`\`\`
{linie z diff_hunk}
\`\`\`
```

### 6b. Decyzja uzytkownika

**Jesli goal = "komentarze na GitHub":**

Najpierw zaproponuj **draft komentarza** od razu pod opisem znaleziska — nie czekaj az uzytkownik poprosi. Domyslny format po polsku:

```
**{title}**

{description}

{Jesli suggestion istnieje:}
Sugestia:
{suggestion}
```

Potem `AskUserQuestion` z opcjami:
- **Wyslij komentarz** — postuj draft 1:1 przez `gh api`
- **Przeredaguj** — wejdz w petle dialogu (patrz nizej)
- **Pomin** — przejdz dalej bez postowania

**Jesli goal = "poprawki lokalnie":**

`AskUserQuestion` z opcjami:
- **Napraw** — zastosuj sugestie (edytuj plik)
- **Pokaz wiecej kontekstu** — przeczytaj wiecej linii z pliku, potem zapytaj ponownie
- **Pomin** — przejdz dalej

### 6c. Akcja

**Dla "Wyslij komentarz":** wywolaj `gh api` (patrz 6d nizej), zapamietaj jako "dodany".

**Dla "Przeredaguj"** (petla redakcyjna):

To **nie jest pojedyncza edycja** — to dialog ktory moze trwac kilka rund. Uzytkownik bedzie typowo prosil o:
- skrocenie / wydluzenie ("za dlugie", "rozwin punkt o X")
- zmiane tonu ("mniej kategorycznie", "bardziej bezposrednio", "miekszy", "ostrzejszy")
- inny jezyk ("po angielsku", "po polsku")
- dodanie/usuniecie elementu ("dodaj odnosnik do tej funkcji", "wywal sugestie kodu", "dodaj pytanie zamiast stwierdzenia")
- konkretny rewrite ("napisz to inaczej, np. ...", "uzyj formy pytajacej")
- zmiane targetu linii ("to powinno byc na linii 45 nie 42")

Zasady petli:
1. **Pokaz aktualny draft za kazdym razem** — nawet jesli zmiana jest mala, wypisz pelna nowa wersje zeby uzytkownik widzial finalne brzmienie. Bez "tak, zrobione" bez tekstu.
2. **Nie postuj az do explicit potwierdzenia** — po kazdej rewizji ponownie zapytaj `AskUserQuestion`: **Wyslij** / **Dalsze zmiany** / **Pomin**.
3. **Zachowaj kontekst rozmowy** — uzytkownik moze mowic "wroc do poprzedniej wersji" albo "zmien tylko ten fragment". Trzymaj historie wersji w glowie.
4. **Nie nadinterpretuj** — jak uzytkownik pisze "skroc", skroc nie zmieniajac merytoryki. Jak pisze "zmien ton", zostaw tresc faktyczna.
5. **Mozesz zaproponowac 2 warianty** — jesli prosba jest niejednoznaczna ("napisz to lepiej"), pokaz dwie wersje (A i B) zamiast zgadywac.
6. **Postuj tylko po jednoznacznym "wyslij"** — nie postuj na slowach typu "ok", "dobra", "fajne". Czekaj na akcje wybrana przez `AskUserQuestion`.

**Dla "Napraw" (goal lokalnie):** zastosuj sugestie przez `Edit` tool. Jesli `suggestion` jest pusta lub niejasna, najpierw przeczytaj plik dookola wskazanej linii zeby zaproponowac konkretna zmiane, pokaz ja uzytkownikowi i zastosuj po potwierdzeniu.

**Dla "Pomin":** nic nie rob, przejdz dalej.

Zapamietuj decyzje (ile dodano komentarzy, ile naprawiono, ile pominieto) — potrzebne w kroku 7.

### 6d. Postowanie komentarza przez `gh api`

```bash
# Inline comment, single line
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="{comment_body}" \
  -f commit_id="{commit_sha}" \
  -f path="{file}" \
  -F line={line_end} \
  -f side=RIGHT
```

```bash
# Inline comment, multi-line (gdy line_start != line_end)
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="{comment_body}" \
  -f commit_id="{commit_sha}" \
  -f path="{file}" \
  -F start_line={line_start} \
  -F line={line_end} \
  -f start_side=RIGHT \
  -f side=RIGHT
```

Jesli `gh api` zwroci blad (np. linia spoza diff range, plik nie istnieje w commicie), poinformuj uzytkownika krotko i zaproponuj fallback:
- **PR-level comment** (top-level, bez linkowania do linii):
  ```bash
  gh pr comment {pr_number} --body "{comment_body z prefiksem o pliku/linii}"
  ```
- Albo **Pomin** — przejdz dalej.

## Krok 7: Podsumowanie

Po przejsciu wszystkich findings, pokaz krotkie podsumowanie:

```
### Podsumowanie code review PR #{number}

**Konfiguracja:** {strictness} / {severity_filter} / cel: {goal}
**Znaleziono:** X findings (przed filtrowaniem: Y)

**Wynik:**
- Dodano komentarzy na GitHub: A
- Naprawiono lokalnie: B
- Pominieto: C

{Jesli dodano komentarze:} Link do PR: {pr_url}
{Jesli naprawiono lokalnie:} Pamietaj zacommitowac zmiany przed kolejnym pushem.
```

Jesli `goal = "poprawki lokalnie"` i sa nowe zmiany w worktree, zaproponuj komende:
```bash
git status
git diff
```

## Wazne zasady

1. **Zbieraj findings, nie postuj zbiorczo** — wzorzec z `/code-review:code-review` postuje jeden zbiorczy komentarz. My postujemy inline comments per-finding, tylko te ktore uzytkownik zaakceptowal.

2. **Confidence > 80 to nie automatyczny pass** — uzytkownik moze ustawic prog na 50 (Surowy) i wtedy widzi srednio-pewne znaleziska. To celowe.

3. **Severity klasyfikacja przez agentow** — w prompcie dla agentow podaj rubric (critical/medium/minor) i wymagaj zeby kazde znalezisko mialo `severity`.

4. **Czytaj kod gdy potrzeba** — jesli finding ma niejasna sugestie albo `Pokaz wiecej kontekstu`, uzyj `Read` na konkretnym pliku.

5. **Nie postuj jako bot** — komentarze ida z konta uzytkownika (`gh` uzywa jego tokena). Nie dodawaj stopek typu "Generated with Claude Code" do inline comments — to nie zbiorczy review.

6. **Multi-line findings** — gdy `line_start != line_end`, uzyj wariantu API z `start_line`. Single-line — bez `start_line`.

7. **Idempotentnosc** — jesli ten sam PR jest reviewowany drugi raz, nie sprawdzaj czy jakies komentarze juz tam sa. Uzytkownik moze chciec dorzucic kolejne uwagi po nowej iteracji.

8. **Limit findings na widok** — jesli po filtrowaniu jest > 20 findings, zapytaj uzytkownika czy chce iterowac po wszystkich, czy tylko po top N (np. tylko critical, albo tylko top 10 po confidence).

9. **Skala promptu agenta** — gdy diff jest duzy (> 2000 linii), przekaz agentom tylko zmienione hunki, nie caly diff. `gh pr diff` zwraca caly diff — mozna go pociac per plik przed wyslaniem.

10. **Pre-existing issues** — agenty maja ignorowac problemy ktore istnialy przed tym PR-em. Wskaz to wprost w ich prompcie (jak `/code-review:code-review`).
