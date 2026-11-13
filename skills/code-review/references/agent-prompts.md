# Kontrakt i prompty

Placeholdery: `{D}` katalog dossier, `{n}` numer PR, `{owner}/{repo}`, `{base}` base branch, `{repo_path}` = `{D}/wt` (worktree z head PR). Read, Grep i git tylko w `{repo_path}`, wtedy `plik:linia` odnosi sie do head PR. Base to `origin/{base}`.

W promptach nie wklejaj sekcji **Pytania kontrolne** ani **Schemat findings**: podaj absolutna sciezke do tego pliku i kaz agentowi przeczytac tylko te dwie sekcje.

---

## KONTRAKT (piszesz sam) — Krok 2

Zrodla: `{D}/task.md` (task, story nadrzedna z komentarzami — tam sa ustalenia ze spotkan i z innymi zespolami — oraz sasiednie subtaski), `{D}/pr.md`, `{D}/diff.patch`, `{D}/context-pack.md`. Bez `task.md` kontraktem jest opis PR; zaznacz to na gorze.

Nie streszczaj PR. Ustal, co PR mial zrobic, i wypisz to, co recenzenci maja probowac obalic. Najwyzej ok. 60 linii. `{D}/contract.md`:

1. **Cel** — 1-3 zdania: jaki problem biznesowy rozwiazuje zadanie (ze story, nie z opisu PR).
2. **Ustalenia** — z komentarzy taska i story, kazde ze zrodlem (klucz, autor, data).
3. **AC** — kazde: SPELNIONE / BRAK / CZESCIOWO / KWESTIONOWANE, z `plik:linia`. KWESTIONOWANE = samo AC prowadzi do awarii albo kloci sie z celem lub ustaleniami (np. zakaz ponowienia operacji wysylanej at-most-once; "dokladnie raz" bez deduplikacji; AC opisuje tylko szczesliwa sciezke procesu przechodzacego przez kilka systemow). Opisz mechanizm.
4. **Rozjazd z Jira** — gdzie PR robi inaczej niz AC lub opis taska: co mowi Jira, co robi PR, blad PR czy zmiana zalozen.
5. **Zakres** — co nalezy do tego PR, a co do sasiednich subtaskow (klucz -> zakres).
6. **Twierdzenia do obalenia** — C1..Cn: zdania z opisu PR, komentarzy w kodzie i docs, ktore obiecuja gwarancje albo zachowanie ("never throws", "all or nothing", "duplicates handled by X", "no consumer affected"), z miejscem, gdzie kod powinien to gwarantowac.
7. **Funkcjonalnosci DODATKOWE** — F1..Fn: zmiany, ktore nie wynikaja z zadania (refactor, CI, infra, migracja poza zakresem).
8. **Tanie poprawki** — P1..Pn: dla kazdej sciezki awarii z AC i Cn sprawdz, czy zmiana w komponencie tego PR rzedu kilkunastu linii, bez nowego mechanizmu (nowej kolejki, joba, tabeli), ja zamyka albo zaweza. Taka poprawka to kandydat na checkbox, nawet gdy opis PR akceptuje ryzyko albo pelne rozwiazanie lezy gdzie indziej.
9. **Napiecia** — T1..Tn tylko dla tego, co zostaje po poprawkach P: kazda z dwoch opcji kosztuje w innym komponencie. Nazwa, sciezka awarii, opcja A, opcja B, kto placi gdzie. Nie rozstrzygaj.

Budzet: najwyzej ok. 15 wywolan narzedzi. Diff czytasz tam, gdzie wymaga tego status AC albo twierdzenie; reszte przegladaja recenzenci.

---

## RECENZENT — Krok 2

Wspolny prompt, `{lens}` i `{questions}` z tabeli nizej:

```
Jestes recenzentem w code review PR #{n} ({owner}/{repo}). Soczewka: {lens}. Twoje id: {id}.

Pliki: {D}/contract.md (cel, zakres, twierdzenia; gdy go jeszcze nie ma, pomin), {D}/pr.md, {D}/diff.patch, {D}/context-pack.md (punkt startowy do szukania poza diffem), repo z head PR: {repo_path}. Przeczytaj sekcje "Pytania kontrolne" i "Schemat findings" z {sciezka do tego pliku}.

Zasady dowodu:
- Znalezisko = plik:linia + krotki cytat + mechanizm + konkretny skutek + poprawka. Bez mechanizmu nie zglaszaj.
- Twierdzenie o kodzie spoza diffa (kto wola, co jest w innym pliku, wersja biblioteki, stan configu) sprawdz narzedziem i wpisz komende w verified_by. Gdy zachowanie da sie odtworzyc tanio (skrypt, tymczasowe repo w {D}/tmp), odtworz je i wpisz wynik. Teze o zachowaniu biblioteki sprawdzasz w jej zrodle (np. `.venv`, cache uv albo `node_modules`) albo odtworzeniem.
- Gdy wskazana linia nie jest dodana w diffie, sprawdz na base (git blame origin/{base} -- <plik>), czy problem istnial przed PR. Jesli tak i PR go nie pogarsza: preexisting = true.
- in_contract: AC / Cn / Pn / Fn / Tn / klucz sasiedniego subtaska / "none" / "unknown" (bez kontraktu).
- confidence ponizej 60 albo verified_by przyznajace brak sprawdzenia kluczowej tezy jest w porzadku: orkiestrator sprawdzi taki punkt sam.

Budzet: najwyzej 4 znaleziska, najwazniejsze najpierw. Po 20 wywolaniach narzedzi zapisz to, co masz. Styl, formatowanie i struktura katalogow to nie Twoj temat. Pola tekstowe po angielsku, zwiezle.

Pytania, od ktorych zaczynasz: {questions}

Zapisz {D}/findings-{id}.json i zwroc tylko liste: id, tytul, confidence.
```

