---
name: address-review-comments
description: Analizuje komentarze z pull requesta dla aktualnego brancha. Pobiera komentarze z GitHub, analizuje kazdy z nich (problem, rozwiazanie, priorytet) i przeprowadza uzytkownika krok po kroku, pytajac czy poprawic czy pominac. Po zakonczeniu oznacza naprawione komentarze jako resolved i dodaje odpowiedzi do pominieetych. Uzyj tego skilla gdy uzytkownik chce przejrzec komentarze z PR, odpowiedziec na review, naprawic uwagi z code review, lub wspomina o komentarzach/review w PR. Takze gdy uzytkownik mowi "sprawdz komentarze", "przejdz przez review", "napraw uwagi z PR", "co jest do poprawy w PR", "review comments", "address feedback".
allowed-tools: Read, Grep, Glob, Bash(git:*), Bash(gh:*), Edit, Write, AskUserQuestion, Agent
---

# PR Comment Analyzer

Analizujesz komentarze z review pull requesta i prowadzisz uzytkownika krok po kroku przez kazdy z nich, przedstawiajac analize i rekomendacje po polsku, a nastepnie pytajac czy naprawic czy pominac.

Cala komunikacja z uzytkownikiem jest po polsku.

## Krok 1: Identyfikacja brancha i PR

```bash
# Aktualny branch
git branch --show-current

# PR dla tego brancha
gh pr list --head "$(git branch --show-current)" --json number,title,url --jq '.[0]'
```

Jesli nie znaleziono PR dla aktualnego brancha, poinformuj uzytkownika i zakoncz. Nie zgaduj i nie pytaj o numer PR.

## Krok 2: Pobranie komentarzy

```bash
# Inline review comments
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments --jq '.[] | {id, path, line, body, user: .user.login, created_at, diff_hunk, in_reply_to_id}'

# Top-level PR comments
gh api repos/{owner}/{repo}/issues/{pr_number}/comments --jq '.[] | {id, body, user: .user.login, created_at}'
```

Pobierz `{owner}/{repo}` z git remote:
```bash
gh repo view --json nameWithOwner --jq '.nameWithOwner'
```

**Filtrowanie:**
- Pomin komentarze od aktualnego uzytkownika (to odpowiedzi, nie feedback)
- Pomin komentarze od botow (github-actions, dependabot, itp.)
- Grupuj watki odpowiedzi — jesli komentarz jest odpowiedzia (`in_reply_to_id` ustawione), dolacz go do komentarza nadrzednego
- Jesli brak komentarzy do review, poinformuj uzytkownika i zakoncz

## Krok 3: Analiza kazdego komentarza

Dla kazdego komentarza (lub watku komentarzy) przeprowadz analize:

1. **Zrozum kontekst** — przeczytaj `diff_hunk` zeby zrozumiec jakiego kodu dotyczy komentarz. Jesli diff hunk nie wystarcza, przeczytaj plik wskazany w `path` i `line`.

2. **Sklasyfikuj typ komentarza:**
   - **Bug/Blad** — reviewer znalazl prawdziwy bug, bledna logike lub potencjalny blad runtime
   - **Bezpieczenstwo** — podatnosc, brak walidacji, problem z uprawnieniami
   - **Styl/Konwencja** — nazewnictwo, formatowanie, preferencje stylu kodu
   - **Architektura/Design** — problem strukturalny, coupling, separacja odpowiedzialnosci
   - **Wydajnosc** — nieefektywnosc, brak optymalizacji
   - **Sugestia** — usprawnienie nice-to-have, alternatywne podejscie
   - **Pytanie** — reviewer prosi o wyjasnienie (moze nie wymagac zmian w kodzie)
   - **Nitpick** — drobna kwestia kosmetyczna, literowka

3. **Ocen priorytet:**
   - **Trzeba naprawic** — bugi, problemy bezpieczenstwa, uszkodzona funkcjonalnosc
   - **Warto naprawic** — uzasadnione uwagi architektoniczne lub wydajnosciowe
   - **Miło miec** — usprawnienia stylu, drobne sugestie
   - **Kandydat do pominiecia** — nitpicki, czysto subiektywne preferencje, juz zaadresowane

4. **Zaproponuj rozwiazanie** — jesli komentarz wymaga naprawy, opisz konkretnie co trzeba zmienic. Podaj plik i linie. Jesli fix jest prosty, przygotuj dokladna zmiane kodu.

## Krok 4: Przejscie przez komentarze jeden po drugim

Przedstaw kazdy komentarz uzytkownikowi w tym formacie:

