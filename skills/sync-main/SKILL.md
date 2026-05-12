---
name: sync-main
description: Synchronizuje bieżący branch ze zmianami z origin/main (`git fetch` + `git merge`) i automatycznie rozwiązuje konflikty — w szczególności specjalny przypadek CHANGELOG.md gdy ten sam numer wersji istnieje na main i na branchu (wpis z main zostaje, wpis użytkownika dostaje wyższy patch). Ogarnia też CHANGELOG-i (apps/panel, apps/api) i konflikty w plikach i18n (en.json/de.json). Po rozwiązaniu robi commit merge'a (push robi użytkownik ręcznie). Triggeruj zawsze gdy użytkownik mówi: "zmerguj main", "pobierz zmiany z main", "scal main do brancha", "ściągnij main", "rozwiąż konflikt changelog", "merge from main", "pull main into branch", "update branch from main", "sync z main", "zaktualizuj brancha z main".
allowed-tools: Read, Edit, Write, Bash(git:*), AskUserQuestion
---

# Merge Main with Smart Conflict Resolution

Bierzesz najnowsze zmiany z `origin/main` i mergujesz do brancha. Konflikty rozwiązujesz inteligentnie — szczególnie CHANGELOG-i, gdzie wpis użytkownika musi trafić nad wpis z main z bumpniętym numerem wersji.

## Workflow

### Krok 1: Sanity check stanu repo

```bash
git status --porcelain
git rev-parse --abbrev-ref HEAD
```

Jeśli są niezacommittowane zmiany — **przerwij** i powiedz użytkownikowi, że ma czysty branch zanim zaczniesz merge. Niezacommittowane zmiany podczas merge'a to przepis na utratę pracy.

Jeśli branch to `main`/`master` — przerwij, bo nie ma sensu mergować maina do siebie.

### Krok 2: Fetch i merge

```bash
git fetch origin main --quiet
git merge origin/main --no-edit
```

Jeśli merge się uda bez konfliktów — koniec, powiedz użytkownikowi że gotowe i czeka na ręczny push.

### Krok 3: Diagnoza konfliktów

```bash
git status --porcelain | grep '^UU\|^AA\|^DD'
```

Zgrupuj konflikty na trzy kategorie:
- **CHANGELOG** (`*/CHANGELOG.md`) — specjalna logika wersjonowania (Krok 4)
- **i18n** (`*/i18n/*.json`) — merge JSON-ów (Krok 5)
- **Inne** — kod, configi, etc. (Krok 6)

### Krok 4: Rozwiązywanie CHANGELOG-ów

To jest kluczowy przypadek. Reguła:

> Jeśli na origin/main istnieje wpis pod tym samym numerem wersji co mój wpis w branchu, wpis z main zostaje pod swoim numerem, **mój wpis idzie wyżej i dostaje wyższy patch** (`0.1.73` → `0.1.74`).

**Przebieg:**

1. Otwórz plik z konfliktem i znajdź sekcje `<<<<<<< HEAD ... ======= ... >>>>>>> origin/main`.

2. Wyciągnij wersje z obu stron — pierwsza linia każdej strony to nagłówek `## [X.Y.Z] - YYYY-MM-DD`.

3. **Decyzja na podstawie numerów wersji:**

   | Mój branch (HEAD) | origin/main | Akcja |
   |-------------------|-------------|-------|
   | `0.1.73` | `0.1.73` | Mój wpis bumpnij na `0.1.74` (patch+1), wpis z main zostaje pod `0.1.73`. **Mój idzie wyżej.** |
   | `0.1.73` | `0.1.74` | Mój wpis bumpnij na `0.1.75` (patch+1 vs max), idzie wyżej. Wpis z main `0.1.74` zostaje. |
   | `0.1.74` | `0.1.73` | Mój wpis (`0.1.74`) zostaje na swoim numerze i idzie wyżej (już ma wyższy numer). Wpis z main `0.1.73` zostaje pod sobą. |
   | różne wersje, brak kolizji | — | Po prostu połącz oba bloki: mój wyżej, main niżej. |

   Reguła ogólna: `nowa_wersja_użytkownika = max(moja_wersja, main_wersja) + patch(1)` jeśli była kolizja, inaczej moja wersja zostaje.

4. **Aktualizacja daty wpisu użytkownika:**
   Sprawdź `currentDate` z kontekstu sesji (system reminder). Jeśli data we wpisie użytkownika jest inna niż dzisiejsza — zaktualizuj na dzisiejszą. Wpis z main zostaw z jego oryginalną datą.

5. **Format wynikowy** (przykład dla kolizji `0.1.73` vs `0.1.73`, dziś `2026-04-27`):

   ```markdown
   ## [0.1.74] - 2026-04-27

   ### Added
   - <wpisy użytkownika z [@user]>

   ### Changed
   - <wpisy użytkownika>

   ### i18n
   - <wpisy użytkownika>

   ## [0.1.73] - <data oryginalna z main>

   ### Added
   - <wpisy z main>

   ### Changed
   - <wpisy z main>
   ```

6. Zachowaj wszystkie sekcje (`### Added`, `### Changed`, `### Fixed`, `### i18n`, etc.) z każdej strony — nie zlewaj ich w jedną listę. Jeśli któraś strona miała pustą sekcję, pomiń ją.

