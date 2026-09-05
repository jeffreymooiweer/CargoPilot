# User guide

A walk through CargoPilot, from opening the app to downloading your paperwork. The whole
flow is one wizard; you can go back to any earlier step at any time.

- [1. Pick a transport mode](#1-pick-a-transport-mode)
- [2. Enter your packages](#2-enter-your-packages)
- [3. Dangerous goods](#3-dangerous-goods-only-if-needed)
- [4. Shipment details](#4-shipment-details)
- [5. Export and your documents](#5-export-and-your-documents)
- [The AI assistant](#the-ai-assistant)
- [The equipment library](#the-equipment-library)
- [Settings](#settings)
- [Language](#language)
- [Tips](#tips)

## 1. Pick a transport mode

Click **New shipment** and choose how the goods travel. **Road, rail, sea and inland
waterway are released**; the air and multimodal tiles are visible but locked — their
regulatory checks are not complete yet, and a half-right document is worse than none.
The [roadmap](../ROADMAP.md) tracks when each one unlocks.

This choice decides which documents are offered, which rulebook applies to any dangerous
goods (ADR for road, RID for rail, IMDG for sea, ADN for inland waterway, IATA DGR for
air), and which kind of locations the route fields suggest.

Always ship the same way? Set a fixed transport mode under [Settings](#settings) and
CargoPilot opens straight into it; *change transport mode* at the top of the wizard brings
the tiles back.

You do not choose forms here. CargoPilot assembles the document set from the shipment
itself and shows the advice on the [export step](#5-export-and-your-documents), where you
can still adjust it.

## 2. Enter your packages

Three ways to get your load in:

**Type it.** Add a line, search the catalogue for the material, or write a free
description. Fill in quantity and unit.

**Paste it.** Click **Import**, paste from Excel or a text file. One line per row:

```
Steel angle 80x80x8x6000 | 8 | pieces
Euro pallet with bricks   | 12 | pallets
```

Columns are separated by a pipe (`|`) or a tab, in the order
`description | quantity | unit`.

**Upload a file.** `.xlsx`, `.csv` or `.txt`. Download the template from the same dialog
if you want the exact layout.

Your file rarely has the template's layout, and it does not have to. CargoPilot reads the
header row and works out which column is which. When it recognises the names it says so;
when it does not, it guesses by position and **tells you it guessed**, in an amber panel
above the text. Each dropdown shows what is actually in that column — `2. Benaming ·
Stalen hoekprofiel 80x80x8x6000` rather than "column 2" — so you can see at a glance
whether it picked the right one.

Two things worth knowing there. A column you do not need can be left unmapped. And if
your file starts with a header row that CargoPilot did not recognise, tick **first row is
a header**, or that row is imported as a piece of cargo.

### What happens next

CargoPilot reads each line and tries to recognise the material and any dimensions in it,
in Dutch, English, German or French. `Steel angle 80x80x8x6000` becomes steel, 80 × 80 × 8 mm,
6000 mm long, and so does `Stahl Winkelprofil 80x80x8x6000`. From there it calculates the weight, the material volume and the transport volume.

A green line means it worked. An orange or red line means it could not work out the
weight — usually because the description has no dimensions. Type the weight in yourself
and carry on; nothing blocks you.

You can adjust any weight by hand, and scale the total proportionally from the summary
if you know the real weighbridge figure.

### Dangerous goods on a line

Tick **Dangerous goods** on any package that contains them. CargoPilot also spots UN
numbers written in a description (`UN 1203`) and ticks the box for you. And it
recognises substances by name: type `petrol` or `benzine` and a small chip offers the
matching UN number — confirm it and the number travels to the dangerous goods step, or
dismiss it and it stays away for that line. Either way, a dangerous goods step appears
after this one.

The contents of one package are read from the sentence too: `1000 jerricans of 25 l of
petrol` fills the net quantity per package and computes the totals, for jerricans,
drums, IBCs and any other counted package alike.

## 3. Dangerous goods (only if needed)

Enter the **UN number**, confirm the chip from the previous step, or search by
substance name. That is usually all you need to type.

From that one number CargoPilot works out the proper shipping name, the class and
division, subsidiary risks, packing group, packing instruction, transport category,
tunnel code, Kemler number, limited and excepted quantity limits, the EmS emergency
schedules for sea transport and the air freight rules. Quantities, packaging type and
masses come from the packages you already entered.

**Only empty fields are filled.** Anything you typed yourself stays exactly as you left
it.

**Only the genuinely open questions are asked.** Everything the tables can supply is
shown as an answer, not a question; what remains is the short list of facts only you
know — how it travels (packages, tank, bulk), which of several official names fits your
product, the kind of packaging (steel 3A1 against plastic 3H1) — each with the reason
it is asked.

Below the form, the **compliance panel** shows live warnings: the ADR 1,000-point
calculation, loading incompatibilities, sea segregation conflicts, the IATA Q value.
Fill in the **net quantity per inner packaging** (with a unit, such as `500 g` or
`0.5 L`) and it also compares your quantities against the limited and excepted quantity
limits of chapters 3.4 and 3.5 — telling you per line whether it falls within or
outside those limits, or that it needs more input. Some findings are warnings you can
proceed past; a few — an incomplete classification, or a substance that is not
permitted for carriage at all — will block the export until resolved.

[Dangerous goods](dangerous-goods.md) explains all of it in detail.

**Say how it travels.** Next to the unit sits a **form**: solid, sheets, bundled, stacked
or loose bulk. It decides how much of a cubic metre is actually material, so 20 m³ of oak
is 14,400 kg as beams and 6,480 kg tipped loose. For gravel, grain and liquids the field
shows a dash — their density already describes them as they travel, and applying a second
factor would count the air twice.

**A profile needs its wall thickness.** An angle profile of 80 × 80 is two legs a few
millimetres thick, not a solid 80 × 80 bar — the difference is a factor of five. So for an
angle profile, a square tube or a round tube a fourth field appears: **wall thickness in
mm**. Leave it empty and the line reports that the thickness is missing rather than
producing a weight; a plate, a beam or a plank does not show the field at all, because
three measurements already describe them.

**A round section needs no height.** For a pipe or a round bar the width column *is* the
diameter and the height field shows a dash: a diameter, a length and — for a pipe — a wall
thickness fix the weight completely.

**The weight recalculates by itself.** There is no recalculate button any more. Change a
quantity, a unit, a form or a dimension and the figures follow shortly after you stop
typing.

**Dimensions belong in their own columns.** Length, width and height are fields on the
line, so a description no longer has to read `balk 200x200x3000` for the measurements to
count. Anything recognised in the description still fills in as a placeholder; what you
type wins. On a phone the three fields sit behind **view more**, with quantity and unit on
the collapsed card.

## 4. Shipment details

This is where you enter the shipment **once**:

- **Parties** — sender, consignee, carrier
- **Route** — place of loading, place of delivery, terminals
- **References** — order numbers, booking references, customs references. Two of them
  come with their conditions in the help text: the **ENS reference (ICS2)** for goods
  entering the EU customs territory (the entry summary declaration is normally lodged by
  the carrier; when its MRN is known, it travels on the papers) and the **AES ITN** for
  exports from the United States (the proof of the Electronic Export Information filing,
  which belongs on the transport document). Both check their format on export, so a
  mistyped reference is caught before it reaches an official form.

The carrier's numbers usually arrive **after** you book — in the confirmation e-mail.
**Paste booking confirmation** at the top of this step reads that e-mail for the
recognisable references (AWB number with its own check digit, booking number, ENS MRN,
AES ITN) and puts them only into fields that are still empty. Nothing you typed is ever
overwritten, and the pasted text is read once and stored nowhere.

Address fields search real addresses as you type. Route fields suggest airports, ports
or railway stations, filtered to your transport mode. You can always type your own text.

You can also **draw or upload your signature** here, or skip it and sign on paper. Your
signature goes in the sender's box only — carrier and consignee signatures are always
left blank.

After the shared details, each selected form gets its own small step ("Form 3 of 5")
with only the fields that form still needs. A green dot means that form is complete, an
orange dot means something required is still missing. Forms that need nothing extra are
listed as *covered by the shipment details*.

Dates that mean "drawn up today" start as today; operational dates (loading, requested
departure) are facts of the trip and are never guessed. The details of your previous
shipment can be brought back with one click, so a regular route is not retyped.

## 5. Export and your documents

The final screen assembles your document set and lists every document with its status.
The **advice** does the choosing for you: the documents the rules require come first
(the dangerous goods transport document for your mode, for instance), the customary
ones are recommended, and everything else the mode offers is there to add. Tick and
untick as you like — the advice is a starting point, not a lock.

| Status | Meaning |
|---|---|
| **Ready** | All required fields are filled |
| **Draft** | Exportable, but some optional fields are still empty |
| **Waiting for carrier data** | Fields only the carrier can supply are missing |
| **Blocked** | A safety check failed — see the compliance panel |

Click **Download document** for each one, or **Download all as ZIP** for one archive
holding every document that is ready — and, when the shipment carries dangerous goods,
the UN cards and the instructions in writing for the journey's regimes as well.
Anything the server has to leave out (an incomplete document, a UN card it does not
hold) is named in a README inside the archive rather than silently missing. Every
document downloads as a PDF and carries a draft notice.

**Mail them instead of downloading.** Where your administrator has set up a mail
server, the same set can be sent straight from this screen: fill in the address, add a
covering note if you want one, and the documents travel as attachments. The message is
written in the language the papers are drawn up in, so a German consignee reads German.

> Documents are generated on the spot and deleted from the server the moment your
> download finishes. Nothing is archived.

### UN cards

If your shipment contains dangerous goods, you can also download the **UN cards** for the
substances you declared — a zip with one datasheet per UN number **per regime** your
journey touches (ADR for road, ADN for inland waterways, IMDG for sea), for your own
records. Only your substances are included, not the whole library, and a regime for
which no card exists is named as missing rather than papered over with another regime's
card. They are not part of the transport documentation.

The card set itself is not bundled with the application: an administrator installs it
once under **Settings → UN Cards**, either straight from the CargoPilot releases or from
an uploaded ZIP (see [un-cards.md](un-cards.md)). Until then the wizard simply says no
cards are available.

## The AI assistant

The AI mark in the wizard header opens the assistant: a small survey that fills the
same wizard through natural language. Describe the shipment — `1000 jerricans of 25 l
of petrol and a pallet of sand-lime brick` — and it becomes goods lines through the
same recognition the lines step uses, one line per item.

From there the assistant asks **one question per screen**, and only questions the app
itself has open: a substance to confirm, an open dangerous goods question, a
measurement the calculation still misses, a document field. Each question is phrased in
plain language; the formal field name and the help with its article references sit
behind the **info mark**. Address questions search real addresses and route questions
suggest airports, ports and stations, exactly like the wizard's own fields. **Previous**
really goes back, optional questions have a **skip**, and a vague answer gets a
follow-up with an example instead of a shrug.

Everything lands in the same wizard state, so you can close the assistant at any point
and continue by hand — or the other way round — without losing anything.

The assistant works without any model installed. An administrator can add a small local
language model under **Settings** which only makes the *reading* more flexible (free
prose, paraphrased answers, measurements written as words); it never decides regulatory
content. See the [README](../README.md#the-ai-assistant-optional) for what it is and
what it costs.

## Groupage: several consignments on one vehicle

Every other screen asks about *one* consignment. The ADR does not look at your
administration, though — it looks at what is physically on the vehicle, and three of its
rules are decided per transport unit no matter how carefully each consignment was filled
in:

- **The 1.1.3.6 points.** Two consignments that each stay under the 1000 can pass it
  together, and the moment they do the whole load needs orange plates, a driver with an
  ADR certificate and the equipment of 8.1.5. This is the case the screen exists for:
  each customer is told "exempt", truthfully, and the vehicle is not.
- **Mixed loading (7.5.2).** Within one consignment this was always checked. Between two
  consignments from different customers, nobody was checking it.
- **The limited-quantities mark (3.4.13/3.4.14).** Both of its conditions are about the
  unit rather than the consignment.

Open **Groupage** in the menu and add the consignments. They come in as the **JSON
exports** the export step writes for each shipment — CargoPilot keeps no shipment
history, so there is no list to pick from, and the file you already have is the input.
Rename them to whatever you call them on the floor: those names appear in the warnings,
so "these two may not travel together" tells you which pallet to take off.

One optional field: the **permitted maximum mass of the transport unit** in tonnes.
Provision 3.4.13 only applies above 12 tonnes, and that is the one fact about the load
the app cannot work out for itself. Leave it empty and the limited-quantities marking is
reported as undecided rather than guessed.

**The trip is not stored.** It exists on the screen and in the request, and reloading
clears it — the same promise the rest of the application keeps about your shipments.

## Shipments: the history, where the installation keeps one

By default CargoPilot keeps no shipments: once the papers are downloaded, the shipment is
gone. An organisation can switch a history on at deploy time (`CARGOPILOT_HISTORY=true`,
see [Configuration](configuration.md#shipment-history)), and then two things appear.

On the export step, a **History** card. Downloading the documents keeps the shipment; the
card's button keeps it before that, and says when it was last kept. A shipment that was
opened from the history keeps its identity, so keeping it again updates the same entry.

In the menu, **Shipments**: the kept shipments with a search over reference and parties,
a transport-mode filter and a date range — a table on a wide screen, cards on a phone.
Opening one shows the record and offers three things: **Open in wizard** puts the whole
shipment back where it was, on the step it was on; **Documents again** renders the same
bundle the export step handed out, on the current version; **Remove** takes it out of the
history after a confirmation. The **Structured export (JSON)** is the same file the
export step offers, and it is what the groupage page accepts.

Who sees which is a matter of **departments**. An administrator sees every kept shipment
and gets a department filter on the page; everyone else sees their own department's
shipments, and someone without a department sees the ones that belong to none. An
installation that never makes a department keeps the plain rule: everyone sees
everything. Administrators make departments and assign people on the **Users** page.

## The equipment library

Under **Equipment overview** you can keep a library of your own items so they can be
picked from the catalogue while entering packages.

It starts **empty on purpose** — no operational data ships with the app. An
administrator fills it by downloading the template, filling it in and importing it.

**Export library** hands the whole list back as a spreadsheet in the very same columns
the import reads, so the file round-trips: it is your backup, the hand-over to a
colleague who maintains the list in Excel, and the seed for a second installation, all
in one. Nothing is exported unless you click — there is no schedule and no copy kept
anywhere.

## Settings

Everything under **Settings** belongs to your account, not to the browser you happen to be
using. Sign in somewhere else and it comes with you.

**Appearance.** Light, dark or follow the system, and the interface language.

**Defaults for a shipment.** If you always ship by the same mode, pick it here and
CargoPilot opens straight into it — the transport-mode tiles are still one click away, via
*change transport mode* at the top of the wizard. You can also set the unit a new package
line starts with.

**My details.** The consignor name and address, a contact, your usual carrier, your loading
point, and the 24-hour emergency number that the IMDG Code and the IATA DGR want on a
dangerous goods declaration. These are the fields that are the same on nearly every
consignment, and they are filled in for you on every form that asks for them — only where
the field is still empty, so nothing you typed yourself is ever overwritten. Switch
*Pre-fill my details* off to keep the details without having them applied.

**Signature.** Draw or upload it once and it is ready on every shipment; you can still
replace or remove it per shipment. It is stored on your own server and nowhere else — see
[Privacy](privacy.md#what-is-stored).

**Two-step verification.** Under *Details* you can protect your account with a second
factor: an authenticator app, which scans a QR code, or a code sent to your e-mail
address — whichever suits you, unless your administrator requires one. Setting it up
gives you eight recovery codes; write them down, because they are shown once and each
works only once. They are what gets you back in when the phone is gone. Switching it off
asks for a code first, and if you chose the e-mail method you can have one sent to you
at that moment.

**Forgotten your password?** The sign-in screen has a link. You get a mail with a link
that works once and expires after an hour, and after choosing a new password you are
signed in straight away rather than sent back to the sign-in screen. Both need a mail
server; without one, ask your administrator to set a new password for you.

### After an update

When your administrator pulls a newer CargoPilot image, the first sign-in afterwards shows
a **what's new** card with the release notes between the version you last used and the one
now running. Close it and it will not return until the next update; the card follows your
account, so a second device does not show the same notes twice. The notes themselves are
the project's own changelog entries and are in English; a first sign-in on a fresh account
shows no card at all.

### For administrators

Administrators see two more tabs. **Administration** holds the settings that apply to
the whole installation and are saved together: the language and theme new users start
with, the organisation name and address offered as a consignor to anyone who has not
filled in their own, whether the UN card download is offered, how long a session lasts,
and — under **Outbound connections** — whether address lookup, catalogue sync and the
update check are allowed to reach the internet at all. It also holds the **mail server**,
with a test message to prove it works before anyone depends on it, the **web address**
the application is reached on (which the links in those mails use), and the **two-step
verification policy**: off, required for administrators, or required for everyone. See
[Configuration](configuration.md#mail-server) for the settings themselves. Under
**Branding** the installation gets its own face: a name for the header, the sign-in page
and the browser tab, a logo shown in its own colours in both themes and carried in
outgoing mail, and a picture per transport mode for the tiles on the first screen. The
pictures apply the moment they are uploaded and each has a way back to the default; the
name is saved with the button. See [Configuration](configuration.md#branding) for the
formats and sizes accepted.

**Users.** A separate page lists the accounts, where an administrator adds one, changes
a role, deactivates or removes an account, sets a new password, and clears somebody's
two-step verification when they have lost both their phone and their recovery codes. A
new account can be invited by mail instead of being handed a password: the colleague
gets a link, valid for seven days and usable once, and chooses their own password. The
invitation says an administrator made the account without naming which one. On an
installation that keeps its shipments the same page holds **Departments**: make one,
rename it, remove it — its people and shipments then belong to none rather than
disappearing — and pick a department per user beside their role. **Maintenance** holds the things
an administrator *does* rather than saves: updating, the **UN Cards** section where the
card set is installed, checked for updates or removed (see [un-cards.md](un-cards.md)),
and the assistant's optional local model. When the update check is on and a newer
release exists, administrators get a small dismissible note in the
corner. The **Updating** panel carries a **check now** button and,
where the operator has deliberately enabled it (Docker socket plus
`UPDATE_APPLY_ENABLED`, see
[Configuration](configuration.md#updating-from-inside-the-application)), an **update
and restart** button that pulls the new release and swaps the container — the brief
restart is the update happening, and a failed attempt puts the previous version back.
Without that opt-in the section explains the manual route: pulling the newer image and
restarting the container, by hand, with Docker Compose, via Watchtower or from Unraid's
Docker tab. See
[Configuration](configuration.md#two-places-and-which-one-wins) for how these relate to the
environment variables.

## Language

Under **Settings** you pick Dutch, English, German or French. That choice runs all the way
through: the screens, the field labels, the dangerous goods help, the compliance warnings,
the error messages and the documents you download.

One thing follows the regulations rather than your choice. The proper shipping name of a
dangerous substance is prescribed per mode: a German CMR or CIM may carry the German name
from ADR Table A, but a sea or air document must be in English (IMDG 5.4.1.4.1, IATA DGR
8.1.2.1). CargoPilot puts the right one on each document and tells you when it did.
See [Dangerous goods](dangerous-goods.md#what-one-un-number-gives-you).

## Tips

- **Reference numbers in the description.** Anything the parser does not recognise stays
  in the description and ends up on the document, so notes stay visible.
- **Free text always wins.** Every suggestion box also accepts text you type yourself.
  Nothing forces you into a list.
- **Missing a document?** The advice on the export step preselects what the shipment
  needs, but everything the mode offers can be ticked there as well.
- **Working offline?** Packages, weights, UN numbers, ports and airports all work
  without internet. Only address autocomplete needs a connection.
- **Check before you sign.** Every document is a draft. The app is a typing assistant,
  not a safety adviser.