| id | Model | `{lens}` | `{questions}` |
|---|---|---|---|
| R1 | sonnet | Po commicie, twierdzenia i testy | grupy A i C; przejdz po kazdym Cn, Pn, Tn i kazdej funkcjonalnosci DODATKOWEJ z contract.md |
| R2 | sonnet | Poza diffem | grupa B; przejdz po kazdej sekcji context-pack.md jak po liscie kandydatow |
| RF | fable (tylko glebokie review) | Caly PR wzgledem celu zadania | zacznij od Celu i Ustalen w contract.md: czego PR nie robi, a zadanie wymaga? Potem grupy A, B i C |

---

## WERYFIKATOR re-review — Krok 6

```
Re-review PR #{n} ({owner}/{repo}). Pliki: {D}/prior-review.md (moje poprzednie punkty z checkboxami i datami), {D}/changes-since-review.patch (zmiany w plikach PR od ostatniego review; po rebase zamiast niego {D}/diff.patch calego PR), {D}/replies.md (odpowiedzi autora), repo z head PR: {repo_path}. Przeczytaj sekcje "Pytania kontrolne" i "Schemat findings" z {sciezka do tego pliku}.

1. Kazdy punkt z checkboxem: ADDRESSED / PARTIAL / NOT-ADDRESSED / ANSWERED (autor uzasadnil, ze nie trzeba — ocen, czy uzasadnienie wytrzymuje). Dowod: plik:linia w head albo sha commita.
2. Tylko zmiany od ostatniego review, pytaniami A/B/C: czy poprawki wprowadzily nowy problem (komentarz obiecuje wiecej niz kod, nowy wyscig, brak testu na nowa sciezke, poprawka tylko w jednym z plikow rodzenstwa). Najwyzej 3 nowe znaleziska w schemacie findings. Po 20 wywolaniach narzedzi zapisz to, co masz.

Zapisz {D}/rereview.json: {"items":[{"text":"...","status":"...","evidence":"...","note":"..."}],"findings":[...]} i zwroc liczby per status oraz tytuly nowych znalezisk.
```

---

## Pytania kontrolne

**A. Po commicie i wspolbieznosc**
- Co sie stanie, gdy krok N+1 padnie po commicie kroku N? Czy ponowienie naprawia skutek, czy efekt przepada na zawsze?
- Kto deduplikuje? Czy producent jest at-most-once tam, gdzie konsument moglby byc idempotentny?
- Co moze sie zmienic miedzy odczytem a zapisem (cofniecie, wygasniecie, rownolegly request)? Czy zapis ponownie sprawdza warunek i liczbe zmienionych wierszy?
- Blad calego batcha vs pojedynczego elementu: czy exit code, metryka albo log klamia "sukces"? Czy wyjatek jest polykany?
- Granice czasu: pierwszy dzien miesiaca, polnoc w strefie czasowej, weekend, spozniony run, okno alertu krotsze niz przerwa — czy wynik jest poprawny i idempotentny?

**B. Poza diffem**
- Kto jeszcze wola zmieniona funkcje albo konsumuje zmieniony event, endpoint, kolumne, klucz configu — i co teraz dostanie?
- Czy plik ma rodzenstwo wymagajace tej samej zmiany (inne workflowy CI, overlaye stage/prod, inne implementacje tego samego wzorca)? Czy nowy plik trzyma konwencje istniejacych (nazwy, poziomy, struktura)?
- Jaki stan infrastruktury poza repo PR zaklada (kolejki, bindingi, policy, TTL, sekrety, uprawnienia) i gdzie jest opisany dla proda?
- Od jakiej reguly z CLAUDE.md albo docs PR odstepuje? Czy wyjatek jest zapisany?
- Czy wartosc safety-critical (dry_run, tenant, identyfikatory prod) jest dziedziczona z domyslnego configu przez kazde srodowisko?
- Co trafia do logow (PII, e-maile, tokeny, cale body wiadomosci)?
- Kolejnosc wdrozenia: migracja vs kod, producent vs konsument, stage vs prod.

**C. Twierdzenia i testy**
- Czy komentarz, docs albo opis PR obiecuje gwarancje, ktorej kod nie daje? Jak brzmialoby zdanie prawdziwe?
- Czy test sprawdza wlasnosc (np. "oba zapisy w jednej transakcji"), czy tylko "cos wywolano"?
- Czy jest test na sciezke, ktora PR wprowadza (ponowienie, blad publikacji, wyscig)?
- Czy uzyta wersja biblioteki ma prostszy albo atomowy sposob (wersje w context-pack)?
- Czy nowy kod duplikuje istniejacy wzorzec (rodzenstwo w context-pack)?

## Schemat findings

```json
{"findings": [{
  "id": "R1-1",
  "title": "Short title, max 80 chars",
  "file": "path/to/file.ts",
  "line": 42,
  "mechanism": "what happens, step by step",
  "consequence": "what breaks, for whom, when",
  "fix": "concrete change, snippet allowed",
  "evidence": [{"file": "path", "line": 1, "quote": "...", "source": "diff|repo|jira|context-pack|repro"}],
  "verified_by": "commands used, or 'diff only'",
  "in_contract": "AC2|C3|P1|F4|T1|<sibling task key>|none|unknown",
  "preexisting": false,
  "confidence": 80
}]}
```
