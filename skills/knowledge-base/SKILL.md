---
name: knowledge-base
description: Prywatna baza wiedzy w ~/Projekty/agent-knowledge-base - krotkie notatki Markdown typu decision (decyzja z powodami i odrzuconymi opcjami), gotcha (pulapka - objaw, przyczyna, rozwiazanie) i finding (wniosek z researchu lub wlasnej proby). Zapisuje notatke tylko po akceptacji szkicu przez uzytkownika, pilnuje struktury skryptem, czyta notatki przed decyzjami technicznymi i prowadzi comiesieczny przeglad. Uzyj gdy uzytkownik mowi: "zapisz do kb", "zapisz do bazy wiedzy", "dodaj do kb", "zanotuj to", "co mamy w kb o X", "czy juz to badalem", "sprawdz w bazie wiedzy", "przeglad kb", "kb lint", "knowledge base". Takze przed decyzja techniczna albo ocena technologii, gdy warto sprawdzic wczesniejsze ustalenia.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/knowledge_base.py:*), Bash(grep:*), Bash(git -C ~/Projekty/agent-knowledge-base:*), Read
---

# Prywatna baza wiedzy

Prowadzisz prywatna baze wiedzy uzytkownika: krotkie notatki Markdown, z ktorych korzystasz w kolejnych sesjach. Z uzytkownikiem rozmawiasz po polsku. Tresc notatek piszesz po polsku z polskimi znakami, nazwy plikow po angielsku.

## Gdzie

- Repo notatek: `~/Projekty/agent-knowledge-base` - pliki `notes/<technologia>-<temat>.md` i `INDEX.md`.
- Skrypt: `python3 ${CLAUDE_SKILL_DIR}/scripts/knowledge_base.py lint|check|stats`.
- `INDEX.md` generuje `check`. Nigdy nie edytuj go recznie.
- Kod wyjscia 2 (`knowledge base not found`) znaczy, ze repo notatek nie jest sklonowane na tej maszynie. Powiedz to i zakoncz.

## Co zapisywac

Test wejscia: jesli wyszukiwarka albo dokumentacja odpowie na to w minute, nie zapisuj.

Wchodzi:
- decyzja z powodami i odrzuconymi opcjami (`decision`),
- pulapka, ktora kosztowala czas: objaw, przyczyna, rozwiazanie (`gotcha`),
- wniosek z wlasnej proby albo zweryfikowanego researchu (`finding`),
- specyfika srodowiska uzytkownika i slepe uliczki.

Nie wchodzi: streszczenia dokumentacji i tutoriali, ogolne opisy technologii, surowe wyniki researchu bez weryfikacji, logi sesji, rzeczy zapisane w repo albo w `git log`.

Gdy uzytkownik prosi o zapis czegos z listy "nie wchodzi", nie zapisuj. Powiedz, ze to nie przechodzi testu wejscia, i zaproponuj, co z tego warto zapisac (np. jego wlasny wniosek albo decyzje).

## Zapis

Tylko na polecenie uzytkownika. Kroki:

1. Jesli `git -C ~/Projekty/agent-knowledge-base remote` pokazuje `origin`: `git -C ~/Projekty/agent-knowledge-base pull --rebase --autostash`.
2. Ustal typ: `decision`, `gotcha` albo `finding`.
3. Szukaj istniejacej notatki: `grep -i` w `INDEX.md` i w `notes/`, po polskich i angielskich slowach. Jesli jest notatka na ten temat, popraw ja: przepisz cala tresc od nowa (nie dopisuj na koncu) i ustaw `checked` na dzis. Nie tworz drugiej notatki o tym samym.
4. Przeczytaj `${CLAUDE_SKILL_DIR}/templates.md`. Przygotuj szkic (do 150 slow tresci) i pokaz go w czacie razem z nazwa pliku.
5. Czekaj na akceptacje. Bez niej nic nie zapisuj.
6. Zapisz plik i uruchom `check`. Przy bledach popraw notatke i uruchom `check` ponownie.
7. `git -C ~/Projekty/agent-knowledge-base add notes INDEX.md`, potem `git -C ~/Projekty/agent-knowledge-base commit -m "kb: add <slug>"` (albo `kb: update <slug>`, `kb: delete <slug>`). `<slug>` to nazwa pliku bez `.md`. Commit na `main`, bez `Co-Authored-By` i bez innej atrybucji.
8. Jesli jest `origin`: `git -C ~/Projekty/agent-knowledge-base push origin main`.

W tym repo nigdy nie tworz branchy ani pull requestow. Gdy push sie nie uda, powiedz to i zostaw commit lokalnie.

## Odczyt

Kiedy: przed decyzja techniczna, przy ocenie technologii, gdy debugowanie sie przeciaga, gdy uzytkownik pyta, co mamy w kb.

1. `grep -i <slowo> ~/Projekty/agent-knowledge-base/INDEX.md` - probuj polskich i angielskich slow.
2. Przeczytaj najwyzej 3 trafione notatki narzedziem Read (nie `cat`: hook liczy tylko odczyty przez Read).
3. Sprawdz `applies` i `checked`. Jesli notatka moze byc nieaktualna (inna wersja, stara data), powiedz to.
4. Gdy notatka wplynela na odpowiedz, dodaj jedna linie: `Z kb: <slug>`.

## Kandydat do kb

Po zadaniu, z ktorego zostal trwaly wniosek, mozesz dodac najwyzej jedna linie: `Kandydat do kb: <wniosek w jednym zdaniu>`. Niczego nie zapisuj sam.

## Przeglad ("przeglad kb", "kb lint")

1. Uruchom `lint` i `stats`.
2. Przy kazdym ERROR i WARN, a takze przy notatce z 0 sesji w ostatnich 90 dniach i `checked` starszym niz 90 dni, zapytaj uzytkownika: potwierdzic, poprawic czy usunac.
3. `checked` podbijaj tylko po realnym sprawdzeniu. Nieaktualne notatki usuwaj zamiast archiwizowac - historia zostaje w gicie.
4. Na koniec `check`, commit i push jak przy zapisie.

## Twarde reguly

- Frontmatter: dokladnie `type`, `when` (do 120 znakow: w jakiej sytuacji czytac notatke), `applies`, `checked` (`YYYY-MM-DD`), `proof` (`tested` albo `read`). Zadnych innych pol.
- Tresc: pierwsza linia `# Tytul`, do 150 slow, sekcje wedlug `templates.md`. Etykiety sekcji i linii ze zrodlem kopiuj z `templates.md` dokladnie, z polskimi znakami. Przy `proof: read` linia ze zrodlem jest wymagana.
- Nazwa pliku: `<technologia>-<temat>.md` - male litery, cyfry i myslniki, po angielsku.
- Bez akceptacji uzytkownika nic nie trafia do repo.
