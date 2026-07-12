# Roadmap

Versiebeleid: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH` (zie `VERSION` en git-tags `v*`).

## v1.1.0 (huidige release) — Multimodale transportkeuze

- Modaliteitskeuze bij start (weg, spoor, zee, binnenvaart, lucht, multimodaal)
- Formulierenselectie per modaliteit als eerste wizardstap
- Documentregister met veldstatussen (gebruiker/vervoerder/operationeel/handtekening)
- CMR, CIM, IMO DGF, IATA DGD, VGM, AWB- en B/L-shipping-instructions, ADR/ADN-document, paklijst, afleverbon
- Gedeelde zendinggegevens hergebruikt over documenten; DG-exportblokkades per modaliteitsprofiel

## v1.0.0

- Appendix A1-wizard met catalogus, DG-stap en Excel-export
- Lege materieelbibliotheek; import via template door de beheerder
- Geen operationele materieeldata in GitHub of Docker-images

## Gepland

### v1.1.x — Verdieping multimodaal

- NHM-code zoeken/selecteren als masterdataveld (CIM vak 24)
- Configureerbare landen-/carrierregels voor douanereferenties (ENS/ICS2, AES/ITN)
- Import van carriergegevens (AWB-nummer, boeking) na bevestiging

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
