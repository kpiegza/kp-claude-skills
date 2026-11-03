---
name: create-deployment-post
description: Wpis o wdrozeniu na kanal Teams Monetisation / Deployments na podstawie pull requesta (z aktualnego brancha, numeru albo URL PR). Temat `[scope] krotki opis po polsku`, tresc = link do PR. Buduje na skillu monetisation-core:rasp-teams - czyta kanaly Pull Request and Code Review oraz Deployments, wzoruje sie na wczesniejszych wpisach (gdy PR byl juz ogloszony na PR&CR, przejmuje jego temat), pokazuje podglad i publikuje dopiero po zgodzie uzytkownika; bez Teams kopiuje temat do schowka. Uzyj gdy uzytkownik mowi: "wpis na teams", "wpis deploymentowy", "tekst na teams", "wygeneruj wpis na deployment", "co wdrazam", "wpis na kanal deployment", "deployment message", "post na teams", "message na deployment kanal", "co napisac na teams", "oglos wdrozenie", "wrzuc na deploymenty", "napisz na deployments", "opublikuj wdrozenie na teams", "wyslij wpis o wdrozeniu", "post deploymentowy", "wdrozone, daj znac na teams".
model: haiku
effort: medium
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/deploy_post.py prepare:*), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/deploy_post.py preview:*), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/deploy_post.py clipboard:*), AskUserQuestion
---

# Create Deployment Post

Zakladasz watek na kanale Teams **Monetisation / Deployments**: temat `[scope] opis`, tresc = link do PR. Z uzytkownikiem rozmawiasz po polsku. Jedyne narzedzia: skrypt `python3 ${CLAUDE_SKILL_DIR}/scripts/deploy_post.py` i `AskUserQuestion`. Nie uzywasz gh, git, pbcopy ani teams.py - wszystko robi skrypt.

## Dane (zebrane przed startem)

!`python3 ${CLAUDE_SKILL_DIR}/scripts/deploy_post.py prepare '$ARGUMENTS'`

Blok powyzej: PR, kandydaci na scope, wpis z PR&CR (jesli jest), moje wczesniejsze wpisy jako wzorce, gotowa komenda `preview`. Jesli zamiast bloku widzisz sama komende, blok dotyczy innego PR niz chcial uzytkownik albo zawiera `BLAD`, uruchom `python3 ${CLAUDE_SKILL_DIR}/scripts/deploy_post.py prepare <numer|URL>` z wlasciwym PR i pracuj na nowym bloku. Bez PR nie zgaduj: zapytaj o numer albo URL i zakoncz.

## Krok 1: temat

1. **Jest wpis PR&CR** dla tego PR -> temat = jego temat, doslownie, razem z polskimi znakami i tagami; reguly z punktu 2 go nie dotycza. Zmien go tylko, gdy uwagi uzytkownika albo opis PR mowia, ze wdrozenie rozni sie od PR (np. "tylko INT", numer wersji, czesc zmian).
2. **Brak wpisu** -> uloz temat; "Moje wpisy" to wzor stylu opisu, nie zrodlo scope:
   - `[scope] Opis`. Scope = pierwszy kandydat z bloku. Nazwa repo tylko gdy zmiana dotyczy calego repo (CI, obraz bazowy, zaleznosci) albo kilku aplikacji naraz. Drugi tag `[komponent]` tylko gdy moje wpisy dla tego repo tak robia.
   - Opis **po polsku z polskimi znakami** (ą ę ł ś ż ...), 40-100 znakow, wielka litera, rzeczownik odczasownikowy albo fraza: "Wysyłka X do Y po Z", "Zmiana X na Y w Z", "Poprawka Z", "Podbicie X -> Y". Bez "wdrażam", bez kropki na koncu, bez prefiksu feat/fix.
   - Konkrety z PR (nazwy kolumn, wersje, CVE, klienci, nazwy dagow) zostaja doslownie. Nie powtarzaj scope w opisie. Nie dopisuj niczego, czego nie ma w tytule i opisie PR.
3. Tresc: link do PR dodaje skrypt. `--note "<linia>"` tylko gdy uzytkownik o to prosi (wpis PR&CR z dodatkowym akapitem nie jest powodem).

## Krok 2: podglad i zgoda

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/deploy_post.py preview --pr <URL PR> --subject "<temat>" [--note "<linia>"]
```

W odpowiedzi pokaz doslownie temat i tresc z podgladu (sekcja "Treść (sformatowana)"), jedna linie o zrodle tematu (z PR&CR / nowy) i kazde `UWAGA` z bloku danych (np. PR byl juz na Deployments). Gdy opis PR ma kroki wdrozeniowe (okno wdrozenia, kolejnosc, cos do zrobienia po deployu), przypomnij je jednym zdaniem - do wpisu ich nie dodajesz. Potem `AskUserQuestion` z opcjami:
- **Wyslij** -> Krok 3.
- **Popraw** -> nowy temat albo wskazowka z odpowiedzi, powtorz Krok 2.
- **Tylko schowek** -> `python3 ${CLAUDE_SKILL_DIR}/scripts/deploy_post.py clipboard --subject "<temat>"`, koniec.
- **Anuluj** -> koniec, nic nie wysylasz.

Gdy wynik `preview` zaczyna sie od `TEAMS NIEDOSTEPNE`: temat jest juz w schowku; przekaz uzytkownikowi powod i instrukcje z wyniku, zakoncz.

## Krok 3: wysylka

Tylko po wyborze **Wyslij**: `python3 ${CLAUDE_SKILL_DIR}/scripts/deploy_post.py confirm <ID>` (ID z podgladu). Celowo nie ma jej w `allowed-tools` skilla (moze pojawic sie prompt uprawnien); jedyna droga do wysylki to wybor **Wyslij**. Potem jedna linia: co i gdzie wyslano. `WYNIK NIEZNANY` -> nie wysylaj drugi raz, popros uzytkownika o sprawdzenie kanalu.

## Zasady

- Nic nie idzie do Teams bez zgody na pokazany podglad: wybor **Wyslij** albo wprost napisane "wyslij". "ok", "dobra", "moze byc" to nie zgoda.
- Kazda zmiana tematu = nowy `preview` i nowe pytanie.
- Jeden PR = jeden watek. Wpisu na kanale nie da sie poprawic po wyslaniu.
- Nie modyfikujesz PR ani repo.