```
### Komentarz [N/total] — [Typ] — [Priorytet]
**Reviewer:** @username
**Plik:** path/to/file.ts:line
**Komentarz:** "tresc komentarza reviewera"

**Analiza:** Co reviewer wskazuje i dlaczego to jest wazne (lub nie).

**Rekomendacja:** Twoja konkretna sugestia — co zmienic i jak, lub dlaczego mozna bezpiecznie pominac.
```

Nastepnie zapytaj uzytkownika co zrobic. Uzyj AskUserQuestion z opcjami:
- **Napraw** — zastosuj rekomendowana zmiane
- **Pomin** — przejdz dalej bez zmian

Jesli uzytkownik wybierze "Napraw":
- Zastosuj fix natychmiast (edytuj plik)
- Pokaz krotko co zmieniles
- Przejdz do nastepnego komentarza

Jesli uzytkownik wybierze "Pomin":
- Przejdz do nastepnego komentarza

**Zapamietuj decyzje** — zapisuj ktore komentarze naprawiono (z ich `id`), a ktore pominieto. Bedziesz tego potrzebowal w kroku 6.

## Krok 5: Podsumowanie

Po przejsciu wszystkich komentarzy pokaz krotkie podsumowanie:

```
### Podsumowanie
- Wszystkich komentarzy: X
- Naprawionych: Y
- Pominietych: Z
```

Wymien pominiete komentarze krotko (jedna linia kazdy).

## Krok 6: Aktualizacja komentarzy na GitHub

Po podsumowaniu, automatycznie zaktualizuj komentarze na GitHub:

### Naprawione komentarze — oznacz jako resolved

Dla kazdego review komentarza ktory zostal naprawiony, uzyj GitHub GraphQL API zeby oznaczyc go jako resolved (nie dodawaj komentarza tekstowego — sam resolve wystarczy):

```bash
# 1. Pobierz wszystkie review threads z PR razem z ich comment IDs
gh api graphql -f query='
  query {
    repository(owner: "{owner}", name: "{repo}") {
      pullRequest(number: {pr_number}) {
        reviewThreads(first: 50) {
          nodes {
            id
            isResolved
            comments(first: 1) {
              nodes { id }
            }
          }
        }
      }
    }
  }
' --jq '.data.repository.pullRequest.reviewThreads.nodes[] | {threadId: .id, commentId: .comments.nodes[0].id, isResolved: .isResolved}'

# 2. Dopasuj thread ID do comment node_id ktory chcesz rozwiazac

# 3. Oznacz watek jako resolved
gh api graphql -f query='
  mutation {
    resolveReviewThread(input: { threadId: "THREAD_ID_HERE" }) {
      thread { isResolved }
    }
  }
'
```

Jesli resolve przez GraphQL nie zadziala (np. brak watku), jako fallback dodaj krotka odpowiedz po polsku:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies \
  -f body="Naprawione."
```

### Pominiete komentarze — dodaj odpowiedz po polsku

Dla kazdego pominietego inline review komentarza, dodaj odpowiedz po polsku wyjasniajaca decyzje:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies \
  -f body="Pomijam — nie wplywa na funkcjonalnosc w obecnym zakresie."
```

Dla top-level (issue) komentarzy uzyj:
```bash
gh api repos/{owner}/{repo}/issues/{pr_number}/comments \
  -f body="Przyjete do wiadomosci — zaadresowane czesciowo. Szczegoly w odpowiedziach inline."
```

**Wazne:** Przed wysylaniem odpowiedzi na GitHub zapytaj uzytkownika o potwierdzenie — pokaz liste co zostanie wyslane i pozwol zatwierdzic lub edytowac tresc odpowiedzi.

## Wazne zasady

1. **Czytaj kod** — nie analizuj komentarzy w izolacji. Zawsze sprawdz plik zeby zrozumiec pelny kontekst.
2. **Badz szczery co do priorytetu** — jesli komentarz to nitpick, powiedz to. Jesli to prawdziwy bug, powiedz to. Uzytkownik korzysta z Twojej szczerej oceny.
3. **Szanuj wzorce projektu** — przy proponowaniu fixow, stosuj wzorce z CLAUDE.md jesli istnieje (uprawnienia z tenant, soft deletes, code-first GraphQL, itp.).
4. **Grupuj powiazane komentarze** — jesli wiele komentarzy na tym samym pliku dotyczy tego samego problemu, przedstaw je razem jako jeden punkt.
5. **Kontekst watku ma znaczenie** — gdy komentarz ma odpowiedzi, przeczytaj caly watek. Dyskusja mogla juz rozwiazac problem.
6. **Nie przekombinuj fixow** — zastosuj minimalna zmiane ktora odpowiada na uwage reviewera. Fix z review to nie czas na szeroki refactoring.
