---
name: code-review
description: Code review pull requesta w odniesieniu do zadania z Jiry (czy PR robi to, czego wymagal task, czy zalozenia wytrzymuja awarie, czego brakuje poza diffem), z wynikiem jako jedno podsumowanie z checkboxami zamiast komentarzy inline. Dziala na cudzych PR-ach (review, re-review, approve) i na wlasnych przed oddaniem do review. Uzyj gdy uzytkownik mowi: "zrob code review", "przejrzyj PR", "zreviewuj PR", "code review #1234", "review PR 1234", "re-review", "sprawdz poprawki w PR", "self-review", "przejrzyj moj PR przed review", "czy PR spelnia taska", "code review tego brancha", "skomentuj PR".
allowed-tools: Bash(git:*), Bash(gh:*), Bash(python3:*), Bash(mkdir:*), AskUserQuestion, Read, Grep, Glob, Edit, Write, Agent, SendMessage
---

# Code Review

Review PR-a jak wlasciciel domeny: najpierw co zadanie mialo osiagnac (Jira: task, story, ustalenia w komentarzach, sasiednie subtaski), potem co padnie po commicie, poza diffem i w obietnicach z opisu. Znaleziska przechodza przez petle sedziego, ktory wymaga dowodow, a nie argumentow. Wynik to jedno podsumowanie z checkboxami.

Z uzytkownikiem rozmawiasz po polsku. Review na GitHub piszesz po angielsku, chyba ze uzytkownik poprosi inaczej.

## Role i modele

| Rola | Model | Ile | Zadanie |
|---|---|---|---|
| Orkiestrator (ty) | — | — | dossier, skrypty, pytania do usera, draft, wysylka |
| Analityk, potem sedzia | `fable` | 1 agent, wznawiany przez `SendMessage` | kontrakt zadania, werdykty |
| Recenzenci | `sonnet` | 3 (maly PR: 1) | znaleziska z dowodami, odpowiedzi na wyzwania |
| Weryfikator re-review | `sonnet` | 1 | status poprzednich punktow + nowe commity |

Prompty: `references/agent-prompts.md`. Format wyniku: `references/review-format.md`. Skrypty sa w `scripts/` w katalogu bazowym tego skilla (podanym przy jego zaladowaniu) — dalej `$SKILL_DIR`.

Oszczednosc tokenow: agentom podajesz sciezki do plikow dossier, nigdy ich tresc. Sedzia to ten sam agent co analityk, a w rundzie wyzwan wznawiasz tych samych recenzentow, wiec w kolejnych rundach nikt nie czyta diffa od nowa. Najwyzej dwie rundy.

Agenci moga dzialac w tle. Kolejna faze zaczynasz dopiero, gdy przyjda powiadomienia o zakonczeniu wszystkich agentow poprzedniej fazy.

## Krok 1: PR, tryb i dossier

1. PR z wiadomosci (numer, URL) albo z aktualnego brancha. Bez PR — powiedz to i zakoncz, nie zgaduj.
   ```bash
   gh pr view {pr} --json number,title,url,author,body,headRefName,headRefOid,baseRefName,state
   gh repo view --json nameWithOwner --jq .nameWithOwner
   gh api user --jq .login
   ```
   Musisz byc w lokalnym klonie tego repo (skrypty czytaja historie git). Jesli nie jestes, zapytaj o sciezke.
2. Tryb:
   - autor PR == zalogowany user -> **self** (self-review przed oddaniem),
   - inaczej -> **reviewer**. Sprawdz moje poprzednie komentarze i review na tym PR:
     ```bash
     gh api repos/{owner}/{repo}/issues/{pr}/comments --paginate --jq '[.[] | select(.user.login=="{me}") | {id, created_at, body}]'
     gh api repos/{owner}/{repo}/pulls/{pr}/reviews --paginate --jq '[.[] | select(.user.login=="{me}") | {id, submitted_at, state, body}]'
     ```
     Gdy ktorys zawiera `- [ ]` albo `- [x]`, zapytaj `AskUserQuestion`: **Re-review** czy **Pelne review od nowa**. Re-review: dokoncz punkty 3-4 tego kroku i przejdz do Kroku 7.
