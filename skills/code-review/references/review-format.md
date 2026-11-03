# Format review

Jedno podsumowanie na runde, nie komentarze inline. Na GitHub po angielsku, w trybie self po polsku w czacie.

## Zasady

- Sekcja pojawia sie tylko, gdy ma tresc. Bez wstepu, bez sekcji "co jest dobrze", bez stopek.
- **Checkbox `- [ ]` = do zrobienia w tym PR** (werdykt THIS-PR). Wszystko inne to zwykle punkty bez checkboxa.
- Punkt: **pogrubiony tytul** (`plik` albo `plik:linia`): mechanizm, skutek, poprawka. 2-4 zdania. Snippet w bloku kodu tylko wtedy, gdy jest poprawka.
- 3-5 checkboxow na runde. Sedzia laczy punkty o tym samym mechanizmie; gdy nadal jest ich wiecej, pokazujesz wszystkie, posortowane po skutku.
- Werdykt -> sekcja: THIS-PR -> "Worth fixing in this PR"; FOLLOW-UP -> "Follow-up (<KEY>)"; NICE-TO-HAVE i SCOPE -> "Nice-to-have (can be a separate PR)"; NOT-COVERED -> "Not covered"; JIRA -> "Jira". SCOPE, ktory autor ma uzasadnic w opisie PR, moze byc checkboxem.
- Napiecie z wybrana przez usera opcja -> pierwsza sekcja z tytulem napiecia, zbudowana z `{D}/decision-{T}.md` ("**Decision:**", "Why:", checkboxy tego PR, follow-up drugiego komponentu). Napiecie bez decyzji -> punkt "Open question" w "Not covered".

## Pierwsze review (GitHub, EN)

```markdown
## `<topic>`: <tension, e.g. delivery vs. duplicates>

**Decision:** <one-sentence rule>. <why it matters, one sentence>

Why: <concrete failure path>.

### <component> (this PR)
- [ ] <what this PR has to do because of the decision>

### <other component> (follow-up, <KEY>)
- <what the sibling task has to do>

## Remaining review points

### Worth fixing in this PR
- [ ] **<Title>** (`path/to/file.ts`): <mechanism>. <consequence>. <fix>.

### Follow-up (<KEY>)
- **<Title>** (`path`): ...

### Nice-to-have (can be a separate PR)
- **<Title>** (`path`): ...

### Not covered
- <accepted risk>: <why acceptable now>. Mitigation: <alert / task / doc>.

### Jira
- <KEY> AC <n> says "<quote>", the PR <does X> (agreed in this review). Update the AC.
```

Bez napiecia: pomijasz pierwsza sekcje, a "Remaining review points" zamieniasz na "## Review".

## Re-review (GitHub, EN)

```markdown
## Re-review after the fixes

Thanks, the earlier points are addressed. <N> more:

- [ ] **Still open: <title>** (`path`): <what is still missing>.
- [ ] **<New title>** (`path`): <mechanism>. <consequence>. <fix>.
```

Gdy czesc punktow jest otwarta, pierwsze zdanie: "Thanks, `<sha7>` addresses most points. Still open:".

Wszystko zalatwione:

```markdown
Thanks, `<sha7>` and `<sha7>` look good. <N> optional nits, not blocking:

- **<Nit>** (`path`): ...
```

Approve (body `gh pr review --approve`): `LGTM, thanks.` + `The nits in the last comment are optional.`, gdy byly nity.

## Self-review (czat, PL)

Te same sekcje po polsku: **Do poprawy w tym PR**, **Follow-up (<KEY>)**, **Nice-to-have**, **Not covered**, **Jira**, **Napiecia do decyzji**. Pod kazdym checkboxem jedna linia: co zmienic i w ktorym pliku.

## Przyklad (fikcyjny)

```markdown
## `order.paid`: delivery vs. duplicates

**Decision:** publish on every successful payment confirmation, including the already-confirmed branch. Duplicates are cheap; a lost event is not.

Why: if anything fails after the commit (the invoice read or `publish` returning false), the client's retry hits `alreadyConfirmed` and nothing is published, so the event is gone for good.

### API (this PR)
- [ ] Publish in the `alreadyConfirmed` branch as well, with `paidAt` from the stored row.
- [ ] Normalize `customerEmail` the same way as the lookup (`trim().toLowerCase()`), or the worker won't match it.

### Worker (follow-up, SHOP-212)
- Claim with a conditional `UPDATE ... WHERE notified_at IS NULL RETURNING`, so two parallel events don't both send.

## Remaining review points

### Worth fixing in this PR
- [ ] **Comment overstates the guarantee** (`payment.service.ts`): "no paid order without the event" is not true, `publish` after the commit can still return false. Say what the transaction guarantees (all rows updated or none).

### Not covered
- `publish` returns false on the only confirmation: rare, the client has no reason to retry. Mitigation: an alert on the publisher's warn log.
```
