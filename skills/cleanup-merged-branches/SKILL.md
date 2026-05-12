---
name: cleanup-merged-branches
description: Bezpieczne usuwanie lokalnych branchy ktore zostaly zmergowane do main/master — z podwojna weryfikacja (git + GitHub PR), ochrona chronionych nazw (main, master, develop, staging, production, release/*, hotfix/*) i obsluga squash merge edge case. Domyslnie tyka tylko lokalnych branchy, nigdy nie uzywa force delete bez explicit potwierdzenia. Uzyj gdy uzytkownik mowi: "wyczysc branche", "usun zmergowane branche", "porzadki w branchach", "cleanup branchy", "ile mam zbednych branchow", "co moge usunac", "delete merged branches", "remove old branches", "branch cleanup", "prune branches", "posprzataj branche", "skasuj branche". Takze gdy uzytkownik chce ogarnac lokalna liste branchy po wielu zmergowanych PRach.
allowed-tools: Bash(git:*), Bash(gh:*), AskUserQuestion, Read
---

# Cleanup Merged Branches

Usuwasz lokalne branche, ktore juz zostaly zmergowane — bezpiecznie, z podwojna weryfikacja i wieloma checkpoint'ami. Cel: nie zostawic zbednych branchy, ale **nigdy** nie zniszczyc pracy uzytkownika.

## Zasady bezpieczenstwa (czytaj zawsze przed dzialaniem)

1. **Tylko `git branch -d`** (safe delete) — nigdy `git branch -D` (force) bez explicit potwierdzenia uzytkownika dla konkretnego brancha.
2. **Chronione nazwy nigdy nie sa kandydatami** — `main`, `master`, `develop`, `staging`, `production`, `release/*`, `hotfix/*`, `prod/*`.
3. **Current branch nigdy nie jest kandydatem** — odfiltruj go z listy zanim cokolwiek pokazesz.
4. **Domyslnie tylko lokalne branche** — usuwanie remote (`git push origin --delete`) wymaga osobnego, eksplicytnego "tak".
5. **Per-branch confirmation** — uzytkownik zatwierdza kazdy branch z osobna lub wszystkie razem przez `AskUserQuestion`, nigdy jednym "tak" w czacie.
6. **Stop on error** — jesli `-d` odmowi (branch niezmergowany), zatrzymaj sie i pokaz dlaczego. Nigdy nie eskaluj automatycznie do `-D`.

## Krok 1: Sanity check stanu repo

```bash
git rev-parse --is-inside-work-tree
git status --porcelain
git branch --show-current
```

Jesli to nie jest git repo — przerwij. Jesli sa niezacommittowane zmiany — ostrzez uzytkownika ale **kontynuuj** (usuwanie branchy nie tyka working tree, ale lepiej zeby user mial swiadomosc).

Zapamietaj current branch — to filtr ktorego uzyjesz w kroku 3.

## Krok 2: Wyznaczenie base brancha

```bash
git remote show origin 2>/dev/null | grep 'HEAD branch' | sed 's/.*: //'
```

Jesli polecenie zwroci `main` lub `master` — uzyj tego. Jesli nie ma origin lub remote nie odpowiada, fallback:

```bash
git branch -l main master | head -1 | tr -d ' *'
```

Zapamietaj base brancha — to przeciwko niemu sprawdzasz zmergowanie.

## Krok 3: Lista wszystkich lokalnych branchy

```bash
git for-each-ref --format='%(refname:short)|%(committerdate:short)|%(upstream:short)' refs/heads/
```

Dostaniesz format: `branch-name|2026-04-15|origin/branch-name`.

## Krok 4: Filtrowanie chronionych i current

Z listy z kroku 3 wykluczy:
- **Current branch** (z kroku 1)
- **Base branch** (z kroku 2)
- **Chronione nazwy** — pasujace do regex: `^(main|master|develop|staging|production|prod|dev)$` lub zaczynajace sie od `release/`, `hotfix/`, `prod/`

Co zostalo = **kandydaci do dalszej analizy**.

## Krok 5: Sprawdzenie zmergowania (podwojny check)

To jest **kluczowa** czesc skilla. Squash merge na GitHubie nie zostawia ancestor relationship, wiec `git branch --merged` go nie wylapie.

### Check A: ancestor check (lokalny)

```bash
git branch --merged "$BASE_BRANCH" | grep -v '^\*' | sed 's/^[ ]*//'
```

Branche w tej liscie = "zmergowane wedlug git" (zwykly merge lub fast-forward).

### Check B: GitHub PR check

Dla **kazdego** kandydata z kroku 4:

```bash
gh pr list --state merged --head "$BRANCH_NAME" --json number,mergedAt,title --limit 1
```

Jesli zwroci niepustą tablice — byl zmergowany PR z tego brancha (lapie squash + rebase merge).

### Klasyfikacja

Dla kazdego kandydata oznacz:
- **`merged-via-git`**: tak/nie (Check A)
- **`merged-via-pr`**: tak/nie (Check B) + numer PR, data merge'a
- **`last-commit-date`**: z kroku 3

**Kandydat do usuniecia** = `merged-via-git` LUB `merged-via-pr`.

**Jezeli zaden z checkow nie potwierdza zmergowania** — branch zostaje pominiety w prezentacji. Mozesz wymienic go osobno jako "branche bez sladu zmergowania" zeby uzytkownik wiedzial, ale **nie traktuj jako kandydata**.

## Krok 6: Prezentacja kandydatow

Pokaz tabele po polsku:

```
Znalazlem N branchy do usuniecia:

| Branch                            | Ostatni commit | Status            |
|-----------------------------------|----------------|-------------------|
| feature/MONBACK-1234-add-export   | 2026-03-15     | PR #4521 merged   |
| bugfix/fix-login-redirect         | 2026-02-28     | merged into main  |
| chore/bump-deps                   | 2026-01-10     | PR #4489 merged   |

Branche ktore nie sa zmergowane (pomijam): ...
Branche chronione (pomijam): ...
```

## Krok 7: Wybor co usunac

Uzyj `AskUserQuestion` z multiSelect (jezeli kandydatow > 1) lub single (jezeli 1).

Opcje:
- **Usun wszystkie** — wykonaj `git branch -d` dla kazdego po kolei
- **Wybierz pojedynczo** — pokaz kolejne `AskUserQuestion` per branch
- **Anuluj** — nie usuwaj nic

Jezeli kandydatow > 5, **domyslnie sugeruj "Wybierz pojedynczo"** — masowe usuwanie wielu branchy zwieksza ryzyko, ze user nie zauwazy ze cos jest na liscie.

## Krok 8: Usuwanie

Dla kazdego zatwierdzonego brancha:

```bash
git branch -d "$BRANCH_NAME"
```

**Jezeli `-d` odmowi** (np. komunikat "branch is not fully merged"):

1. Zatrzymaj usuwanie tego brancha.
2. Pokaz uzytkownikowi pelny output bledu.
3. Wyjasnij: "Git odmowil bezpiecznego usuniecia. Branch ma commity ktorych nie ma na `<base>`. Moze to byc:
   - Squash merge na GitHubie (sprawdzone w kroku 5, ale moglo cos sie nie zgadzac)
   - Niewypchniete commity ktore zaginely
   - Branch jeszcze nie jest zmergowany"
4. Zapytaj przez `AskUserQuestion`:
   - **"Pomin ten branch"** — kontynuuj z reszta
   - **"Sprawdz commity ktore znikna"** — pokaz `git log <base>..<branch>` zeby user zobaczyl co zostanie utracone, potem pytaj jeszcze raz
   - **"Wymus usuniecie (`git branch -D`)"** — ostatecznosc, tylko po pokazaniu commitow

**Nigdy nie eskaluj automatycznie do `-D`.** To musi byc swiadoma decyzja uzytkownika dla konkretnego brancha.

## Krok 9: Usuwanie odpowiednikow ze zdalnego repo (opcjonalnie)

Po usunieciu **lokalnych** branchy zapytaj uzytkownika, czy chce tez usunac ich odpowiedniki ze zdalnego repo (`origin`). To **destruktywna i widoczna dla innych operacja** — wymaga swiadomej decyzji.

### Krok 9.1: Sprawdz ktore zdalne odpowiedniki jeszcze istnieja

Dla **kazdego** brancha ktory wlasnie zostal lokalnie usuniety, sprawdz czy istnieje na origin:

```bash
git ls-remote --heads origin "$BRANCH_NAME"
```

Jesli output pusty — branch juz nie istnieje na zdalnym (np. ktos inny go usunal lub GitHub auto-usunal po merge). Pomin w prezentacji.

Jesli output niepusty — branch dalej jest na origin, kandydat do usuniecia zdalnego.

### Krok 9.2: Zapytaj uzytkownika

Pokaz liste kandydatow do usuniecia zdalnego i zapytaj przez `AskUserQuestion`:

```
Te branche zostaly usuniete lokalnie i nadal istnieja na origin:
- feature/MONBACK-1234-add-export
- bugfix/fix-login-redirect

Czy usunac je tez ze zdalnego repo?
```

Opcje:
- **Tak, wszystkie** — usuniecie wszystkich zdalnych odpowiednikow
- **Wybierz pojedynczo** — per-branch confirmation
- **Nie** — zostaw zdalne nienaruszone

### Krok 9.3: Usuwanie zdalnego

Dla kazdego zatwierdzonego brancha:

```bash
git push origin --delete "$BRANCH_NAME"
```

**Obsluga bledow:**

- **`remote ref does not exist`** — branch juz nie istnieje na origin, traktuj jako sukces (cel osiagniety).
- **`protected branch`** — branch ma protection rules na GitHubie. Zatrzymaj sie dla tego brancha, pokaz blad, kontynuuj z reszta. Nie probuj bypassowac protection.
- **`403 / permission denied`** — uzytkownik nie ma push prawa. Zatrzymaj caly krok 9, pokaz blad, przejdz do kroku 10.
- **Network error** — pokaz blad, zapytaj czy ponowic czy pominac.

**Nigdy nie uzywaj `--force`** przy `git push origin --delete` — operacja delete sama w sobie nie wymaga force, force only zmieni semantyke na "wymus mimo niezgodnosci".

## Krok 10: Czyszczenie stale remote tracking refs (opcjonalnie)

Po ewentualnym kroku 9 zapytaj:

> "Czy chcesz tez wyczyscic stale remote tracking refs (`git remote prune origin`)? To usunie lokalne wskazania na `origin/<branch>` ktore juz nie istnieja na zdalnym."

Jesli tak:

```bash
git remote prune origin
```

To jest **bezpieczna** operacja — usuwa tylko lokalne refs, nie tyka commitow ani zdalnego repo.

## Krok 11: Raport koncowy

Pokaz krotkie podsumowanie po polsku:

```
### Wyczyszczono branchy

Lokalnie usuniete (N):
- feature/MONBACK-1234-add-export
- bugfix/fix-login-redirect

Zdalnie usuniete na origin (M):
- feature/MONBACK-1234-add-export
- bugfix/fix-login-redirect

Pominiete na zyczenie (K):
- chore/bump-deps (zostawione lokalnie i na origin)

Bledy / wymagaja uwagi (L):
- feature/incomplete-work — nie zmergowany, decyzja: pominieto
- feature/protected — protected branch na GitHubie, nie usunieto zdalnie

Stale remote refs: prune'd / pominieto.
```

## Edge cases

- **Brak kandydatow** — poinformuj uzytkownika i zakoncz (nie pytaj o nic).
- **User jest na branchu ktory chcialby usunac** — wykryj to w kroku 1, poinformuj: "Jestes obecnie na `feature/xyz`. Najpierw przelacz sie na `main`: `git checkout main`, potem mozemy wrocic."
- **Brak remote (`origin` nie ustawione)** — pomin Check B (GitHub), uzyj tylko Check A (lokalny ancestor). Poinformuj uzytkownika ze sprawdzasz tylko lokalnie.
- **`gh` nie zainstalowane / niezalogowane** — pomin Check B, uzyj tylko Check A. Ostrzez ze squash-merged branche moga zostac pominiete.
- **Branch sciezki ze slashem (`feature/foo/bar`)** — traktuj jak zwykla nazwe, `-d` ogarnia.
- **Stary branch (> 6 miesiecy) ale niezmergowany** — **nie** usuwaj. Wymien w sekcji "branche bez sladu zmergowania" w prezentacji, niech uzytkownik sam zdecyduje.

## Czego skill NIGDY nie robi

- Nie usuwa zdalnych branchy bez **osobnego, explicit potwierdzenia** w kroku 9 — automatyczne usuwanie zdalnych po lokalnych jest zabronione.
- Nie uzywa `git branch -D` bez explicit potwierdzenia per branch + pokazania commitow ktore zostana utracone.
- Nie uzywa `git push --force` w kroku 9 (delete operation nie wymaga force, force only zmieni semantyke).
- Nie omija branch protection rules na GitHubie — jesli `git push origin --delete` zwroci `protected branch`, skill kapituluje dla tego brancha.
- Nie usuwa current brancha (git odmowi i tak, ale skill nawet go nie pokazuje).
- Nie usuwa chronionych nazw (`main`, `master`, etc.) niezaleznie od tego co user mowi — ani lokalnie, ani zdalnie.
- Nie modyfikuje `.git/config`, nie zmienia remote'ow, nie tyka tag-ow.
- Nie pusha **niczego innego** do remote (zadnych commitow, tagow, pull requestow) — krok 9 to wylacznie `git push origin --delete`.