3. Dossier, ref i worktree z head PR (working tree usera zostaje nietkniety). Ustal sciezke `{D}` = `<$TMPDIR albo /tmp, bez koncowego />/kp-code-review/{repo}-{pr}-{sha7}` i wpisuj ja doslownie w kolejnych komendach:
   ```bash
   mkdir -p "{D}"
   git fetch -q origin {base} "pull/{pr}/head:refs/kp-review/{pr}"
   git worktree add -q --detach "{D}/wt" "refs/kp-review/{pr}"
   git diff "origin/{base}...refs/kp-review/{pr}" > "{D}/diff.patch"
   python3 "$SKILL_DIR/scripts/context_pack.py" --base "origin/{base}" --head "refs/kp-review/{pr}" --out "{D}/context-pack.md"
   ```
   Agentom jako `{repo_path}` podajesz `{D}/wt`: tam Read, Grep i git widza dokladnie head PR, a nie branch, ktory user ma wyciagniety. Gdy `{D}/wt` juz istnieje (ponowne uruchomienie dla tego samego commita), uzyj go zamiast `worktree add`.
   Do `{D}/pr.md` zapisz tytul, autora, branch i opis PR. Opis zapisz tez osobno do `{D}/body.md`.
4. Kontekst zadania:
   ```bash
   python3 "$SKILL_DIR/scripts/task_context.py" --branch "{headRefName}" --title "{title}" --body-file "{D}/body.md" --out "{D}/task.md"
   ```
   | exit | Co robisz |
   |---|---|
   | 0 | dalej |
   | 3 (Jira nie odpowiada, zwykle brak VPN) | `AskUserQuestion`: Sprobuj ponownie / Wkleje tresc taska (zapisz do `{D}/task.md`) / Kontynuuj bez Jiry |
   | 4 (brak klucza taska) | zapytaj o klucz (`--key`) albo kontynuuj bez Jiry |
   | 2 (brak `jira.py`) | kontynuuj bez Jiry, wspomnij o zmiennej `KP_JIRA_SCRIPT` |

   Bez Jiry kontraktem jest opis PR. Napisz to userowi i dodaj zdanie w review ("Reviewed against the PR description; the task was not available").
5. Rozmiar: maly PR (do 150 zmienionych linii poza testami i do 5 plikow) dostaje jednego recenzenta R0.
6. Jedna linia dla usera: `PR #{pr} · tryb {self|reviewer} · task {KEY albo "bez Jiry"} · {N} plikow`.

## Krok 2: Analityk zadania i R2

W jednej wiadomosci spawn:
- analityka: `model: fable`, prompt ANALITYK. Zapamietaj jego id jako `judge`.
- R2 (Poza diffem): `model: sonnet`, prompt RECENZENT. R2 nie potrzebuje kontraktu, zaczyna od `context-pack.md`.

Maly PR: tylko analityk (R0 potrzebuje kontraktu, startuje w Kroku 3).

Gdy analityk skonczy, pokaz userowi 3-5 linii z jego podsumowania (cel, kwestionowane AC, rozjazdy, napiecia) i lec dalej bez pytania.

## Krok 3: Recenzenci R1 i R3

Gdy jest `contract.md`, spawn w jednej wiadomosci R1 i R3 (albo samego R0): `model: sonnet`, prompt RECENZENT z soczewka z tabeli. Zapamietaj ich id. Kazdy recenzent zapisuje `{D}/findings-{id}.json`.

Specjalistow z repo (`.claude/agents/*.md`) dodajesz tylko na prosbe usera, z tym samym schematem findings. Repo-skille z `disable-model-invocation: true` mozna im dac najwyzej jako checkliste do przeczytania.

## Krok 4: Petla sedziego

