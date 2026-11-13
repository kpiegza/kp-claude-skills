---
name: code-review
description: Uzyj gdy uzytkownik chce code review pull requesta - cudzego (review, re-review, approve) albo wlasnego przed oddaniem do review - albo pyta, czy PR spelnia zadanie z Jiry. Frazy: "zrob code review", "przejrzyj PR", "zreviewuj PR", "code review #1234", "review PR 1234", "re-review", "sprawdz poprawki w PR", "self-review", "przejrzyj moj PR przed review", "czy PR spelnia taska", "code review tego brancha", "skomentuj PR", "glebokie review".
allowed-tools: Bash(git:*), Bash(gh:*), Bash(python3:*), Bash(mkdir:*), AskUserQuestion, Read, Grep, Glob, Edit, Write, Agent
---

# Code Review

Review PR-a jak wlasciciel domeny: co zadanie mialo osiagnac (Jira: task, story z ustaleniami w komentarzach, sasiednie subtaski) i co padnie po commicie, poza diffem albo wbrew obietnicom z opisu. Wynik to jedno podsumowanie z checkboxami.

**Przebieg ma staly ksztalt: dossier -> kontrakt -> jedna fala recenzentow -> jeden triage -> draft.** Kazdy agent dostaje jeden prompt i oddaje jeden plik. Punkt przechodzi dalej, gdy ma dowod sprawdzony narzedziem.

Z uzytkownikiem rozmawiasz po polsku. Review na GitHub piszesz po angielsku, chyba ze uzytkownik poprosi inaczej.

Prompty i szablon kontraktu: `references/agent-prompts.md`. Format wyniku: `references/review-format.md`. Skrypty: `scripts/` w katalogu bazowym skilla (podanym przy zaladowaniu), dalej `$SKILL_DIR`.

## Kto szuka problemow

| PR | Recenzenci | Model |
|---|---|---|
| maly: do 150 zmienionych linii poza testami i do 5 plikow | ty sam, pytania A+B+C | — |
| pozostale | R1 (A+C) i R2 (B) | `sonnet` |
| uzytkownik poprosil w tej rozmowie o "glebokie review" albo o Fable | dodatkowo RF (caly PR wzgledem celu zadania) | `fable` |

Agenci to `subagent_type: general-purpose` z modelem z tabeli. Podajesz im sciezki do plikow dossier, nie ich tresc. Uruchamiasz ich z `run_in_background: true`; triage zaczynasz, gdy przyjda powiadomienia od wszystkich. Gdy narzedzie Agent nie ma `run_in_background`, najpierw piszesz kontrakt, a R1 i R2 uruchamiasz razem w jednej wiadomosci.

## Krok 1: PR, tryb i dossier

1. PR z wiadomosci (numer, URL) albo z aktualnego brancha. Bez PR powiedz to i zakoncz.
   ```bash
   gh pr view {pr} --json number,title,url,author,body,headRefName,headRefOid,baseRefName,state
   gh repo view --json nameWithOwner --jq .nameWithOwner
   gh api user --jq .login
   ```
   Musisz byc w lokalnym klonie tego repo. Jesli nie jestes, zapytaj o sciezke.
2. Tryb: autor PR == zalogowany user -> **self**, inaczej -> **reviewer**. W trybie reviewer sprawdz moje poprzednie komentarze i review:
   ```bash
   gh api repos/{owner}/{repo}/issues/{pr}/comments --paginate --jq '[.[] | select(.user.login=="{me}") | {id, created_at, body}]'
   gh api repos/{owner}/{repo}/pulls/{pr}/reviews --paginate --jq '[.[] | select(.user.login=="{me}") | {id, submitted_at, state, body}]'
   ```
   Gdy ktorys zawiera `- [ ]` albo `- [x]`: `AskUserQuestion` **Re-review** / **Pelne review od nowa**. Re-review: dokoncz punkt 3 i przejdz do Kroku 6.
