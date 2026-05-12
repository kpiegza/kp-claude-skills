---
name: create-deployment-post
description: Generuje krotki wpis na kanal deployment w Teams na podstawie pull requesta (z aktualnego brancha lub podanego numeru PR). Format `[scope] krotki opis po polsku, co wdrazamy`. Automatycznie wykrywa scope (nazwa repo lub aplikacji w monorepo), tlumaczy tytul PR z angielskiego na polski i kopiuje wynik do schowka przez pbcopy. Skill **nigdy** nie publikuje samodzielnie — tylko generuje tekst, user wkleja do Teams recznie. Uzyj gdy uzytkownik mowi: "wpis na teams", "wpis deploymentowy", "tekst na teams", "wygeneruj wpis na deployment", "co wdrazam", "wpis na kanal deployment", "deployment message", "post na teams", "message na deployment kanal", "co napisac na teams".
allowed-tools: Bash(gh:*), Bash(git:*), Bash(pbcopy), Bash(echo:*), AskUserQuestion, Read
---

# Create Deployment Post

Generujesz **jedna linie** do wklejenia na kanal deployment w Teams. Format dominujacy w przykladach:

```
[scope] krotki opis po polsku, co wdrazamy
```

Skill **nigdy** sam nie pisze do Teams API. Generuje tekst, kopiuje do schowka, user wkleja recznie.

## Wykrywanie intencji z wiadomosci

Sprawdz co uzytkownik podal:
- **Numer PR**: wzorce `#1234`, `PR 1234`, `pull request 1234` -> uzyj jako input.
- **Nazwa brancha**: jesli explicit podana -> uzyj.
- **Brak wskazania**: aktualny branch (`git branch --show-current`).

## Krok 1: Pobranie PR

**Jezeli numer PR podany:**
```bash
gh pr view $PR_NUMBER --json title,body,headRefName,baseRefName,url,number,state
```

**Jezeli current branch:**
```bash
gh pr list --head "$(git branch --show-current)" --json number,title,body,headRefName,baseRefName,url,state --limit 1
```

Jezeli PR nie znaleziono:
- Zatrzymaj sie.
- Poinformuj uzytkownika ze nie ma otwartego ani zmergowanego PR z tego brancha.
- Zapytaj o numer PR przez `AskUserQuestion`.

## Krok 2: Wykrycie scope (zawartosc `[...]`)

Scope to nazwa repo lub aplikacji ktora wdrazasz. Sproboj w tej kolejnosci:

### Zrodlo A: monorepo — aplikacja na podstawie zmienianych plikow

Najpierw sprawdz czy to monorepo (RASP ma `adplatform`, `adplatform2`). Pobierz liste zmienionych plikow:

```bash
gh pr diff $PR_NUMBER --name-only | head -30
```

Mapowanie sciezek na scope (typowe dla RASP):

| Sciezka | Scope |
|---------|-------|
| `src/javascript/adp-api/` | `adp-api` |
| `src/javascript/adp-panel/` | `adp-panel` |
| `src/frontend/das-panel/` | `das-panel` |
| `src/golang/cmd/das-bidder/` | `das-bidder` |
| `src/javascript/adp-ad-template/` | `adp-ad-template` |
| `src/javascript/das-sese/` | `das-sese` |
| `src/javascript/oads-panel/` | `oads-panel` |
| `src/javascript/oads-core-api/` | `oads-core-api` |
| `src/javascript/ad-offer-provider/` | `ad-offer-provider` |
| `src/javascript/gdpr-popup/` | `gdpr-popup` |
| `projects/adp_rds/` | `adp-rds` |
| `projects/adp_activity/` | `adp-activity` |
| `projects/karuzela/` | `karuzela` |

Jezeli wiele aplikacji w jednym PR — wybierz **dominujaca** (najwiecej zmienionych plikow). Jezeli niejasne, zapytaj uzytkownika.

### Zrodlo B: nazwa repo

Jezeli nie monorepo lub nie pasuje mapowanie:

```bash
gh repo view --json name --jq .name
```

To bedzie scope (np. `crm-salesforce`, `unlayer-templates`, `adp-events-api`).

### Zrodlo C: fallback — zapytaj uzytkownika

Jezeli zadne ze zrodel nie da jasnego scope (rzadkie), pokaz uzytkownikowi liste plikow i zapytaj jaka aplikacja/repo to jest.

## Krok 3: Generowanie opisu po polsku

Opis = **jedna linijka, po polsku, max ~80 znakow**. W stylu istniejacych wpisow.

### Style observed w przykladach

| Wzorzec | Przyklad |
|---------|----------|
| Rzeczownik odczasownikowy | `Ujednolicenie opisu w szablonach sponsoringu` |
| Rzeczownik odczasownikowy | `Naprawa anonimizacji dla eventow typu request` |
| Czasownik 1. os. | `Wdrazam mozliwosc ustawienia completed na BIP przez mia` |
| Czasownik 1. os. | `Wdrazam poprawke do wysylania eventow do Piano na Lamodzie` |
| Konkret z metryka | `zmiana konfiguracji requests 1 vcpu -> 2 vcpu` |
| Krotka fraza | `Faktury z SF` |
| Krotka fraza | `Downscale RMQ` |