1. `SendMessage` do `judge` z promptem SEDZIA runda 1. Sedzia zapisuje `{D}/verdicts.json` i `{D}/decisions.md`.
2. Gdy sa werdykty CHALLENGE: kazdemu recenzentowi, ktory je dostal, wyslij `SendMessage` z promptem WYZWANIE (tylko jego pytania). Potem `SendMessage` do `judge` z promptem SEDZIA runda 2.
3. Po rundzie 2 nie ma kolejnych wyzwan. Nierozstrzygniete punkty sedzia zamyka werdyktem.
4. Pokaz userowi jedna linie: `Sedzia: X do poprawy w PR, Y follow-up, Z nice-to-have, W odrzuconych (glowne powody)`.

## Krok 5: Napiecia i decyzje

Dla kazdego napiecia z `needs_user_decision` (najwyzej 2) zadaj `AskUserQuestion`: opcja A / opcja B / Zostaw jako otwarte pytanie. Opisy opcji wez z `contract.md` (kto placi w ktorym komponencie). Mandat do decyzji ma user, nie agent.

Po wyborze opcji wyslij `SendMessage` do `judge` z promptem DECYZJA. Sedzia zapisuje `{D}/decision-{T}.md`: Decision, Why, checkboxy dla tego PR, punkty dla komponentu z sasiedniego subtaska i zmiany werdyktow, ktore wynikaja z decyzji (np. logika zbedna po decyzji staje sie checkboxem "Remove ...", a nie nice-to-have). Pierwsza sekcja review powstaje z tego pliku. Napiecie zostawione jako otwarte idzie do "Not covered" jako "Open question".

## Krok 6: Draft i wynik

Zbuduj review z `verdicts.json` wedlug `references/review-format.md`. Kazdy punkt ma plik i dowod ze znaleziska. Punkty DROP pomijasz.

**Tryb reviewer**
1. Zapisz `{D}/review.md` i pokaz go userowi w calosci.
2. `AskUserQuestion`: **Wyslij** / **Przeredaguj** / **Zostaw lokalnie**.
3. Przeredaguj to petla: po kazdej zmianie pokazujesz pelna nowa wersje i pytasz ponownie. Skracasz bez zmiany merytoryki, zmieniasz ton bez zmiany faktow. Przy niejasnej prosbie pokazujesz warianty A i B. "ok" albo "dobra" to nie jest "Wyslij".
4. Wysylka tylko po wyborze **Wyslij**: `gh pr comment {pr} --body-file "{D}/review.md"`.
5. Po wysylce, gdy sa FOLLOW-UP do nowego taska, NOT-COVERED z mitygacja typu task albo JIRA: zaproponuj kazdy osobno i wykonaj tylko po zgodzie. `jira-create.py` i `jira-update.py` leza obok `jira.py` (sciezka z `task_context.py`):
   - nowy subtask: `python3 <dir>/jira-create.py "<title>" --parent <PARENT> --description "<...>" --ac "<...>" --markdown`,
   - rozjazd z AC: komentarz `python3 <dir>/jira-update.py <KEY> --comment "<...>"`. AC zmieniasz tylko na wyrazna prosbe.

**Tryb self**
1. Pokaz liste w czacie po polsku (format self).
2. Dla kazdego checkboxa `AskUserQuestion`: **Napraw lokalnie** / **Pomin** / **Dopisz jako znane ryzyko do Notes w opisie PR**.
   - Napraw: pokaz proponowana zmiane, zastosuj przez `Edit`, nie commituj.
   - Notes: pokaz nowy opis PR, po zgodzie `gh pr edit {pr} --body-file <plik>`.
3. Rozjazdy z Jira: zaproponuj poprawke opisu PR albo komentarz w Jirze, tylko po zgodzie.

## Krok 7: Re-review (tryb reviewer)