3. Dossier `{D}` = `<$TMPDIR albo /tmp, bez koncowego />/kp-code-review/{repo}-{pr}-{sha7}` (wpisuj doslownie). Worktree z head PR, working tree usera zostaje nietkniety:
   ```bash
   mkdir -p "{D}"
   git fetch -q origin {base} "pull/{pr}/head:refs/kp-review/{pr}"
   git worktree add -q --detach "{D}/wt" "refs/kp-review/{pr}"   # gdy {D}/wt istnieje, uzyj go
   git diff "origin/{base}...refs/kp-review/{pr}" > "{D}/diff.patch"
   ```
   Zapisz `{D}/pr.md` (tytul, autor, branch, opis) i `{D}/body.md` (sam opis). Potem w jednej wiadomosci dwa wywolania:
   ```bash
   (cd "{D}/wt" && python3 "$SKILL_DIR/scripts/context_pack.py" --base "origin/{base}" --head "refs/kp-review/{pr}" --out "{D}/context-pack.md")
   python3 "$SKILL_DIR/scripts/task_context.py" --branch "{headRefName}" --title "{title}" --body-file "{D}/body.md" --out "{D}/task.md"
   ```
   | exit `task_context.py` | Co robisz |
   |---|---|
   | 0 | dalej |
   | 3 (Jira nie odpowiada, zwykle brak VPN) | `AskUserQuestion`: Sprobuj ponownie / Wkleje tresc taska (zapisz do `{D}/task.md`) / Kontynuuj bez Jiry |
   | 4 (brak klucza taska) | zapytaj o klucz (`--key`) albo kontynuuj bez Jiry |
   | 2 (brak `jira.py`) | kontynuuj bez Jiry, wspomnij o zmiennej `KP_JIRA_SCRIPT` |

   Bez Jiry kontraktem jest opis PR; dopisz w review "Reviewed against the PR description; the task was not available".
4. Jedna linia dla usera: `PR #{pr} · tryb {self|reviewer} · task {KEY albo "bez Jiry"} · {N} plikow · recenzenci {ty | R1+R2 | R1+R2+RF}`.

`{repo_path}` dla agentow to `{D}/wt`: tam Read, Grep i git widza dokladnie head PR.

## Krok 2: R2, kontrakt, R1

1. PR nie jest maly: od razu spawn R2 (`model: sonnet`, prompt RECENZENT). R2 nie potrzebuje kontraktu.
2. Napisz sam `{D}/contract.md` wedlug szablonu KONTRAKT. Status kazdego AC potwierdzasz w kodzie (`plik:linia`).
3. Pokaz userowi 3-5 linii: cel, AC z problemem, tanie poprawki, rozjazdy z Jira, napiecia. Lec dalej bez pytania.
4. W jednej wiadomosci spawn R1 (`sonnet`) i, w glebokim review, RF (`fable`). Ten sam prompt RECENZENT z soczewka z tabeli.
5. Maly PR: przejdz sam pytania A, B i C (najwyzej 6 znalezisk) i zapisz `{D}/findings-self.json` w schemacie findings.

Specjalistow z repo (`.claude/agents/*.md`) dodajesz tylko na prosbe usera, z tym samym schematem findings.

## Krok 3: Triage (jeden przebieg)

**Skutek krytyczny (K):** PII, token albo cale body wiadomosci w logach; utrata danych lub eventu; bezpieczenstwo; awaria na sciezce z celu zadania.
**Tania poprawka:** poprawka P z kontraktu albo zmiana w komponencie tego PR rzedu kilkunastu linii, bez nowego mechanizmu (nowej kolejki, joba, tabeli).

Przeczytaj wszystkie `{D}/findings-*.json`. Najpierw polacz duplikaty (ten sam plik i mechanizm; zostaje lepszy dowod). Potem dla kazdego znaleziska werdykt wyznacza **pierwszy pasujacy wiersz**:

