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

## What the releases have changed since

Each release of the plan reruns the tasks it touches. The numbers below are from the
same harness against the same tasks, so a row is comparable with the baseline above.

| Release | Task | Actions | Windows | Note |
|---|---|---|---|---|
| 108 (v1.193.0) | 1 A simple shipment | 26 → **20** | 3 → **0** | The line dialog is no longer on the way to a shipment |
| 108 (v1.193.0) | 2 Five quantities | 15 → **5** | 5 → **0** | One keystroke per quantity, and nothing opens |
| 108 (v1.193.0) | 4 A substance suggestion | 8 → **5** | 2 → **1** | Reaching the line to look again costs less; the finding itself stands |
| 108 (v1.193.0) | 8 A reload during entry | 5 → **3** | 1 → **0** | Only the cost of getting there; the entry is still lost |
| 109 (v1.194.0) | 3 Fifty rows imported | 3 → **4** | 1 → **0** | No dialog, and the fourth action is the one that was impossible: narrowing to the row that wants attention |
| 110 (v1.195.0) | 4 A substance suggestion | 8 → **5** | 2 → **0** | And **completable**: the answer can be found again and changed |
| 111 (v1.196.0) | 5 An extra document | 7 → **4** | 0 → **0** | The missing field is named as a button; three forms crossed became two |
| 111 (v1.196.0) | 6 An error from the overview | 11 → **3** | 0 → **0** | Press the field's name, type the answer, come back |
| 112 (v1.197.0) | 1 A simple shipment | 20 → **19** | 0 → **0** | The details step is one page of groups: two forms crossed became one |
| 112 (v1.197.0) | 5 An extra document | 4 → **4** | 0 → **0** | Same four actions, but the extra document adds no form of its own |
| 113 (v1.198.0) | 5 An extra document | 4 → **5** | 0 → **0** | The choice moved to before the fields; coming back to it from a finished shipment is the fifth action |

Task 3 is the one row in this table where the action count went *up*, and it is the
release's point rather than a regression. Pasting fifty rows costs the same three actions
it always did and no longer opens a window; the fourth is the button that narrows the
fifty lines to the one that needs looking at — which in the baseline could only be found
by scrolling 5,746 pixels. The lines themselves still come back as 49 **OK** and one
**Controle nodig**, and that one now says why: *no dimensions in the description and no
weight filled in*.

Task 4 is the one the baseline could not complete. The question is now on its line with
three named answers, the line says which was given, and **Change the answer** takes it
back — so "close it, judge it, revise it later" is a thing that can actually be done.

Tasks 5 and 6 are the two the baseline measured as walking: the export step named what
was missing in one line of plain text, and reaching any of it meant **Terug**, finding
the form, finding the field, and walking forward again. Each name is now a button that
opens the step, the form and the field it belongs to, puts the cursor in it, and offers
the way straight back. Task 6's eleven actions bought a whole form crossed a second
time; its three buy the one correction the task is about. The step changes and the one
back-step stay what they were — going to a field on an earlier step *is* going back —
but the forms crossed on the way fell from two to none.

The same release made **Next** say what is still empty before it walks on, which costs a
second press on a form left deliberately empty. Nothing is blocked: the second press
carries on under its own label, and the export step keeps saying what is missing. Task 1
measured unchanged at 20 actions, so the telling costs nothing when the fields are
filled.

Release 112 turned the details step from a form per document into one page of three
groups — the parties, the route, the additions — so the *forms* column is the one that
moved: task 1 crossed two and now crosses one, and task 5's extra document, which used to
bring a form with it, brings none. What the column does not show is the duplication that
went with it. The answers are one map keyed by field key, so a document asking for
`container_number` was re-asking what an earlier form had already asked, under its own box
number. Counted straight from the registry, a sea shipment of an IMO declaration, a bill of
lading instruction, a VGM and a packing list put **68** questions across its forms; the same
shipment now asks **62**, each once. Road with a packing list and a delivery note goes from
39 to 37, air from 43 to 40. Where two documents want the same answer the form says so
underneath it — *also asked by: Delivery note (Date)* — rather than asking again.

Release 113 moved the document choice from the export step, where the baseline found it
*behind eleven checkboxes, after every document field has been filled in*, to the step
that asks its questions. Task 5 is the second row in this table where the number went up,
and for a plain reason: the task starts from a finished shipment and now has to walk back
to a choice that, in the ordinary order, is made before the fields. Measured on the same
harness, choosing a document **in place** — standing on the step it belongs to, ticking
it, following *to those questions* and answering the first — costs **3 actions and no step
change at all**. The fifth action of task 5 is the way back, not the choosing.

What the run also showed is the answer the app can now give to *and what do I have to fill
in?* Ticking the delivery note said it added five questions and put the cursor in the first
of them; ticking the packing list after it said, correctly, that it adds none — everything
it needs was already being asked.

Tasks 7, 9 and 10 were unchanged by 108 to 113.

## What was not run

The reload of task 8 was measured in the organisation application only. The same reload
in the open application and with the history switched off belongs to release 115, which
is where the promise not to store anything has to be kept, and it will be measured
there. Nothing in this baseline was run on a phone-sized viewport; the mobile
measurements start with release 108, which is the first to change what a phone shows.
