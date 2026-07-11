# Changelog

Alle noemenswaardige wijzigingen worden gedocumenteerd volgens [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-07-11

Eerste stabiele release.

### Toegevoegd

- Wizard: review-first flow met materiaalcatalogus, synoniemen en appendix-vragen
- Appendix A1-export op basis van het officiële Excel-template
- Appendix D (gevaarlijke stoffen) met ADR UN-lookup
- Overzicht materieel: beheer, import via template (.xlsx/.csv/.txt)
- Wizard-import: plakken en bestand uploaden met template
- Gewicht per regel bewerkbaar; totaalgewicht proportioneel schaalbaar in samenvatting
- Automatische catalogus-sync (materialen, profielen) uit openbare bronnen
- Donkere modus, NL/EN UI, Docker/Unraid-deploy

### Gewijzigd

- Semantische versies vanaf v1.0.0 (`VERSION`, Docker-tags `v*`, health-endpoint)
- Materieelbibliotheek start **leeg**; geen voorgevulde operationele data meer in de repository of image

### Verwijderd / privacy

- Vooraf gevulde materieellijst (`equipment_overview.json`) uit codebase en Docker-build
- Bij opstarten worden legacy-items met bron `overzicht_materieel` uit bestaande databases verwijderd
- Verouderde gebouwde frontend-static in `backend/static/` (build gebeurt in Docker)

### Bekende beperkingen (roadmap)

- Eén transportmodus (weg/appendix); multimodaal (IATA, CMR, …) volgt in een latere minor release