| # | Warunek | Werdykt |
|---|---|---|
| 1 | `preexisting: true` i PR tego nie pogarsza | DROP; NOT-COVERED, gdy dotyczy celu zadania |
| 2 | dotyczy zakresu sasiedniego subtaska z kontraktu | FOLLOW-UP z kluczem subtaska |
| 3 | kluczowa teza niesprawdzona: `verified_by` puste, "diff only" przy dowodzie spoza diffa albo samo przyznaje brak sprawdzenia; albo `confidence` < 60 | sprawdz sam jednym-dwoma wywolaniami narzedzi. Potwierdzone (wynik narzedzia pokazuje kod, ktory robi to, co mowi teza, albo wynik odtworzenia) -> dalsze wiersze, inaczej DROP. Teza o zachowaniu biblioteki wymaga jej zrodla albo odtworzenia |
| 4 | skutek K i tania poprawka | THIS-PR (checkbox), takze gdy opis PR akceptuje ryzyko |
| 5 | opis PR, dokumentacja zmieniona w PR albo Jira swiadomie akceptuje to ryzyko (masz cytat) | NOT-COVERED z ich mitygacja |
| 6 | skutek K, poprawka w zakresie zadania | THIS-PR |
| 7 | ryzyko realne, poprawka wykracza poza zakres zadania | NOT-COVERED z mitygacja (alert, task albo dokumentacja) |
| 8 | pozostale | NICE-TO-HAVE |

Poza tabela:
- rozjazd z AC, ktory zmienia zachowanie -> tylko sekcja Jira,
- funkcjonalnosc DODATKOWA bez uzasadnienia w opisie PR -> punkt "justify in the PR description or split",
- stan taska w Jirze i braki w opisie PR -> tylko do usera w czacie.

Limity: wszystkie checkboxy THIS-PR (polaczone po mechanizmie), najwyzej 3 nice-to-have i 3 punkty "Not covered" (wybierasz po skutku).

Pokaz userowi jedna linie: `Triage: X do poprawy w PR, Y follow-up, Z nice-to-have, V Not covered, W odrzuconych · napiecia N · Jira M`.

**Napiecie** to konflikt, w ktorym kazda z dwoch opcji kosztuje w innym komponencie (np. at-least-once w producencie vs deduplikacja w konsumencie). Gdy tania poprawka zamyka albo zaweza sciezke awarii, jest checkboxem (wiersz 4), a napieciem zostaje tylko reszta. Checkbox, ktory wybrana opcja napiecia pochlania, przenosisz do sekcji decyzji. Dla kazdego napiecia z kontraktu (najwyzej 2) `AskUserQuestion`: opcja A / opcja B / Zostaw jako otwarte pytanie. Po wyborze sam piszesz sekcje decyzji wedlug `references/review-format.md`: Decision, Why, checkboxy dla tego PR (logika zbedna po decyzji = checkbox "Remove ..."), punkty dla komponentu z sasiedniego subtaska. Otwarte napiecie -> "Open question" w "Not covered".

## Krok 4: Draft i wynik

Zbuduj review wedlug `references/review-format.md`. Kazdy punkt ma plik i dowod ze znaleziska.

**Tryb reviewer**
1. Zapisz `{D}/review.md` i pokaz go userowi w calosci.
2. `AskUserQuestion`: **Wyslij** / **Przeredaguj** / **Zostaw lokalnie**.
3. Przeredaguj to petla: po kazdej zmianie pelna nowa wersja i ponowne pytanie. Skracasz bez zmiany merytoryki, zmieniasz ton bez zmiany faktow. "ok" albo "dobra" to nie jest "Wyslij".
4. Wysylka tylko po **Wyslij**: `gh pr comment {pr} --body-file "{D}/review.md"`.
5. Po wysylce, gdy sa FOLLOW-UP do nowego taska, NOT-COVERED z mitygacja "task" albo punkty Jira: zaproponuj kazdy osobno i wykonaj tylko po zgodzie. `jira-create.py` i `jira-update.py` leza obok `jira.py` (sciezka z `task_context.py`):
   - nowy subtask: `python3 <dir>/jira-create.py "<title>" --parent <PARENT> --description "<...>" --ac "<...>" --markdown`,
   - rozjazd z AC: `python3 <dir>/jira-update.py <KEY> --comment "<...>"`. AC zmieniasz tylko na wyrazna prosbe.

