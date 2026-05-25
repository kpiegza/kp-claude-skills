# kp-claude-skills

Osobiste skille Claude Code, zapakowane jako lokalny plugin `kp`.

## Co tu jest

Dziewiec skilli (`skills/`) — wszystkie auto-aktywuja sie na podstawie kontekstu rozmowy. Podzielone na dwie grupy: **programowanie** i **pisanie prac**.

### Skille deweloperskie

Wspieraja codzienny workflow git + GitHub: branche, PR-y, code review, deploymenty.

- **`kp:sync-main`** — synchronizuje branch z `origin/main` z inteligentnym rozwiazywaniem konfliktow CHANGELOG / i18n.
- **`kp:address-review-comments`** — przejscie krok-po-kroku przez komentarze review PR z analiza i propozycjami fixow.
- **`kp:create-branch`** — interaktywne tworzenie brancha z prefiksem + opcjonalnym podpieciem taska Jira.
- **`kp:create-pull-request`** — utworzenie PR z ustrukturyzowanym opisem (Task / Context / Scope / Changes / Notes).
- **`kp:cleanup-merged-branches`** — bezpieczne usuwanie lokalnych i zdalnych branchy zmergowanych do main (z podwojnym checkiem git + GitHub PR, ochrona chronionych nazw, brak force delete bez zgody).
- **`kp:create-deployment-post`** — generuje wpis na kanal deployment Teams z pull requesta (`[scope] opis po polsku`), kopiuje do schowka.
- **`kp:code-review`** — interaktywny code review PR: konfigurowalny poziom surowosci, severity filter (krytyczne / +srednie / wszystko), wybor czy postowac inline komentarze na GitHub czy poprawiac kod lokalnie. Spawnuje rownolegla analize wieloagentowa (na wzor `/code-review:code-review`) i prowadzi krok-po-kroku przez znaleziska.

### Skille do pisania prac

Wspieraja prace pisemne (eseje, prace dyplomowe) w **stylu uzytkownika** — najpierw budujesz profil stylu z wlasnych tekstow, potem generujesz nowe teksty w tym samym tonie, opcjonalnie z formatowaniem zgodnym z wymogami uczelni.

- **`kp:analyze-writing-style`** — analizuje teksty uzytkownika w `corpus/` (PDF, DOCX, TXT, MD) i buduje/aktualizuje `profile/writing-style.md`. Wyciaga sygnatury stylu (spojniki, dlugosc zdan, manieryzmy, anty-wzorce) z cytatami dowodowymi. Obsluguje import plikow spoza repo (np. `~/Downloads/esej.docx`) — sam przenosi/kopiuje do `corpus/`.
- **`kp:write-in-my-style`** — pisze tekst (rozdzial pracy magisterskiej, fragment licencjatu, esej, akapit) w stylu uzytkownika na podstawie `profile/writing-style.md`. Akapit-po-akapicie z auto-weryfikacja zgodnosci ze stylem. Opcjonalnie generuje DOCX zgodny z wymogami uczelni (`profile/university-requirements/`).

**Dane prywatne:**
- `corpus/` — Twoje teksty zrodlowe (gitignore'owane, nigdy nie trafia do repo)
- `profile/writing-style.md` — wygenerowany profil stylu z cytatami (gitignore'owany)
- `profile/university-requirements/` — publicznie dostepne wymogi uczelni (commitowane)

## Instalacja

Z poziomu Claude Code:

```
/plugin marketplace add /Users/kpiegza/Projekty/kp-claude-skills
/plugin install kp@kp-claude-skills
```

Po instalacji i restarcie sesji skille widac jako `kp:sync-main`, `kp:address-review-comments`, `kp:create-branch`, `kp:create-pull-request`, `kp:cleanup-merged-branches`, `kp:create-deployment-post`, `kp:code-review`, `kp:analyze-writing-style`, `kp:write-in-my-style`.

## Aktualizacja

Edytujesz pliki w tym repo → nastepna sesja Claude Code juz widzi zmiany (cache pluginu wskazuje na to repo).

Synchronizacja miedzy maszynami:

```bash
git pull
```

## Setup na nowej maszynie

```bash
git clone <repo-url> ~/Projekty/kp-claude-skills
# w Claude Code:
/plugin marketplace add ~/Projekty/kp-claude-skills
/plugin install kp@kp-claude-skills
```

Dla skilli do pisania prac dodatkowo:

```bash
# Wymagane narzedzia do generowania DOCX
brew install pandoc
pip3 install python-docx
```
