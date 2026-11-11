# Szablony notatek

Etykiety kopiuj dokładnie, z polskimi znakami. Linie z `opcjonalnie` możesz pominąć. Linia `Źródło:` jest wymagana przy `proof: read`. Całość treści (od `# ` w dół) ma najwyżej 150 słów.

## decision

```markdown
---
type: decision
when: <w jakiej sytuacji przeczytać, max 120 znaków>
applies: <wersja / środowisko / projekt>
checked: <YYYY-MM-DD>
proof: <tested|read>
---
# <Decyzja w jednym zdaniu>
**Decyzja:** <co wybrano>
**Dlaczego:** <główny powód>
**Odrzucone:** <opcja (powód); opcja (powód)>
**Wrócić, gdy:** <opcjonalnie: warunek ponownej oceny>
Źródło: <link lub miejsce; wymagane przy proof: read>
```

## gotcha

```markdown
---
type: gotcha
when: <w jakiej sytuacji przeczytać, max 120 znaków>
applies: <wersja / środowisko / projekt>
checked: <YYYY-MM-DD>
proof: <tested|read>
---
# <Objaw w kilku słowach>
**Objaw:** <co widać>
**Przyczyna:** <dlaczego>
**Rozwiązanie:** <co pomogło>
**Ślepy trop:** <opcjonalnie: co nie pomogło>
Źródło: <wymagane przy proof: read>
```

## finding

```markdown
---
type: finding
when: <w jakiej sytuacji przeczytać, max 120 znaków>
applies: <wersja / środowisko / projekt>
checked: <YYYY-MM-DD>
proof: <tested|read>
---
# <Wniosek w kilku słowach>
**Pytanie:** <co sprawdzaliśmy>
**Wniosek:** <odpowiedź>
**Dlaczego:** <główne argumenty>
**Nie dotyczy:** <opcjonalnie: kiedy wniosek nie obowiązuje>
Źródło: <wymagane przy proof: read>
```

# Przykłady

## decision — `notes/postgres-queue-skip-locked.md`

```markdown
---
type: decision
when: wybór kolejki zadań dla serwisu, który już ma Postgresa
applies: billing-api, PostgreSQL 16, do ok. 200 zadań/s
checked: 2026-10-14
proof: tested
---
# Kolejka zadań w Postgresie (SKIP LOCKED), nie w SQS
**Decyzja:** tabela `jobs` i `SELECT … FOR UPDATE SKIP LOCKED`.
**Dlaczego:** zadanie powstaje w tej samej transakcji co zmiana domenowa, więc nie trzeba outboxa.
**Odrzucone:** SQS (druga infrastruktura, brak transakcyjności); Redis Streams (słabsza trwałość).
**Wrócić, gdy:** ruch przekroczy 200 zadań/s albo tabela puchnie mimo autovacuum.
```

## gotcha — `notes/sed-in-place-macos.md`

```markdown
---
type: gotcha
when: sed -i w skrypcie działa na Linuksie, a na macOS kończy się błędem
applies: macOS (BSD sed), skrypty bash współdzielone z CI na Linuksie
checked: 2026-11-03
proof: tested
---
# sed -i psuje się na macOS
**Objaw:** `sed -i 's/a/b/' plik` na macOS kończy się błędem „invalid command code”.
**Przyczyna:** BSD sed wymaga po `-i` argumentu z rozszerzeniem kopii zapasowej.
**Rozwiązanie:** `sed -i '' 's/a/b/' plik` na macOS albo `perl -pi -e`, które działa wszędzie.
**Ślepy trop:** `sed -i -e` na macOS po cichu tworzy kopię `plik-e`.
```

## finding — `notes/vitest-vs-jest-monorepo.md`

```markdown
---
type: finding
when: rozważana migracja testów z Jest na Vitest w monorepo
applies: monorepo TS, pnpm workspaces, Jest 29, Vitest 3
checked: 2026-09-22
proof: tested
---
# Vitest skraca nasze CI, ale migracja nie jest darmowa
**Pytanie:** czy przejście z Jest na Vitest skróci CI?
**Wniosek:** tak, w spike'u z 9 do 6 minut; migrować pakiet po pakiecie.
**Dlaczego:** natywny ESM bez transformacji Babel; 31 plików wymagało zmian w mockach modułów.
**Nie dotyczy:** pakietów z własnym środowiskiem testowym opartym na jsdom 16.
Źródło: branch `spike/vitest` i log CI z 2026-09-21.
```