**Preferuj rzeczownik odczasownikowy** (`Dodanie X`, `Naprawa Y`, `Zmiana Z`, `Ujednolicenie W`) — najczestszy wzorzec. Czasownik 1. osoby (`Wdrazam X`) tez OK, ale uzywaj tylko gdy w PR body jest taki ton.

### Zrodla opisu

W kolejnosci pierwszenstwa:

1. **PR body — sekcja `## Task` lub `## Context`** — jezeli ma polski opis (rzadkie, bo skill `create-pull-request` wymusza angielski), uzyj.
2. **Jira ticket** — jezeli task ID jest w nazwie brancha (np. `feature/MONBACK-1234-...`), pobierz polski tytul:
```bash
# Sproboj przez gh (jezeli jest issue) — czasem zwraca nic
gh api "search/issues?q=MONBACK-1234" --jq '.items[0].title' 2>/dev/null

# Jezeli jest dostepny skill monetisation-core:jira-task — uzyj go zeby pobrac tytul po polsku.
# Inaczej: zapytaj uzytkownika o polski tytul.
```
3. **Tytul PR** (angielski) — przetlumacz na polski, skroc do esencji. Pamietaj: tytul `create-pull-request` ma format `feat(scope): description` — opis jest po `:` i jest po angielsku. Wez ten opis, przetlumacz.

### Reguly skracania

- Skroc rzeczownik scope w opisie (nie powtarzaj scope: `[adp-api] Dodanie nowego filtra`, nie `[adp-api] Dodanie nowego filtra w adp-api`).
- Trzymaj **konkret**: nazwy ficzerow, metryki, nazwy customer'ow gdy maja znaczenie ("dla Lamoda", "dla Onet").
- Unikaj jargonu z code review ("DRY", "refactor for testability") — to nie idzie na kanal deployment.

## Krok 4: Specjalne przypadki formatu

Wiekszosc wpisow ma prosty format `[scope] opis`. Niektore repo maja konwencje:

- **`das-sese`** — czesto z dodatkiem `- wdrazam -`: `[das-sese] - wdrazam - Campaign offsete`. Uzyj tego wzorca **tylko jezeli** scope to das-sese **i** opis jest naturalnym uzupelnieniem "wdrazam X" (czyli rzeczownik/krotka fraza). Inaczej standard.
- **`MIA`** — uppercase scope. Wez `[MIA]` jezeli scope wykryty to MIA.
- **Nested path** (rzadko): `[adp-ad-template/adt-ad_template_onet]` — uzyj jezeli widzisz PR ktory dotyka tylko jednego sub-template w adp-ad-template (sciezka `src/javascript/adp-ad-template/templates/adt-ad_template_onet/`).

Te wzorce sa **opcjonalne**. Default = `[scope] opis`.

## Krok 5: Pokazanie propozycji uzytkownikowi

Pokaz propozycje **dokladnie** jak ma wygladac na Teams:

```
Proponowany wpis:

[adp-api] Wdrazam filtrowanie CampaignSummaryFilterInput po subAccountIds

Akceptujesz?
```

Uzyj `AskUserQuestion`:
- **Tak, kopiuj do schowka** — wykonaj Krok 6.
- **Edytuj** — zapytaj o poprawiony tekst (jako single text input lub asked freeform), pokaz znowu (powrot do Kroku 5).
- **Anuluj** — koniec, nic nie kopiuj.

## Krok 6: Kopiowanie do schowka

```bash
printf '%s' "$FINAL_TEXT" | pbcopy
```

Uzyj `printf '%s'` zamiast `echo` zeby nie dolozyc newline'a na koncu (Teams nie potrzebuje).

Potwierdzenie po polsku:

> "Skopiowane do schowka. Wklej (Cmd+V) na kanal deployment Teams."

## Edge cases

- **Brak `gh` / niezalogowany** — zatrzymaj sie, ostrzez ze nie mozna pobrac PR z GitHub, zapytaj uzytkownika o tekst manualnie lub o numer PR + tytul.
- **PR nie istnieje (zly numer)** — pokaz blad, zapytaj o numer ponownie.
- **Brak `pbcopy` (nie macOS)** — pokaz finalny tekst w czacie z instrukcja "skopiuj recznie", nie probuj `xclip`/innych.
- **Monorepo z wieloma aplikacjami w PR** — zapytaj ktora aplikacja jest dominujaca dla wpisu. Albo wybierz po liczbie zmienionych plikow (najwiecej = dominujaca).
- **PR z draft state** — ostrzez ze PR jest draft (jeszcze nie do mergowania), zapytaj czy na pewno wpis na deployment.
- **PR z roznych repo (rzadko)** — niemozliwe, jeden PR = jedno repo. Zignoruj.

## Reguly

- **Krotko**: caly wpis razem z `[scope]` ma byc max ~100 znakow. Im krocej tym lepiej.
- **Po polsku**: opis zawsze po polsku, niezaleznie ze tytul PR i body sa po angielsku. **Tlumacz**.
- **Nie wymyslaj funkcjonalnosci**: jezeli nie wiesz co PR robi, zapytaj uzytkownika. Lepiej zapytac niz wygenerowac wpis ktory nie odpowiada zmianom.
- **Skill NIGDY nie publikuje samodzielnie do Teams** — tylko generuje tekst + kopiuje do schowka. Wklejenie robi user.
- **Nie modyfikuje PR**: zero `gh pr edit`, zero zmian w repo. Read-only operacja.