**Tryb self**
1. Lista w czacie po polsku (format self).
2. Dla kazdego checkboxa `AskUserQuestion`: **Napraw lokalnie** / **Pomin** / **Dopisz jako znane ryzyko do Notes w opisie PR**. Napraw: pokaz zmiane, zastosuj przez `Edit`, nie commituj. Notes: pokaz nowy opis, po zgodzie `gh pr edit {pr} --body-file <plik>`.
3. Rozjazdy z Jira: zaproponuj poprawke opisu PR albo komentarz w Jirze, tylko po zgodzie.

## Krok 5: Sprzatanie i podsumowanie

```bash
git worktree remove --force "{D}/wt"
git update-ref -d "refs/kp-review/{pr}"
```

Pokaz: tryb, czy Jira byla dostepna, recenzenci, liczby (checkboxy / follow-up / nice-to-have / odrzucone), co wyslano (link, utworzone taski), sciezke dossier.

## Krok 6: Re-review (tryb reviewer)

1. Do `{D}/prior-review.md` zapisz moje komentarze i review z checkboxami (z datami). Ostatnia data to `T`. Komentarze innych osob po `T` zapisz do `{D}/replies.md`.
2. `reviewed_sha` to ostatni commit PR z `committedDate <= T`:
   ```bash
   gh pr view {pr} --json commits --jq '[.commits[] | select(.committedDate <= "T")] | last | .oid // empty'
   ```
   - Pusty wynik albo `git cat-file -e {reviewed_sha}` z bledem (rebase, force-push): przegladasz `{D}/diff.patch` calego PR, a review zaczyna sie od "The branch was rebased, so this re-review covers the whole PR".
   - Inaczej przyrost tylko w plikach PR:
     ```bash
     gh pr view {pr} --json files --jq '.files[].path' > "{D}/pr-files.txt"
     git diff "{reviewed_sha}" "refs/kp-review/{pr}" -- $(cat "{D}/pr-files.txt") > "{D}/changes-since-review.patch"
     ```
3. Przyrost do 150 linii: weryfikujesz sam wedlug promptu WERYFIKATOR. Wiekszy: jeden agent `sonnet` z tym promptem.
4. Nowe znaleziska przechodza triage z Kroku 3; kontraktem jest `{D}/prior-review.md`.
5. Draft w formacie re-review, potem ta sama petla co w Kroku 4.
6. Wszystko ADDRESSED albo ANSWERED i brak nowych punktow: `AskUserQuestion` **Approve z LGTM** / **Tylko komentarz** / **Nic**. Approve: `gh pr review {pr} --approve --body "<body>"`.
7. Opcjonalnie, po zgodzie: odhacz zalatwione punkty w poprzednim komentarzu (`gh api -X PATCH repos/{owner}/{repo}/issues/comments/{id} -F body=@<plik>`).

## Zasady

1. Na GitHub i do Jiry idzie tylko to, co user wybral (Wyslij / Approve / Utworz task). Bez stopek "Generated with Claude".
2. Punkt = plik, mechanizm, skutek, poprawka, dowod.
3. Kontrakt nie jest wyrocznia: AC moze byc bledne. Rozjazd PR z AC to blad PR albo zmiana zalozen do odnotowania w Jirze.
4. Styl, formatowanie i struktura katalogow nie sa tematem tego review.

## Typowe bledy

| Blad | Co robisz zamiast |
|---|---|
| Niepewny punkt odsylasz agentowi z pytaniem | Sprawdzasz go sam (wiersz 3 triage) albo odrzucasz |
| Fable "dla pewnosci" przy duzym PR | Fable tylko, gdy user poprosil o glebokie review |
| Konkretna poprawka w tym PR zamieniona w napiecie | Napiecie = dwie opcje, kazda placi w innym komponencie |
| PII w logach jako nice-to-have albo "accepted risk" | Wiersz 4 triage: skutek K z tania poprawka to checkbox, nawet gdy opis PR akceptuje ryzyko |
| Review jest parafraza opisu PR | Kontrakt wypisuje twierdzenia do obalenia, R1 je sprawdza |
| Dlugie review z kilkunastoma punktami | Limity z Kroku 3, sprawy Jiry tylko do usera |
| Triage zaczety przed powiadomieniem od ostatniego agenta | Czekasz na wszystkich |
