<div align="center">

# CargoPilot

**Turn a list of packages into finished transport documents.**

Paste your load, and CargoPilot works out the weights and volumes, fills in the official
CMR, CIM, AVC and IATA forms, and checks your dangerous goods before you print.

[![Docker Pulls](https://img.shields.io/docker/pulls/jeffersonmouze/cargopilot?logo=docker&logoColor=white&label=docker%20pulls&color=2496ED)](https://hub.docker.com/r/jeffersonmouze/cargopilot)
[![Latest release](https://img.shields.io/github/v/release/jeffreymooiweer/CargoPilot?logo=github&label=release&color=2ea44f)](https://github.com/jeffreymooiweer/CargoPilot/releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/jeffreymooiweer/CargoPilot/ci.yml?branch=main&logo=githubactions&logoColor=white&label=build)](https://github.com/jeffreymooiweer/CargoPilot/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-under%20development-orange)](ROADMAP.md)
[![Licence](https://img.shields.io/badge/licence-Apache--2.0%20%2B%20Commons%20Clause-blue)](LICENSE)

[![Docker image size](https://img.shields.io/docker/image-size/jeffersonmouze/cargopilot/latest?logo=docker&logoColor=white&label=image%20size&color=2496ED)](https://hub.docker.com/r/jeffersonmouze/cargopilot)
[![Backend](https://img.shields.io/badge/backend-FastAPI%20%C2%B7%20Python%203.12-009688?logo=fastapi&logoColor=white)](docs/development.md)
[![Frontend](https://img.shields.io/badge/frontend-React%2018%20%C2%B7%20TypeScript-61DAFB?logo=react&logoColor=black)](docs/development.md)
[![Unraid](https://img.shields.io/badge/Unraid-ready-F15A2C?logo=unraid&logoColor=white)](docs/getting-started.md#unraid)
[![Interface](https://img.shields.io/badge/interface-NL%20%C2%B7%20EN%20%C2%B7%20DE-lightgrey)](#)
[![Self-hosted](https://img.shields.io/badge/self--hosted-your%20data%20stays%20yours-6f42c1)](docs/privacy.md)

</div>

---

> [!WARNING]
> **CargoPilot is under active development.** Every document it produces is a **draft**.
> Check it, complete it and have it signed by a qualified person before you use it.
> See the [disclaimer](DISCLAIMER.md).

## What is CargoPilot?

Preparing freight paperwork is repetitive. The same addresses, the same reference
numbers, the same weights — typed again into every form, each with its own layout and
its own rules. Get a box number wrong on a dangerous goods declaration and the shipment
stops at the gate.

CargoPilot does that part for you. You enter your shipment once. It recognises what you
are shipping, calculates the weights and volumes, and fills in the paperwork for the
transport mode you picked — road, rail, sea, inland waterway, air, or a combination.

It runs on your own machine or server. Nothing is sent to a cloud service, and no
shipment history is kept.

## What it does

**Understands your load.** Paste a list, or import an Excel or CSV file. CargoPilot
recognises materials and dimensions in Dutch, English and German — `Steel angle 80x80x8x6000` —
and works out the weight from a built-in database of **400 goods**, from cement and
timber to grain, chemicals and white goods. Anything it cannot work out, you can correct
by hand.

**Fills in the real forms.** The CMR, CIM, AVC and IATA declarations are the genuine
official documents, filled in — not lookalikes drawn from scratch. Everything else is
produced as a clean PDF.

**Asks each question once.** Sender, consignee, route and references are entered a
single time and reused across every form you selected. After that you only see the
fields a given form still needs.

**Knows its way around dangerous goods.** Type a UN number and CargoPilot works out the
proper shipping name, class and division, subsidiary risks, packing group, transport
category, tunnel code, EmS emergency schedules and the air freight rules. It warns you
about incompatible loads, calculates the ADR 1,000-point exemption and the IATA Q value,
and refuses to export a declaration that is not complete.

**Hands you the paperwork for your own file.** Alongside the transport documents, a
shipment with dangerous goods can download the UN reference cards for exactly the
substances it declared.

**Finds addresses and terminals for you.** Address autocomplete plus 4,500+ airports,
17,500+ ports and 750+ European railway stations, filtered to the transport mode you
chose.

**Speaks Dutch, English and German**, in light or dark mode. The interface, the field labels, the dangerous goods guidance and the generated documents all follow the language you pick.

## Try it in two minutes

```bash
git clone https://github.com/jeffreymooiweer/CargoPilot.git
cd CargoPilot
cp .env.example .env          # set ADMIN_PASSWORD; the rest has defaults
docker compose up -d --build
```

Open <http://localhost:8080> and log in with the admin account from your `.env`.

Running Unraid, or want the full set of options? See **[Getting started](docs/getting-started.md)**.

## Documentation

| Guide | What's in it |
|---|---|
| **[Getting started](docs/getting-started.md)** | Install with Docker Compose or on Unraid, create the first admin account |
| **[User guide](docs/user-guide.md)** | A walk through the app, from picking a transport mode to downloading your documents |
| **[Documents](docs/documents.md)** | Every document CargoPilot produces, and which ones are official forms |
| **[Dangerous goods](docs/dangerous-goods.md)** | What CargoPilot fills in automatically, and which checks it runs |
| **[DG coverage](docs/dg-coverage.md)** | Per mode: what is checked, what is not, and which gaps matter most |
| **[Configuration](docs/configuration.md)** | Environment variables and settings |
| **[Data sources](docs/data-sources.md)** | Where the goods, location and regulatory data comes from |
| **[Privacy](docs/privacy.md)** | What is stored, and what is deliberately not |
| **[Development](docs/development.md)** | Running from source, tests, versioning, releases |

Also: **[Changelog](CHANGELOG.md)** · **[Roadmap](ROADMAP.md)** · **[Disclaimer](DISCLAIMER.md)**

## Found something wrong?

CargoPilot is only worth as much as its data, and a wrong density or a misplaced box on a
form is best spotted by someone actually shipping. Those reports are the most valuable
ones this project gets — please
[open an issue](https://github.com/jeffreymooiweer/CargoPilot/issues/new/choose).

It is a personal project, so code contributions work a little differently: ask first, in
an issue. [CONTRIBUTING.md](CONTRIBUTING.md) explains why and what a useful report looks
like. Security problems go through
[private reporting](SECURITY.md) rather than a public issue.

## Good to know

CargoPilot is a **civilian** tool. It prepares paperwork; it does not give legal,
customs or safety advice, and it does not replace a dangerous goods safety adviser
(DGSA). The current edition of ADR, RID, ADN, the IMDG Code and the IATA DGR is always
the authority — not this app.

Carrier fields, operational fields and signatures are never filled in for you. Your
signature is only added if you draw or upload one yourself.

## Licence

Apache License 2.0 with the Commons Clause — see [LICENSE](LICENSE).

You may use CargoPilot inside your own organisation. Selling it, reselling it, hosting
it as a paid service or otherwise commercially redistributing the software itself
requires written permission from the copyright holder.
