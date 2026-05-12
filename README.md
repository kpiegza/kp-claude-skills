# kp-claude-skills

Osobiste skille Claude Code, zapakowane jako lokalny plugin `kp`.

## Co tu jest

Szesc skilli (`skills/`) — wszystkie auto-aktywuja sie na podstawie kontekstu rozmowy:

- **`kp:sync-main`** — synchronizuje branch z `origin/main` z inteligentnym rozwiazywaniem konfliktow CHANGELOG / i18n.
- **`kp:address-review-comments`** — przejscie krok-po-kroku przez komentarze review PR z analiza i propozycjami fixow.
- **`kp:create-branch`** — interaktywne tworzenie brancha z prefiksem + opcjonalnym podpieciem taska Jira.
- **`kp:create-pull-request`** — utworzenie PR z ustrukturyzowanym opisem (Task / Context / Scope / Changes / Notes).
- **`kp:cleanup-merged-branches`** — bezpieczne usuwanie lokalnych i zdalnych branchy zmergowanych do main (z podwojnym checkiem git + GitHub PR, ochrona chronionych nazw, brak force delete bez zgody).
- **`kp:create-deployment-post`** — generuje wpis na kanal deployment Teams z pull requesta (`[scope] opis po polsku`), kopiuje do schowka.

## Instalacja

Z poziomu Claude Code:

```
/plugin marketplace add /Users/kpiegza/Projekty/kp-claude-skills
/plugin install kp@kp-claude-skills
```

Po instalacji i restarcie sesji skille widac jako `kp:sync-main`, `kp:address-review-comments`, `kp:create-branch`, `kp:create-pull-request`, `kp:cleanup-merged-branches`, `kp:create-deployment-post`.

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
