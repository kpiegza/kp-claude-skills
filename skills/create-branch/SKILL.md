---
name: create-branch
description: Interaktywne tworzenie nowego brancha git z konwencja prefiksow (feature/bugfix/hotfix/refactor/chore) i opcjonalnym podpieciem taska Jira lub GitHub issue. Sanityzuje nazwy z polskich/niemieckich znakow diakrytycznych. Uzyj gdy uzytkownik mowi: "stworz branch", "nowy branch", "zrob mi branch", "utworz branch", "stworz feature branch", "branch dla MONBACK-X", "create branch", "nowy feature branch", "branch z prefiksem", "zacznij prace nad MONBACK-X". Takze gdy uzytkownik podaje prefix lub task ID bez kontekstu (np. "feature MONBACK-4336", "bugfix dla #123").
allowed-tools: Bash(git:*), Bash(gh:*), AskUserQuestion, Read
---

# Create Branch

Interaktywnie tworzysz nowego brancha git z czysta, ustrukturyzowana nazwa. Dziala w dowolnym repozytorium.

## Wykrywanie intencji z wiadomosci uzytkownika

Zanim zaczniesz krok 1, sprawdz co uzytkownik juz podal w swojej wiadomosci:

- **Prefix** (`feature`, `bugfix`, `hotfix`, `refactor`, `chore`) — jesli wymieniony, pomin krok 1
- **Task ID** (wzorzec typu `MONBACK-1234`, `JIRA-123`, `IDEALOQ226-32`, `#1234`) — jesli wymieniony, pomin pytanie "czy podpiac task" i przejdz od razu do lookupu
- **Wlasna nazwa** (np. "branch o nazwie xyz", "branch xyz") — jesli wymieniona, pomin pytanie "masz nazwe w glowie"

Pozostale kroki przeprowadz interaktywnie.

## Krok 1: Wybor prefiksu

Zapytaj jaki typ brancha. Uzyj `AskUserQuestion` z opcjami:

| Prefix | Kiedy uzyc |
|--------|-----------|
| `feature/` | Nowa funkcjonalnosc |
| `bugfix/` | Naprawa buga |
| `hotfix/` | Pilna poprawka produkcyjna |
| `refactor/` | Restrukturyzacja kodu bez zmiany zachowania |
| `chore/` | Tooling, deps, config, CI, sprzatanie |

## Krok 2: Podpiac task/ticket?

Zapytaj: **"Chcesz podpiac zadanie (np. Jira ticket) do nazwy brancha?"**

### Opcja A: Tak — podpinamy task

Zapytaj: **"Masz kod zadania (np. MONBACK-1234), czy mam wyszukac?"**

**Jesli uzytkownik podal task ID:**
1. Wyszukaj task uzywajac dostepnych narzedzi (skill Jira jesli jest, `gh issue view` dla GitHub issues, albo zapytaj o tytul)
2. Pokaz uzytkownikowi: task ID, tytul, krotkie podsumowanie
3. Zapytaj o potwierdzenie: "Uzywam tego do nazwy brancha?"

**Jesli uzytkownik chce szukac:**
1. Zapytaj czego szukac (slowo kluczowe, temat)
2. Uzyj dostepnych narzedzi do szukania (skill Jira, `gh issue list`, itp.)
3. Przedstaw wyniki jako numerowana liste, pozwol wybrac
4. Pokaz tytul + podsumowanie, poproc o potwierdzenie

**Po potwierdzeniu** wygeneruj nazwe brancha:
- Format: `prefix/TASK-ID-short-description`
- Krotki opis pochodzi z tytulu taska, sanityzowany (patrz Krok 4)

### Opcja B: Bez taska

Zapytaj: **"Masz nazwe w glowie, czy wygenerowac na podstawie zmian w repo?"**

**Jesli uzytkownik podal nazwe:**
- Sanityzuj (patrz Krok 4) i uzyj bezposrednio

**Jesli uzytkownik chce auto-generacji:**
1. Uruchom `git status` i `git diff --stat` zeby zobaczyc niezacommittowane zmiany
2. Jesli nic nie zmienione, uruchom `git log --oneline -5` zeby spojrzec na ostatnie commity
3. Zaproponuj krotka nazwe opisowa na podstawie tego co widzisz
4. Poproc o potwierdzenie

## Krok 3: Potwierdzenie i utworzenie

Pokaz finalna nazwe:

```
Branch: feature/MONBACK-1234-add-billing-export-page
```

Po potwierdzeniu uruchom `git checkout -b <branch-name>`.

Jesli branch juz istnieje, ostrzez uzytkownika i zapytaj co zrobic (przelaczyc sie na niego, wybrac inna nazwe, czy wymusic odtworzenie).

## Krok 4: Sanityzacja nazwy

Przy konwersji tytulu lub inputu uzytkownika na segment nazwy brancha:

1. Lowercase
2. Polskie znaki: `a->a, c->c, e->e, l->l, n->n, o->o, s->s, z->z, z->z`
3. Niemieckie znaki: `a->ae, o->oe, u->ue, ss->ss`
4. Spacje i underscore -> `-`
5. Usun wszystko poza `a-z`, `0-9`, `-`
6. Zwin wielokrotne `-` w jedno
7. Trim wiodacych/koncowych `-`
8. Max 50 znakow dla czesci opisowej (utnij na ostatnim `-` przed limitem)

Task ID (np. `MONBACK-4336`) zachowuje oryginalne wielkosci liter — tylko opis lowercase.

**Przyklady:**
- "Dodaj strone eksportu billingowego" -> `dodaj-strone-eksportu-billingowego`
- "Fix: login redirect  loop (urgent!)" -> `fix-login-redirect-loop-urgent`
- `MONBACK-4336` + "Panel eksportu danych uzytkownikow" -> `MONBACK-4336-panel-eksportu-danych-uzytkownikow`
