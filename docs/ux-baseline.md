# The usability baseline

*What the ten tasks of [the usability plan](ux-plan.md) cost today, measured in a real
browser against v1.191.0 before a line of the plan was built. Every release of the plan
reruns the tasks it touches and reports the difference against these numbers.*

## How it was measured

The harness is [`scripts/ux_bench`](../scripts/ux_bench/README.md), driving the Dutch
interface in Chromium at 1440×900 against an organisation installation with the shipment
history on. An **action** is a click, a value typed into a field, or a key pressed to
move on. A **window** is a modal opening. **Forms** are the forms crossed inside the
shipment-details step, which the main step counter cannot see.

What is not measured is said as much: the harness does not know how long somebody takes
to think, so no task duration is claimed. Its own seconds are recorded in the JSON only
to spot a task that got slower to drive.

## The numbers

| Task | Actions | Windows | Steps | Forms | Back-steps | Repeated | Completed |
|---|---|---|---|---|---|---|---|
| 1 A simple shipment to a downloaded package | 26 | 3 | 2 | 2 | 0 | 3 | yes |
| 2 Five quantities changed on five lines | 15 | 5 | 0 | 0 | 0 | 0 | yes |
| 3 Fifty rows imported, one unclear | 3 | 1 | 0 | 0 | 0 | 0 | yes |
| 4 A substance suggestion closed, judged and revisited | 8 | 2 | 0 | 0 | 0 | 0 | **no** |
| 5 An extra document needing one new answer | 7 | 0 | 4 | 3 | 1 | 3 | yes |
| 6 An error corrected from the final overview | 11 | 0 | 4 | 2 | 1 | 3 | yes |
| 7 An earlier shipment as a new basis | 2 | 0 | 0 | 0 | 0 | 0 | yes |
| 8 A reload during entry (organisation) | 5 | 1 | 1 | 0 | 0 | 0 | **no** |
| 9 Five shipments into one trip | 5 | 0 | 0 | 0 | 0 | 0 | yes |
| 10 A refused save recovered | 1 | 0 | 2 | 2 | 0 | 3 | yes |

Tasks 5, 6 and 10 count only the part that is theirs: reaching the export step is task
1's cost, and is not counted twice.

## What the run found

**1 — a simple shipment.** Three goods lines and a CMR cost 26 actions, three dialogs
and two forms. Nine of those actions are the line dialog opening and closing three
times. After **Regel toevoegen** the focus stays on the button, so the new line's
description has to be found and clicked before it can be typed.

The one field that decides whether anything can be exported — *Ik bevestig deze
verklaringen* — carries no star, because its status is `SIGNATURE_REQUIRED` rather than
`USER_REQUIRED`. Without it every starred field can be filled and the export button
still refuses, disabled, with the reason on the document card and nothing leading from
the button to what would enable it. The address fields lead with a lookup box, so
filling the first control in the field leaves the field the export needs still empty.

Three values were typed twice into different fields within the one task.

**2 — five quantities.** 15 actions and five dialogs: three actions and one window per
quantity, none of which is the number itself.

**3 — fifty rows.** The import itself is cheap — three actions — but it is reachable
only through a dialog; the goods step offers no paste and no file action of its own. Of
the fifty lines, 49 came back **OK** and one **Controle nodig**. That one sits 5,746
pixels down the page, with nothing on screen pointing at it and no filter to bring it
up.

**4 — a substance suggestion.** One recognition question, offered as a floating snackbar
rather than at the line it is about. Closing it with the × stores `dg_dismissed`, so
"not now" is kept as "not this substance", and the line's own dialog then shows no trace
of the suggestion at all: the decision cannot be found again, let alone revised. The
task cannot be completed as written.

**5 — an extra document.** The document choice sits on the export step behind eleven
checkboxes, *after* every document field has been filled in. Ticking one names its
missing field as plain text on the card; the text is not something to click. Reaching
the new question means walking back through the forms by hand — one back-step, three
forms and four step changes for a single answer.

**6 — an error from the final overview.** The export step names eight missing fields in
one line of text, none of it clickable. None of the three main step pills can be clicked
to go back. Correcting it took a **Terug**, re-filling, and walking forward again: 11
actions, four step changes, one back-step.

**7 — an earlier shipment.** Two actions once you are on the shipments list — but the
list itself offers no reuse action at all. Opening the reference is compulsory; **Als
sjabloon gebruiken**, **Openen in wizard**, the JSON export and **Verwijderen** all live
on the detail page.

**8 — a reload during entry.** The wizard was on **Zendinggegevens**; after the reload it
is on **Goederen** with nothing left of the typed description, and nothing warned
beforehand. In the organisation application with the history on, this is entry that
simply disappears.

**9 — five shipments into one trip.** The shipments list has no checkbox and no
multiple selection, so a trip cannot start from the shipments the user is looking at.
On the groupage page each shipment is one action, five in all, on a page reached
separately.

**10 — a refused save.** The entry survives the refusal, which is the important half.
What the user is told is `Error: opslag geweigerd` — the server's sentence with a bare
`Error:` in front of it, and no way to try again from the message.

## What the produced document contained

Task 1's CMR is kept as the content baseline: four pages, carrying all three goods lines
(hoekprofiel, plaat, buis), the consignor, and both places. A later release compares the
same fields rather than the file's bytes — a timestamp differs on every run, and that is
not a difference in the shipment.

## What was not run

The reload of task 8 was measured in the organisation application only. The same reload
in the open application and with the history switched off belongs to release 115, which
is where the promise not to store anything has to be kept, and it will be measured
there. Nothing in this baseline was run on a phone-sized viewport; the mobile
measurements start with release 108, which is the first to change what a phone shows.
