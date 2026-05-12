---
name: create-pull-request
description: Tworzy pull request dla aktualnego brancha przez `gh pr create` z ustrukturyzowanym opisem (Task / Context / Scope / Changes / Notes). Wyciaga task ID z nazwy brancha, weryfikuje CHANGELOG dla apps/panel i apps/api, wymusza commit i push przed utworzeniem PR. Tytul i opis po angielsku. Uzyj gdy uzytkownik mowi: "stworz PR", "nowy pull request", "zrob PR", "wystaw PR", "pusznij PR", "zrob mi PR", "create PR", "new pull request", "wystaw to do review", "open a pull request", "pusz na review". Takze gdy uzytkownik chce zglosic zmiany do review po commitcie.
allowed-tools: Bash(git:*), Bash(gh:*), AskUserQuestion, Read, Edit
---

# Create Pull Request

Tworzysz pull request dla aktualnego brancha z ustrukturyzowanym opisem.

## Wykrywanie intencji z wiadomosci uzytkownika

Sprawdz co uzytkownik juz podal:

- **Target branch** (np. "do develop", "do feature/xyz", "przeciwko main") — jesli podany, uzyj. W przeciwnym razie auto-detect `main`/`master`.
- **Sugestie tresci** (np. "z tytulem X", "zaznacz ze to breaking change") — wpisz do odpowiednich sekcji.

## Krok 1: Wyznaczenie base brancha

Uzyj `main` lub `master` (cokolwiek istnieje w repo), chyba ze uzytkownik wskazal inny target. Sprawdz przez:
```bash
git remote show origin | grep 'HEAD branch'
```

## Krok 2: Analiza zmian

Uruchom `git log` i `git diff` przeciwko base branchowi zeby zrozumiec **wszystkie** commity i zmiany ktore beda zawarte w PR. Spojrz na **kazdy** commit, nie tylko ostatni.

## Krok 3: Wyciagniecie task ID

Spojrz na nazwe brancha pod katem wzorca task ID (np. `MONBACK-4336`, `JIRA-123`, `IDEALOQ226-32`). Zostanie uzyty do linkowania taska.

## Krok 4: Weryfikacja CHANGELOG

Sprawdz czy pliki zmienione w branchu dotykaja `apps/panel/` lub `apps/api/`. Dla kazdej z tych aplikacji zweryfikuj, ze jej `CHANGELOG.md` zostal zaktualizowany w branchu:
```bash
git diff origin/main..HEAD -- apps/panel/CHANGELOG.md
git diff origin/main..HEAD -- apps/api/CHANGELOG.md
```

Jesli brakuje wpisu, uruchom `/changelog` przed kontynuacja. Sprawdz tez, ze zmiany w CHANGELOG sa zacommittowane i wypchniete — jesli nie, najpierw commit i push.

## Krok 5: Commit i push

- Jesli sa niezacommittowane zmiany, zapytaj uzytkownika czy chce zacommittowac przed utworzeniem PR.
- Wypchnij brancha jesli nie jest up to date z remote.

## Krok 6: Utworzenie PR

Uzyj `gh pr create` ze struktura ponizej.

## Format tytulu PR

Krotki, opisowy, **po angielsku**. Max 70 znakow. Wlacz scope w nawiasach jesli jasny:

```
feat(panel): billing usage export page
fix(api): correct date range calculation
refactor(permission): extract isGlobalRole utility
```

## Struktura opisu PR

Uzyj dokladnie tej struktury (HEREDOC dla `gh pr create --body`):

```markdown
## Task
[TICKET-ID](https://link-to-ticket) — one-line description of the task/story

## Context
1-3 sentences explaining WHY this change is needed. What problem does it solve? What was broken or missing? This gives the reviewer the mental model before they look at the diff.

## Scope
Which parts of the codebase are affected. Examples:
- `apps/panel` — campaign creator styles
- `apps/api` + `packages/permission` — new RBAC method
- `prisma` + `apps/api` — schema migration + resolver

## Changes
- **Most important change** — what + why if non-obvious
  - Technical detail: file, component, method
  - Another detail if needed
- **Second change** — description
  - Sub-detail
- **Third change** — description

## Notes
_Optional section. Include only if there are:_
- Breaking changes or migration steps
- Dependencies on other PRs (link them)
- Deployment considerations
- Things reviewer should pay special attention to

_Remove this section entirely if empty._
```

## Reguly

- **BEZ sekcji test plan** — nigdy nie wlaczaj test cases ani QA checklist
- **BEZ podpisu/stopki** — zadnych "Generated with..." ani co-authored lines w opisie PR
- **Jezyk**: tytul i opis PR zawsze po angielsku
- **Link do ticketu**: Skonstruuj URL z task ID. Znane Jira bases: `MONBACK-*`, `DEIDEALO*`, `MONETINC-*`, `MONETEAINC-*` -> `https://jira.ringieraxelspringer.pl/browse/{ID}`. Dla nieznanych prefiksow, zapytaj uzytkownika o base URL. Jesli nie mozesz zbudowac linka, wstaw ID jako plain text.
- **Sekcja Context**: zawsze wlacz — nawet dla malych fixow. Reviewer musi zrozumiec problem przed rozwiazaniem. Nie powtarzaj listy zmian tutaj, skup sie na "why".
- **Sekcja Scope**: wymien dotyczone obszary jako krotkie sciezki z myslnikiem opisu. Pozwala reviewerom szybko zobaczyc blast radius.
- **Sekcja Changes**: posortuj po waznosci, nie chronologicznie. Zacznij od user-facing lub architektonicznych zmian, detale implementacyjne na koncu. Uzyj bold dla glownego punktu, sub-bullets dla technicznych detali (pliki, komponenty, metody).
- **Badz specyficzny**: "Add subAccountIds filter to CampaignSummaryFilterInput" zamiast "Update filters"
