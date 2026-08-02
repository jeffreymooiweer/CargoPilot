# User guide

A walk through CargoPilot, from opening the app to downloading your paperwork. The whole
flow is one wizard; you can go back to any earlier step at any time.

- [1. Pick a transport mode](#1-pick-a-transport-mode)
- [2. Choose your forms](#2-choose-your-forms)
- [3. Enter your packages](#3-enter-your-packages)
- [4. Dangerous goods](#4-dangerous-goods-only-if-needed)
- [5. Shipment details](#5-shipment-details)
- [6. Export](#6-export)
- [The equipment library](#the-equipment-library)
- [Tips](#tips)

## 1. Pick a transport mode

Click **New shipment** and choose how the goods travel: road, rail, sea, inland
waterway, air, or multimodal.

This choice decides which forms are offered, which rulebook applies to any dangerous
goods (ADR for road, RID for rail, IMDG for sea, ADN for inland waterway, IATA DGR for
air), and which kind of locations the route fields suggest. Pick **multimodal** if the
shipment changes mode along the way, or if you simply want every form available.

## 2. Choose your forms

You get the documents that make sense for the mode you picked, with the main transport
document already ticked — CMR for road, CIM for rail, and so on. Tick anything else you
need and untick what you don't.

Forms marked **Official form** are the genuine documents, filled in. The rest are
produced as clean PDFs. See [Documents](documents.md) for the full list.

## 3. Enter your packages

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

### What happens next

CargoPilot reads each line and tries to recognise the material and any dimensions in it,
in Dutch or English. `Steel angle 80x80x8x6000` becomes steel, 80 × 80 × 8 mm, 6000 mm
long. From there it calculates the weight, the material volume and the transport volume.

A green line means it worked. An orange or red line means it could not work out the
weight — usually because the description has no dimensions. Type the weight in yourself
and carry on; nothing blocks you.

You can adjust any weight by hand, and scale the total proportionally from the summary
if you know the real weighbridge figure.

### Dangerous goods on a line

Tick **Dangerous goods** on any package that contains them. CargoPilot also spots UN
numbers written in a description (`UN 1203`) and ticks the box for you. Either way, a
dangerous goods step appears after this one.

## 4. Dangerous goods (only if needed)

Enter the **UN number**, or search by substance name. That is usually all you need to
type.

From that one number CargoPilot works out the proper shipping name, the class and
division, subsidiary risks, packing group, packing instruction, transport category,
tunnel code, Kemler number, limited and excepted quantity limits, the EmS emergency
schedules for sea transport and the air freight rules. Quantities, packaging type and
masses come from the packages you already entered.

**Only empty fields are filled.** Anything you typed yourself stays exactly as you left
it.

Below the form, the **compliance panel** shows live warnings: the ADR 1,000-point
calculation, loading incompatibilities, sea segregation conflicts, the IATA Q value.
Some findings are warnings you can proceed past; a few — an incomplete classification,
or a substance that is not permitted for carriage at all — will block the export until
resolved.

[Dangerous goods](dangerous-goods.md) explains all of it in detail.

## 5. Shipment details

This is where you enter the shipment **once**:

- **Parties** — sender, consignee, carrier
- **Route** — place of loading, place of delivery, terminals
- **References** — order numbers, booking references, customs references

Address fields search real addresses as you type. Route fields suggest airports, ports
or railway stations, filtered to your transport mode. You can always type your own text.

You can also **draw or upload your signature** here, or skip it and sign on paper. Your
signature goes in the sender's box only — carrier and consignee signatures are always
left blank.

After the shared details, each selected form gets its own small step ("Form 3 of 5")
with only the fields that form still needs. A green dot means that form is complete, an
orange dot means something required is still missing. Forms that need nothing extra are
listed as *covered by the shipment details*.

## 6. Export

The final screen lists every selected document with its status:

| Status | Meaning |
|---|---|
| **Ready** | All required fields are filled |
| **Draft** | Exportable, but some optional fields are still empty |
| **Waiting for carrier data** | Fields only the carrier can supply are missing |
| **Blocked** | A safety check failed — see the compliance panel |

Click **Download document** for each one. Every document downloads as a PDF and carries
a draft notice.

> Documents are generated on the spot and deleted from the server the moment your
> download finishes. Nothing is archived.

## The equipment library

Under **Equipment overview** you can keep a library of your own items so they can be
picked from the catalogue while entering packages.

It starts **empty on purpose** — no operational data ships with the app. An
administrator fills it by downloading the template, filling it in and importing it.

## Tips

- **Reference numbers in the description.** Anything the parser does not recognise stays
  in the description and ends up on the document, so notes stay visible.
- **Free text always wins.** Every suggestion box also accepts text you type yourself.
  Nothing forces you into a list.
- **Multimodal for one-offs.** If you need a form that is not offered for your mode,
  start again as multimodal — everything is available there.
- **Working offline?** Packages, weights, UN numbers, ports and airports all work
  without internet. Only address autocomplete needs a connection.
- **Check before you sign.** Every document is a draft. The app is a typing assistant,
  not a safety adviser.