7. Resztę pliku (starsze wersje pod konfliktem) zostaw bez zmian.

8. **Powtórz dla każdego CHANGELOG-a w konflikcie** (`apps/panel/CHANGELOG.md`, `apps/api/CHANGELOG.md`, ewentualnie inne).

### Krok 5: Konflikty w i18n (en.json / de.json)

Pliki tłumaczeń to JSON — konflikt zwykle wynika z dodania kluczy w obu branchach. Strategia:

1. Otwórz plik, znajdź `<<<<<<<` i `>>>>>>>`.
2. **Zachowaj wszystkie klucze z obu stron** — to są zwykle różne klucze pod różnymi sekcjami.
3. Jeśli ten sam klucz ma różne wartości po obu stronach — **zatrzymaj się i zapytaj użytkownika** (`AskUserQuestion`), którą wartość zostawić. To prawdziwy konflikt biznesowy, którego nie powinieneś zgadywać.
4. Pilnuj poprawnego JSON-a (przecinki, brak trailing comma).

Po rozwiązaniu zweryfikuj parse'em:
```bash
python3 -c "import json; json.load(open('<plik>'))" && echo OK
```

### Krok 6: Inne konflikty

Dla każdego pliku poza CHANGELOG/i18n:

1. Przeczytaj plik z markerami konfliktu.
2. Oceń czy jesteś w 100% pewien jak rozwiązać:
   - **Trywialny przypadek** (np. dodany import w obu branchach pod tą samą sekcją, dodany element do listy bez kolizji semantycznej, niezależne zmiany w różnych funkcjach): rozwiąż samodzielnie zachowując oba zestawy zmian.
   - **Wątpliwy przypadek** (ten sam fragment kodu zmieniony różnie po obu stronach, zmiana sygnatury funkcji, refactor który koliduje z dodaniem nowej funkcjonalności): **użyj `AskUserQuestion`** — pokaż obie wersje i zapytaj którą zostawić lub jak je połączyć.
3. Po edycji upewnij się że nie zostały żadne markery konfliktu:
   ```bash
   grep -nE '^(<{7}|={7}|>{7})' <plik>
   ```

### Krok 7: Weryfikacja końcowa

Zanim zacommittujesz:

```bash
# Brak markerów konfliktu w żadnym pliku
git diff --check

# Wszystkie pliki rozwiązane (brak UU, AA, DD)
git status --porcelain | grep -E '^(UU|AA|DD|AU|UA|DU|UD)' && echo "STILL CONFLICTED" || echo "OK"
```

Jeśli `git diff --check` pokazuje markery — wróć do tych plików i dokończ.

### Krok 8: Commit merge'a

```bash
git add -A
git commit --no-edit
```

`--no-edit` użyje domyślnego komunikatu merge'a (`Merge remote-tracking branch 'origin/main' into <branch>`), który w tym repo jest spójny z istniejącymi merge commitami (sprawdź `git log --merges -3` jeśli nie jesteś pewien).

### Krok 9: Raport dla użytkownika

Po commitcie podsumuj zwięźle:
- Hash merge commita
- Lista plików gdzie były konflikty + jak rozwiązany każdy (1 zdanie na plik)
- Przypomnienie: **push robi użytkownik ręcznie** — nie pushuj sam.

Przykład:
> Merge `abc1234`. Konflikty rozwiązane:
> - `apps/panel/CHANGELOG.md` — Twój wpis bumpnięty z 0.1.73 → 0.1.74, nad wpisem z main.
> - `apps/panel/src/assets/i18n/en.json` — automerge kluczy.
>
> Push zostawiam Tobie.

## Reguły bezpieczeństwa

- **Nigdy nie rób `git merge --abort` bez pytania** — użytkownik mógł chcieć zachować częściową pracę.
- **Nigdy nie pushuj** — to zadanie użytkownika.
- **Nigdy nie używaj `--no-verify`** — jeśli pre-commit hook się wywali, zatrzymaj się i pokaż błąd użytkownikowi.
- **Soft fail przy niejasnościach** — w razie wątpliwości pytaj przez `AskUserQuestion` zamiast zgadywać. Lepiej zapytać raz za dużo niż zniszczyć cudzy wpis w changelogu.
- **Nie modyfikuj historii commitów** brancha — żadnego rebase, amend, reset.

## Edge cases

- **Brak konfliktu w CHANGELOG ale jest w innych plikach** — normalny merge, tylko Krok 6.
- **Konflikt CHANGELOG bez kolizji wersji** (oba branche dodały do różnych wersji) — po prostu zachowaj oba bloki w kolejności malejącej po wersji.
- **Wpis użytkownika rozsiany po kilku sekcjach (Added + Changed + i18n)** — bumpuj cały blok wersji jako całość, nie tylko jedną sekcję.
- **Trzy lub więcej wpisów pod tą samą wersją na main** (rzadkie, ale możliwe) — traktuj wszystkie wpisy z main jako "wpis z main" i połącz pod oryginalnym numerem; Twój wpis bumpuj wyżej.
- **Pre-commit hook fail przy commitcie merge'a** — pokaż błąd, zatrzymaj się. Nie commituj `--no-verify`. Użytkownik zdecyduje czy fixuje hook czy abortuje merge.
