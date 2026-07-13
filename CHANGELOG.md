# Changelog

Alle noemenswaardige wijzigingen worden gedocumenteerd volgens [Semantic Versioning](https://semver.org/).

## [1.3.0] — 2026-07-13

Nalevingsbegeleiding gevaarlijke stoffen (ADR & IATA).

### Toegevoegd

- **ADR 1.1.3.6 puntencalculator (1000-puntenregel)**: per DG-product transportcategorie (0-4) en totale hoeveelheid; automatische berekening met factoren ×50/×3/×1/×0, statussen "vrijstelling mogelijk", "boven 1000 punten", "categorie 0 — geen vrijstelling" en "onvolledig", inclusief uitleg wat onder de vrijstelling vervalt en wat verplicht blijft
- **Samenladingscontrole ADR 7.5.2**: waarschuwing bij klasse 1 (behalve 1.4S) samen met andere klassen, verschillende compatibiliteitsgroepen binnen klasse 1 (7.5.2.2) en CV28/7.5.4-scheiding van levensmiddelen (etiketten 6.1/6.2 en klasse 9 UN 2212/2315/2590/3151/3152/3245)
- **IATA-segregatie (Table 9.3.A)**: controle op onverenigbare colli (klasse 1 excl. 1.4S × 2.1/3/4.1/5.1; klasse 8 × 4.3) inclusief nevengevaren, plus de lithiumbatterij-regel (UN 3090/3480 gescheiden van 1/2.1/3/4.1/5.1)
- **IATA Q-waarde (5.0.2.11)**: automatische berekening Q = Σ n/M met afronding naar boven op één decimaal en waarschuwing bij overschrijding van 1,0
- **Nalevingspaneel** in de gevaarlijke-stoffenstap en de exportsamenvatting, met bronvermeldingen (ADR 2025, IATA DGR 67e editie) en herbereken-knop
- Nieuwe DG-velden met helpteksten: ADR-transportcategorie, totale hoeveelheid (1.1.3.6.3-eenheden), netto per verpakking en max. netto per verpakking (Q); UN-lookup vult de transportcategorie voor waar de ADR-database die levert
- Cargo Aircraft Only-signalering richting Shipper's Declaration en AWB-handling information
- Nieuw endpoint: `POST /api/dg/compliance`; regelconfiguratie in `backend/app/config/dg_compliance.json`

## [1.2.0] — 2026-07-12

Multimodale transportkeuze.

### Toegevoegd

- **Modaliteitskeuze bij start**: tegelscherm met wegtransport, spoor, zeevracht, binnenvaart, luchtvracht en multimodaal (aparte illustraties voor licht en donker thema)
- **Formulierenselectie als eerste wizardstap**: per modaliteit alleen relevante formulieren; bij multimodaal alle formulieren selecteerbaar
- **Documentregister** (`backend/app/config/document_registry.json`) met velddefinities en veldstatussen (`USER_REQUIRED`, `CONDITIONAL`, `CARRIER_PROVIDED`, `OPERATIONAL`, `SIGNATURE_REQUIRED`, …)
- **Alle documenten worden nu als PDF gedownload.**
- **Officiële invulbare PDF-formulieren ingevuld**: de **CMR-vrachtbrief** (IRU-model 2007, 4 doorslagen), de **IATA Shipper's Declaration** (open formaat) en de **CIM-vrachtbrief** (CIT CIM/CUV, ed. 2019) worden als originele, invulbare PDF-templates ingevuld — inclusief correcte vaknummering, IATA-kolomvolgorde en "delete non-applicable"-doorstreping. Handtekeningvelden blijven leeg.
- **Zelf-ontworpen documenten als nette PDF** (reportlab): paklijst, afleverbon, IMO Multimodal Dangerous Goods Form, VGM-verklaring, AWB/B-L Shipping Instructions en ADR/ADN-vervoersdocument — met partijen, goederentabel, DG-tabel per profiel, vaste juridische teksten en disclaimer.
- **intern formulier**: xlsx bevat nu alleen de relevante tabbladen **A1** en **D** (Invulinstructie en Overzicht Materieel verwijderd); daarnaast een **PDF-weergave** (liggend) van de A1-regeltabel met vlaggen en de D-tabel.
- **Nieuwe documenten**: CMR (PDF), IATA (PDF), CIM (PDF), IMO Multimodal DG Form, VGM-verklaring (methode 1/2 met somcontrole), AWB Shipping Instructions, B/L / Sea Waybill Shipping Instructions, ADR/ADN-vervoersdocument, paklijst en afleverbon
- **Juridische disclaimer**: aparte disclaimer-pagina in de app (NL/EN), `DISCLAIMER.md`, een concept-waarschuwing bij export en een disclaimer in de metadata/voettekst van gegenereerde documenten. Aansprakelijkheid volledig uitgesloten; Apache License 2.0 met Commons Clause expliciet benoemd.
- Officiële regelgeving en vaste juridische teksten (CMR-paramountclausule, IATA-certificering/WARNING, IMO-verklaring, VGM SOLAS-referentie, ADR 5.4.1-omschrijvingsregel) plus links naar de officiële brontemplates per document
- **Zendinggegevens-stap**: gedeelde blokken (partijen, route, referenties) worden één keer ingevuld en hergebruikt in alle geselecteerde documenten
- **Documentstatussen in de samenvatting**: gereed voor export, concept, wacht op carriergegevens, geblokkeerd door veiligheidsvalidatie, niet van toepassing
- **Gevaarlijke-stoffenvalidatie per modaliteit** (ADR/RID/ADN/IMDG/IATA DGR): export van DG-verklaringen wordt geblokkeerd bij onvolledige classificatie (UN-nummer, Proper Shipping Name, klasse; voor IATA ook packing instruction, colli en hoeveelheid)
- Extra DG-velden bij IMO/IATA-formulieren: technische naam, marine pollutant, Cargo Aircraft Only, overpack, noodcontact, EmS-code
- Nieuwe API-endpoints: `GET /api/documents/registry`, `POST /api/documents/validate`, `POST /api/documents/export`

### Gewijzigd

- Wizard start met formulierenkeuze; appendix-vragen verschijnen alleen als intern formulier is geselecteerd
- Handtekening-, carrier- en operationele velden worden nooit vooraf ingevuld; ze worden in de export als zodanig gemarkeerd
- Navigatie: "Nieuwe appendix" heet nu "Nieuwe zending" en start bij de modaliteitskeuze
- Wizard-voortgangsbalk toont op mobiel iconen i.p.v. tekst (meer stappen passen op het scherm)

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

### Bekende beperkingen (opgelost in v1.1.0)

- Alleen appendix/weg-flow; multimodaal volgde in v1.1.0