1. Do `{D}/prior-review.md` zapisz moje komentarze i review z checkboxami (z datami). Ostatnia data to `T`.
2. `reviewed_sha` to ostatni commit PR z `committedDate <= T`:
   ```bash
   gh pr view {pr} --json commits --jq '[.commits[] | select(.committedDate <= "T")] | last | .oid // empty'
   ```
   - Pusty wynik albo `git cat-file -e {reviewed_sha}` konczy sie bledem (rebase, force-push): przyrostu nie da sie policzyc. Weryfikator dostaje `{D}/diff.patch` calego PR, a review zaczyna sie od zdania "The branch was rebased, so this re-review covers the whole PR".
   - Inaczej przyrost tylko w plikach PR (bez commitow zmergowanych z maina):
     ```bash
     gh pr view {pr} --json files --jq '.files[].path' > "{D}/pr-files.txt"
     git diff "{reviewed_sha}" "refs/kp-review/{pr}" -- $(cat "{D}/pr-files.txt") > "{D}/changes-since-review.patch"
     ```
   Komentarze innych osob po `T` zapisz do `{D}/replies.md`.
3. Spawn weryfikatora: `model: sonnet`, prompt WERYFIKATOR.
4. Nowe znaleziska oceniasz sam rubryka sedziego, bez Fable. Gdy co najmniej 3 nowe znaleziska maja confidence ponizej 90, uruchom sedziego: nowy agent `fable` z promptem SEDZIA runda 1, kontraktem jest `{D}/prior-review.md`, a zmiany, o ktore prosilo poprzednie review, nie sa DODATKOWE.
5. Draft w formacie re-review, potem ta sama petla co w Kroku 6.
6. Gdy wszystko ADDRESSED albo ANSWERED i brak nowych punktow: `AskUserQuestion` **Approve z LGTM** / **Tylko komentarz** / **Nic**. Approve: `gh pr review {pr} --approve --body "<body>"`.
7. Opcjonalnie, po zgodzie: odhacz zalatwione punkty w moim poprzednim komentarzu (`gh api -X PATCH repos/{owner}/{repo}/issues/comments/{id} -F body=@<plik>`).

## Krok 8: Podsumowanie i sprzatanie

```bash
git worktree remove --force "{D}/wt"
git update-ref -d "refs/kp-review/{pr}"
```

Pokaz: tryb, czy Jira byla dostepna, liczby (checkboxy / follow-up / nice-to-have / odrzucone), co wyslano (link do PR, utworzone taski), sciezke dossier. Koszt agentow user sprawdzi przez `/usage`.

## Zasady

1. Na GitHub i do Jiry idzie tylko to, co user wybral (Wyslij / Approve / Utworz task). Bez stopek "Generated with Claude".
2. Bez dowodu nie ma punktu: plik, mechanizm, skutek, poprawka.
3. Kontrakt nie jest wyrocznia. AC moze byc bledne. Rozjazd PR z AC to albo blad PR, albo zmiana zalozen do odnotowania w Jirze — rozstrzyga sedzia.
4. Rzeczy z sasiedniego subtaska to follow-up z jego kluczem, nie checkbox.
5. Problemy sprzed PR, ktorych PR nie pogarsza, nie sa checkboxami.
6. Styl, formatowanie i struktura katalogow nie sa tematem tego review.

## Typowe bledy

| Blad | Jak tego uniknac |
|---|---|
| Review jest parafraza opisu PR | Analityk wypisuje twierdzenia do obalenia, a R3 je sprawdza |
| "Pewnie gdzies to jest wolane" bez grepa | Sedzia daje CHALLENGE, bez nowego dowodu punkt odpada |
| Sedzia zmienia zdanie miedzy rundami | Dziennik decyzji z `purpose`; inny cel = osobna decyzja |
| 10 punktow przy linijkach, jak z lintera | 3-5 checkboxow na runde, laczenie po mechanizmie, jeden komentarz |
| Sedzia startuje, zanim skoncza recenzenci | Czekaj na powiadomienia wszystkich agentow fazy |
| Agent "rozstrzyga" decyzje projektowa | Napiecie idzie do usera (Krok 5) |
