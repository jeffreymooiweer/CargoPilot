# Changelog

Alle noemenswaardige wijzigingen worden gedocumenteerd volgens [Semantic Versioning](https://semver.org/).

## [1.1.0] — 2026-07-12

Multimodale transportkeuze.

### Toegevoegd

- **Modaliteitskeuze bij start**: tegelscherm met wegtransport, spoor, zeevracht, binnenvaart, luchtvracht en multimodaal (aparte illustraties voor licht en donker thema)
- **Formulierenselectie als eerste wizardstap**: per modaliteit alleen relevante formulieren; bij multimodaal alle formulieren selecteerbaar
- **Documentregister** (`backend/app/config/document_registry.json`) met velddefinities en veldstatussen (`USER_REQUIRED`, `CONDITIONAL`, `CARRIER_PROVIDED`, `OPERATIONAL`, `SIGNATURE_REQUIRED`, …)
- **Officiële PDF-formulieren ingevuld**: de **CMR-vrachtbrief** (IRU-model 2007, 4 doorslagen) en de **IATA Shipper's Declaration** (open formaat) worden nu als originele, invulbare PDF-templates ingevuld en als PDF gedownload — inclusief correcte vaknummering, IATA-kolomvolgorde en "delete non-applicable"-doorstreping. Handtekeningvelden blijven leeg.
- **Nieuwe documenten**: CMR-vrachtbrief (PDF), IATA Shipper's Declaration (PDF), CIM-vrachtbrief (spoor), IMO Multimodal Dangerous Goods Form, VGM-verklaring (SOLAS, methode 1/2 met somcontrole), AWB Shipping Instructions, B/L / Sea Waybill Shipping Instructions, ADR/ADN-vervoersdocument, paklijst en afleverbon
- **Juridische disclaimer**: aparte disclaimer-pagina in de app (NL/EN), `DISCLAIMER.md`, een concept-waarschuwing bij export en een disclaimer in de metadata/voettekst van gegenereerde documenten. Aansprakelijkheid volledig uitgesloten; Apache License 2.0 met Commons Clause expliciet benoemd.
- Officiële regelgeving en vaste juridische teksten (CMR-paramountclausule, IATA-certificering/WARNING, IMO-verklaring, VGM SOLAS-referentie, ADR 5.4.1-omschrijvingsregel) plus links naar de officiële brontemplates per document
- **Zendinggegevens-stap**: gedeelde blokken (partijen, route, referenties) worden één keer ingevuld en hergebruikt in alle geselecteerde documenten
- **Documentstatussen in de samenvatting**: gereed voor export, concept, wacht op carriergegevens, geblokkeerd door veiligheidsvalidatie, niet van toepassing
- **Gevaarlijke-stoffenvalidatie per modaliteit** (ADR/RID/ADN/IMDG/IATA DGR): export van DG-verklaringen wordt geblokkeerd bij onvolledige classificatie (UN-nummer, Proper Shipping Name, klasse; voor IATA ook packing instruction, colli en hoeveelheid)
- Extra DG-velden bij IMO/IATA-formulieren: technische naam, marine pollutant, Cargo Aircraft Only, overpack, noodcontact, EmS-code
- Nieuwe API-endpoints: `GET /api/documents/registry`, `POST /api/documents/validate`, `POST /api/documents/export`

### Gewijzigd

- Wizard start met formulierenkeuze; appendix-vragen verschijnen alleen als Appendix A1/D is geselecteerd
- Handtekening-, carrier- en operationele velden worden nooit vooraf ingevuld; ze worden in de export als zodanig gemarkeerd
- Navigatie: "Nieuwe appendix" heet nu "Nieuwe zending" en start bij de modaliteitskeuze

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
