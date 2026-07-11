# Roadmap

Versiebeleid: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH` (zie `VERSION` en git-tags `v*`).

## v1.0.0 (huidige release)

- Appendix A1-wizard met catalogus, DG-stap en Excel-export
- Lege materieelbibliotheek; import via template door de beheerder
- Geen operationele materieeldata in GitHub of Docker-images

## Gepland

### v1.1 — Multimodale transportkeuze

- Keuze transportmodus per zending of per positie (weg, lucht, zee, spoor waar relevant)
- Formulieren en export per modus, naast bestaande appendix-flow

| Modus | Richting | Voorbeeldformulieren / standaarden |
|-------|----------|-------------------------------------|
| Weg | CMR, eventueel nationaal vrachtbrief | CMR-vrachtbriefvelden |
| Lucht | IATA / luchtvracht | AWB, SHC, gevaarlijke-goederen-declaratie lucht |
| Zee | Bill of lading / zeevracht | BL-achtige metadata (later uitwerken) |

- Validatie en helpteksten per formulierset
- Template-download per transportmodus (zoals materieel-import nu)

### v1.2 — Wizard & bibliotheek

- Kolommapping-UI bij ambigue Excel-headers
- Optionele bulk-export materieel (alleen op verzoek; geen standaard-export van gevoelige data)
- Duitse UI-taal

### Later (ideeën)

- Watchtower/Unraid auto-update documentatie in README
- Meerdere appendix-templates per klant/organisatie
- Auditlog zonder inhoud van materiaallijsten (alleen metadata)

## Niet gepland

- Server-side opslag van appendix-inhoud of export-historie (privacy-by-design blijft leidend)
- Voorgevulde operationele materieelbibliotheek in de openbare repository of Docker Hub
