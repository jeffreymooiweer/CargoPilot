# The shell: one screen instead of four steps of furniture

*A second plan, after [the usability plan](ux-plan.md) was measured to its end. That one
made the work cheaper — 83 actions became 53 and the two impossible tasks became possible.
This one is about where the work **sits**: the frame around it, which is still the frame of
2024 with eleven releases bolted onto it.*

## Where it comes from

A set of mockups, drawn from scratch rather than from the existing screens. They are not
adopted as a design — the colours, the button shapes and the exact wording stay CargoPilot's
— but as a **layout**, and the layout is right in four ways this application is not yet.

## What is already built, and only badly placed

Most of it. This matters, because it decides how much of the plan is risk and how much is
rearrangement:

| In the mockup | In CargoPilot today |
|---|---|
| *Concept • automatisch bewaard* under the title | v1.199.0 — kept as a draft, with an honest saved/saving/failed |
| **Plakken uit Excel** / **Bestand kiezen** on the goods panel | v1.194.0 — the same two, in the panel body |
| A status per goods line (*Gereed* / *Te controleren*) | v1.193.0 — the same two words, in a table column |
| The substance question on the line, with two named answers | v1.195.0 — the same question, three answers |
| Third step called **Controleren** rather than *Export* | v1.199.0 — the export step opens with check-your-answers |
| *1 aandachtspunt* counted where the user can act on it | v1.194.0 — counted above the goods list |
| Shipments with a state and an action per row | v1.200.0 — draft / still to complete / ready, with three actions |

## What is genuinely new

1. **A shell that carries the shipment.** Title, draft status, the three steps and the
   transport mode in one header instead of four stacked strips; a rail with icons; a fixed
   action bar at the foot that never covers a field or an error. Release 118 promised that
   bar and did not build it.
2. **A goods line that opens.** The row carries description, quantity, weight and state; it
   *expands* into everything that is now behind **Details** and, for a dangerous line, into
   the UN number, the proper shipping name and the packing group. The mockup's stepper has
   three steps because the substance is answered where the substance is.
3. **A panel that keeps count.** Lines, weight, attention points and *the documents we are
   preparing*, standing beside the work rather than waiting at the end of it.
4. **A place to come back to.** *Verder waar je gebleven was*, today's counts, a quick start,
   and the recent shipments — the first screen for somebody who is continuing rather than
   starting.

## What is deliberately not taken

**The percentage.** The mockup says *Herkenning 96%*. There is no 96% to print: the
recogniser ranks candidates (an exact UN number, a name the entry starts with, a word that
starts with the text, a substring) and that rank is an order, not a probability. Printing a
number that looks measured and is not is the one thing this project does not do. The banner
stays; it says what matched, not how confident a machine feels.

**The colours and the components.** They stay CargoPilot's, in both themes.

## Two decisions, and why

**The dangerous-goods step stays — and usually will not appear.** The substance's identity
(UN, name, packing group, packing) moves onto the line, where the mockup puts it. What
cannot live on a line stays a step of its own: the compliance assessment, the tunnel
restriction, mixed loading, the equipment list, the 1.1.3.6 exemption calculation. That step
appears when there is something to assess and not otherwise, so the common shipment is the
mockup's three steps and a difficult one is honest about being four.

**The overview gets its own address, and nothing is moved out of the way for it.**
[The usability plan](ux-plan.md) says in as many words: recent shipments as templates
*without sending somebody with a default mode through a dashboard first*. Putting the
overview on `/` would do exactly that — today `/` is the transport-mode chooser, and it
already sends somebody with a preferred mode straight into the wizard without a stop. So:

- **`/` keeps doing what it does.** The chooser with its transport-mode tiles stays, images
  and all, including the ones an installation replaced with its own (v1.172.0), and
  including the redirect that skips it for somebody who always ships the same way.
  **Andere modaliteit kiezen** (`/?choose=1`) still brings the tiles back.
- **The overview lives at `/overzicht`**, first in the rail, for whoever wants to start the
  day there. Nobody is sent through it.
- The transport mode in the wizard's header is a *switcher*, not the chooser: it changes
  the mode of the shipment you are already entering. Choosing where to begin, and changing
  your mind halfway, are two different acts and keep two different places.

## The releases

| # | Release | What it changes |
|---|---|---|
| 119 | The shell | One header (title, draft state, steps, mode), an icon rail, a fixed action bar; the same on a phone |
| 120 | A line that opens | Row expands into details and, for a dangerous line, the substance itself; the DG step appears only where there is something to assess |
| 121 | The panel that counts | Lines, weight, attention, and the documents being prepared, live beside the work |
| 122 | Somewhere to come back to | The overview at `/overzicht`: continue where you left off, today's counts, quick start, recent shipments. Nothing else moves |
| 123 | Measured and trimmed | The ten tasks again, and the mobile measurement the first plan left open |

## How it is judged

The same way as the first plan, with the same harness: [`scripts/ux_bench`](../scripts/ux_bench/README.md)
against the same ten tasks, reported in [the baseline](ux-baseline.md), plus — this time —
a phone-sized viewport, which the first plan recorded as not run. A release that makes a
screen prettier and a task no cheaper is a release that has to say so.
