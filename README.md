# kp-claude-skills

Osobiste skille Claude Code, zapakowane jako lokalny plugin `kp`.

## Co tu jest

Cztery skille (`skills/`) — wszystkie auto-aktywuja sie na podstawie kontekstu rozmowy:

- **`kp:sync-main`** — synchronizuje branch z `origin/main` z inteligentnym rozwiazywaniem konfliktow CHANGELOG / i18n.
- **`kp:address-review-comments`** — przejscie krok-po-kroku przez komentarze review PR z analiza i propozycjami fixow.
- **`kp:create-branch`** — interaktywne tworzenie brancha z prefiksem + opcjonalnym podpieciem taska Jira.
- **`kp:create-pull-request`** — utworzenie PR z ustrukturyzowanym opisem (Task / Context / Scope / Changes / Notes).

## Instalacja

Z poziomu Claude Code:

```
/plugin marketplace add /Users/kpiegza/Projekty/kp-claude-skills
/plugin install kp@kp-claude-skills
```

Po instalacji i restarcie sesji skille widac jako `kp:sync-main`, `kp:address-review-comments`, `kp:create-branch`, `kp:create-pull-request`.

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
