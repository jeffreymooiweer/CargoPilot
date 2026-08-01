# Changelog

Alle noemenswaardige wijzigingen worden gedocumenteerd volgens [Semantic Versioning](https://semver.org/).

## [1.10.0] — 2026-08-01

Segregatie geverifieerd tegen de officiële IMDG-code en uitgebreid met scheidingsgroepen en klasse 1.

### Gewijzigd

- **Segregatietabel geverifieerd en bijgewerkt naar Amendement 40-20.** De tabel is regel voor regel vergeleken met hoofdstuk 7.2 van de officiële IMDG-code. 287 van de 289 cellen bleken al correct; vier cellen zijn bijgewerkt omdat Amendement 40-20 strenger is dan de oudere uitgave waar de eerdere versie op leunde:
  - klasse 2.1 × 4.3: van "geen algemene scheiding" naar **2 (gescheiden van)**
  - klasse 3 × 4.3: van 1 (uit de buurt van) naar **2 (gescheiden van)**
  - klasse 2.2 × 5.2: van 2 naar **1 (uit de buurt van)**
  De tabel is nu woordelijk vastgelegd in een test, zodat een toekomstige wijziging niet ongemerkt kan sluipen.

### Toegevoegd

- **Scheidingsgroepen (IMDG 7.2.5)**: alle negentien groepen SGG1 t/m SGG18 (zuren, sterke zuren, ammoniumverbindingen, bromaten, chloraten, chlorieten, cyaniden, zware metalen, hypochlorieten, lood, gehalogeneerde koolwaterstoffen, kwik, nitrieten, perchloraten, permanganaten, metaalpoeders, peroxiden, aziden en alkaliën) zijn opgenomen als naslag in het nalevingspaneel, met de uitleg dat kolom 16b van de Dangerous Goods List bepaalt of een stof erin valt en dat de afzender dat bij n.e.g.-vermeldingen zelf beoordeelt (5.4.1.5.11).
- **Uitzondering voor klasse 8 (IMDG 7.2.6.5)**: zuren en alkaliën van verpakkingsgroep II of III mogen tóch samen in één laadeenheid bij verpakkingen tot 30 L of 30 kg, mits de stoffen niet gevaarlijk reageren en het vervoersdocument de verklaring van 5.4.1.5.11.3 bevat.
- **Samenladingscontrole voor explosieven (IMDG 7.2.7.1.4)**: de volledige matrix van compatibiliteitsgroepen A t/m S bepaalt nu of colli van klasse 1 in dezelfde ruimte of laadeenheid mogen. Groep S is verenigbaar met alles behalve L; groep L uitsluitend met hetzelfde type; de bijzondere bepalingen voor de groepen G (vuurwerk), L en N worden als waarschuwing getoond. Ook de uitzondering van 7.2.7.2.1 (ammoniumnitraat en nitraten samen met springstoffen, behalve UN 0083) is opgenomen.
- **Nevengevaar klasse 1 telt als divisie 1.3** bij het bepalen van de scheiding (IMDG 7.2.3.3), wat strenger uitpakt dan het hoofdgevaar alleen.

## [1.9.0] — 2026-08-01

EmS-database uitgebreid en vervoersverboden gesignaleerd.

### Toegevoegd

- **EmS-noodschema's uitgebreid van circa 90 naar 305 UN-nummers** in een eigen gegevensbestand (`backend/seed/dg/ems.json`), gegroepeerd per gevarenprofiel: brandbare, giftige, oxiderende en inerte gassen, brandbare vloeistoffen (met onderscheid tussen stoffen die op water drijven en overige), brandbare en zelfontbrandende vaste stoffen, met water reagerende stoffen, oxiderende stoffen en ammoniumnitraat, organische peroxiden, giftige en infectueuze stoffen, radioactieve stoffen, bijtende stoffen (ook de bijtend-én-oxiderende combinaties), milieugevaarlijke stoffen en lithiumbatterijen. Bij elke vermelding wordt het profiel getoond ("Brandbare vloeistof die op water drijft"), zodat zichtbaar is waaróm dat schema geldt.
- **Vervoersverbod-signalering**: veertien stoffen die ADR Tabel A niet ten vervoer toelaat (o.a. UN 1798 koningswater, UN 2249 symmetrisch dichloordimethylether, UN 2186 waterstofchloride sterk gekoeld en enkele n.e.g.-vermeldingen met onverenigbare gevaren) worden herkend. De gevaarlijke-stoffenstap toont een rode blokkade en de export van vervoersdocumenten wordt geweigerd; vervoer is alleen mogelijk onder ontheffing van de bevoegde autoriteit.
- Toelichting bij voorwerpen die gevaarlijke goederen bevatten (UN 3537 t/m 3548) over de etikettering volgens 5.2.2.1.12.

### Opgelost

- **Duitse brondata lekte in formulieren.** Voor verboden stoffen vult ADR Tabel A élke kolom met de tekst "BEFÖRDERUNG VERBOTEN". Die belandde in de verpakkingsgroep, de gelimiteerde hoeveelheid en zelfs in de omschrijvingsregel van het vervoersdocument (`UN 1798, NITROHYDROCHLORIC ACID, 8, BEFÖRDERUNG VERBOTEN`). Alle kolommen worden nu gefilterd; het verbod wordt uitsluitend als waarschuwing getoond.
- De EmS-terugval hield geen rekening met de divisie: gassen kregen op basis van klasse "2" geen indicatie. Nu wordt eerst de divisie uit de etikettenkolom gebruikt (2.1 → F-D/S-U, 2.2 → F-C/S-V, 2.3 → F-C/S-U), waardoor vrijwel elk UN-nummer een bruikbaar noodschema krijgt.

### Bekende beperking

De EmS-gegevens zijn een gecureerde compilatie: negen vermeldingen zijn tijdens het samenstellen tegen openbare bronnen gecontroleerd en als zodanig gemarkeerd, de overige volgen het gevarenprofiel van de stof. Voor UN-nummers zonder exacte vermelding toont de app een indicatieve klassestandaard die herkenbaar als suggestie wordt gepresenteerd en niet automatisch wordt ingevuld. De actuele IMDG-uitgave blijft leidend.

## [1.8.0] — 2026-08-01

Gevaarlijke stoffen: automatische invulling per modaliteit en zeevaartsegregatie.

### Toegevoegd

- **Automatische invulling van gevaarlijke-stoffengegevens** (`POST /api/dg/prepare`): u vult per collo alleen het UN-nummer in (of zoekt op stofnaam) en CargoPilot leidt daaruit de juiste vervoersnaam, klasse, nevengevaren, verpakkingsgroep, verpakkingsinstructie, vervoerscategorie, tunnelcode, Kemler-nummer en LQ/EQ-limieten af. Aantal colli, verpakkingssoort en massa's worden overgenomen uit de al ingevoerde colli. Alleen lege velden worden gevuld, zodat handmatige correcties altijd blijven staan.
- **EmS-noodschema's voor zeevervoer**: per UN-nummer wordt de EmS-code (brand- en lekkageschema) ingevuld voor een gecureerde selectie van veelvervoerde stoffen uit de IMDG Dangerous Goods List; voor overige stoffen wordt een indicatieve klassestandaard getoond die als zodanig herkenbaar is.
- **Luchtvrachtregels**: lithiumbatterijen UN 3090/3480 worden automatisch als **Cargo Aircraft Only** met de juiste IATA-verpakkingsinstructie (PI 965/968) gemarkeerd, UN 3091/3481 krijgen PI 966/967 respectievelijk 969/970, en klasse 2.3 (giftige gassen) wordt gemeld als verboden in de luchtvaart.
- **Officiële omschrijvingsregels per formulier** worden automatisch samengesteld en getoond vóór de export: ADR/RID/ADN volgens 5.4.1.1.1 inclusief tunnelcode, aantal colli en totale hoeveelheid, IMDG met EmS-code en marine pollutant, IATA met verpakkingsinstructie en Cargo Aircraft Only-vermelding.
- **Totale hoeveelheid per vervoerscategorie** (ADR 5.4.1.1.1.1) wordt berekend en op de gegenereerde ADR/RID/ADN-documenten geplaatst — verplicht bij gebruik van de 1.1.3.6-vrijstelling en tot nu toe handwerk.
- **IMDG-segregatiecontrole (7.2.4)**: de volledige klassescheidingstabel is opgenomen, inclusief de codes 1 t/m 4 ("away from", "separated from", "separated by a complete compartment or hold", "separated longitudinally") met de bijbehorende afstanden. Nevengevaren tellen mee; bij zeevracht verschijnen de conflicten in het nalevingspaneel.
- **Vrijgestelde en gelimiteerde hoeveelheden** worden uitgelegd in gewone taal (E1 t/m E5 met de maxima per binnen- en buitenverpakking volgens 3.5.1.2, en de LQ-limiet per binnenverpakking volgens 3.4).
- **Klasse-specifieke documentvereisten** worden benoemd: netto explosieve massa en compatibiliteitsgroepen bij klasse 1, temperatuurbeheersing bij zelfontledende stoffen en organische peroxiden, verantwoordelijke persoon bij klasse 6.2, en radionucliden, collo-categorie, transportindex en veiligheidsindex kritikaliteit bij klasse 7. Voor zeevracht wordt het containerbeladingscertificaat genoemd, voor luchtvracht de ondertekening in tweevoud.
- **Versiebeleid** expliciet vastgelegd in de README: patchreleases voor correcties, minor voor nieuwe functionaliteit, major uitsluitend voor ingrijpende herzieningen.

### Opgelost

- **De ADR-classificatiecode werd ten onrechte als nevengevaar ingevuld.** Bij het kiezen van een UN-nummer belandde de classificatiecode (bijvoorbeeld `F1` bij benzine, `M4` bij lithiumbatterijen of `C1` bij zwavelzuur) in het veld "bijkomend gevaar", waardoor de omschrijving op het vervoersdocument bijvoorbeeld `UN 1203, BENZINE, 3 (F1), II` werd in plaats van `UN 1203, BENZINE, 3, II`. Nevengevaren worden nu correct uit de etikettenkolom van ADR Tabel A gehaald: UN 2031 (salpeterzuur) levert nu terecht `8 (5.1)`, benzine levert geen nevengevaar meer. De classificatiecode wordt apart bewaard.
- **Divisie van gassen en explosieven** wordt nu correct bepaald: ADR Tabel A vermeldt bij gassen alleen klasse "2" en bij explosieven alleen "1", terwijl de werkelijke divisie in de etikettenkolom (2.1/2.2/2.3) respectievelijk de classificatiecode (bijvoorbeeld 1.4S) staat. Dit is bepalend voor samenlading en segregatie, die daardoor eerder onvolledig konden zijn.
- De IATA-omschrijving toonde de ADR-verpakkingsinstructie (P001, IBC02) die voor luchtvracht niet geldig is; er wordt nu uitsluitend een IATA-verpakkingsinstructie vermeld wanneer die bekend is.
- De knop om een document te downloaden heette nog **"Download Excel"** terwijl alle documenten als PDF worden geëxporteerd; dit is nu "Document downloaden".
- Twee ontbrekende vertaalsleutels toonden ruwe tekst in de interface: het plakveld in het importvenster had geen placeholder, en inactief materieel toonde `questions.no` (een restant van het verwijderde interne formulier) in plaats van "Inactief".
- De uitleg bij de gevaarlijke-stoffenstap beschreef nog de oude werkwijze (alles handmatig invullen, UN-gegevens alleen online) en is aangepast aan de automatische invulling met offline database.

## [1.7.0] — 2026-07-31

Goederendatabase uitgebreid naar 400 transportgoederen.

### Toegevoegd

- **Goederendatabase uitgebreid van 159 naar 400 goederen** met (stort)dichtheden, bandbreedtes (min/max) en NL/EN-aliassen, transportbreed:
  - **Bouw & natuursteen**: basalt, hardsteen (arduin), travertin, kwartsiet, porfier, spoorballast, dekvloermortel, tegellijm, betonblokken, trottoirbanden, straatbakstenen, gipspleister, zilverzand, dolomiet, krijt, leem, dakbedekkingsrollen, cement in zakken, betonmortel (nat), breuksteen
  - **Isolatie**: perliet, vermiculiet, schuimglas, houtvezelplaat, cellulose-inblaaswol
  - **Metalen**: zuiver ijzer, chroom, mangaan, wolfraam, molybdeen, kobalt, zilver, goud, platina, antimoon, cadmium, bismut, silicium, zamak, hardmetaal (wolfraamcarbide), kwik, ferrosilicium
  - **Hout & plaatmateriaal**: grenen, populier, els, esdoorn, noten, kersen, haagbeuk, iep, kastanje, linde, iroko, sapeli, bangkirai, padoek, wengé, accoya, western red cedar, robinia, thermohout, OSB, MDF, HDF, hardboard, zachtboard, gelamineerd hout (glulam), kruislaaghout (CLT), kurk, rondhout
  - **Brandstoffen, chemie & gassen**: ruwe olie, nafta, huisbrandolie, biodiesel (FAME), HVO, oplosmiddelen (tolueen, xyleen, benzeen, styreen, MEK, IPA, ethylacetaat, terpentine/terpentijn), zuren (azijnzuur, salpeterzuur, fosforzuur), waterstofperoxide, ammonia, glycerine, plantaardige oliën per soort (olijf-, palm-, zonnebloem-, koolzaad-, lijnolie), bitumenemulsie, sterke drank, en vloeibaar gemaakte gassen (LNG, propaan, butaan, CO₂, stikstof, zuurstof, argon, waterstof, watervrije ammoniak)
  - **Meststoffen & chemie (vast)**: ammoniumnitraat, ammoniumsulfaat, DAP/MAP/TSP, kieseriet, urean (UAN), calciumchloride, citroenzuur, waspoeder, actieve kool, carbon black, titaandioxide, zinkoxide, zetmeel, vacuümzout, natriumbicarbonaat, paraffine, bleekloog, ijzerchloride, epoxyhars
  - **Agrarisch**: spelt, boekweit, gierst, sorghum, quinoa, lijnzaad, peulvruchten (erwten, bonen, linzen, kikkererwten), veevoergrondstoffen (sojaschroot, raapzaadschroot, zonnebloemschroot, palmpitschilfers, bietenpulppellets, DDGS, luzernepellets, vismeel), kuilvoer, drijfmest en vaste mest, compost, boomschors, houtkrullen, potgrond, graszaad, mosterd-/sesamzaad, pinda's, hoppellets, tabak en thee
  - **Groente & fruit** (effectieve dichtheid in kisten/dozen): bananen, sinaasappels, citroenen, peren, druiven, meloenen, aardbeien, tomaten, komkommers, paprika, prei, bloemkool, kool, wortelen, champignons
  - **Levensmiddelen**: keukenzout, pasta, havermout, melk- en weipoeder, boter, kaas, honing, chocolade, cacaoboter, gebrande koffie, flessenwater, suikersiroop, azijn
  - **Ertsen & energie**: koper- en zinkconcentraat, chroomerts, mangaanerts, nikkelerts, fosfaaterts, ilmeniet, bariet, bentoniet, kaolien, veldspaat, olivijn, steenzout, petroleumcokes, bruinkool, antraciet, aluinaarde, gebluste kalk
  - **Kunststoffen, papier & textiel**: massief polystyreen, ABS, polycarbonaat, PET, PTFE, PUR-schuim, rubbergranulaat, kopieerpapier, krantenpapier, tissue, boeken, wol-, vlas- en tapijtgoederen, kleding
  - **Afval & recycling**: RDF-balen, e-waste, AEC-bodemas, groenafval, zuiveringsslib, gebruikt frituurvet, gemengd kunststofafval
  - **Stukgoed-praktijkgemiddelden**: lege pallets en kratten, machines op skids, witgoed, loodaccu's, kabelhaspels, sanitair, bevestigingsmateriaal, matrassen, fietsen
- Elke vermelding geeft aan of het om stortdichtheid, massieve dichtheid, vloeistofdichtheid of een effectieve palletdichtheid gaat

### Gewijzigd

- Te brede aliassen zijn verplaatst naar specifiekere goederen (bijv. "olijfolie" van generieke plantaardige olie naar olijfolie, "grenen" van vuren naar grenen, "potgrond" van turf naar potgrond, "gebluste kalk" van ongebluste kalk naar kalkhydraat), zodat herkenning en dichtheid nauwkeuriger zijn
- Alle aliassen zijn gegarandeerd uniek over de hele database, zodat een omschrijving altijd op één goed uitkomt
- Bestaande installaties krijgen de nieuwe goederen automatisch bij de eerstvolgende catalogus-sync (standaard bij opstarten)

## [1.6.0] — 2026-07-25

Handtekeningen op documenten en een complete offline UN- en verpakkingendatabase.

### Toegevoegd

- **Handtekening tekenen, uploaden of overslaan**: in de zendinggegevens-stap kan de afzender een handtekening tekenen (muis, vinger of stylus, met vloeiende lijnen, ongedaan maken en wissen) of een afbeelding uploaden (PNG/JPEG/WebP; een witte achtergrond wordt automatisch transparant gemaakt en de handtekening wordt strak bijgesneden). De handtekening wordt geplaatst in het afzendervak van de documenten: CMR vak 22 (alle vier doorslagen), het handtekeningveld van de IATA Shipper's Declaration en een nette handtekeningsectie in alle gegenereerde PDF's. Overslaan blijft altijd mogelijk om fysiek met pen te ondertekenen. Handtekeningen van vervoerder en geadresseerde (CMR vak 23/24, CIM vak 61, afleverbon-ontvangst) blijven altijd leeg.
- **UN-nummer-autocomplete**: bij het invullen van een UN-nummer of stofnaam verschijnen direct voorstellen uit een **offline database met 2.928 ADR-vermeldingen** (klasse, classificatiecode, verpakkingsgroep, etiketten, gelimiteerde/vrijgestelde hoeveelheden, verpakkingsinstructies, vervoerscategorie, tunnelcode en Kemler-nummer uit ADR Tabel A; Engelse stofnamen uit de officiële Amerikaanse 49 CFR 172.101-tabel). Eén klik vult PSN, klasse, verpakkingsgroep, verpakkingsinstructie, vervoerscategorie en tunnelcode automatisch in; waar internet beschikbaar is verrijkt de bestaande ADR 2025-lookup de gegevens live. Nieuw endpoint: `GET /api/dg/search`.
- **Verpakkingendatabase**: alle 107 UN-verpakkingscodes volgens ADR 6.1.2/6.5.1.4/6.6.2 (vaten, jerrycans, kisten en dozen, zakken, composietverpakkingen met kunststof of glazen binnenhouder, metalen/flexibele/kunststof/composiet-IBC's zoals big bags en 1000-litertotes, grote verpakkingen en drukhouders) met NL/EN-omschrijvingen en indicatie vloeistof/vaste stof. Het verpakkingsveld in de gevaarlijke-stoffenstap is nu een zoekbare keuzelijst; vrije tekst blijft mogelijk. Nieuw endpoint: `GET /api/dg/packagings`.
- De UN-lookup (`GET /api/dg/lookup`) valt automatisch terug op de offline database wanneer de externe ADR-bron niet bereikbaar is — de gevaarlijke-stoffenstap werkt nu volledig offline.

### Gewijzigd

- Formulierteksten verduidelijkt: carrier- en ontvangsthandtekeningen worden nooit vooraf ingevuld; de afzenderhandtekening wordt uitsluitend geplaatst wanneer de gebruiker die zelf tekent of uploadt.

## [1.5.0] — 2026-07-25

Eén wizard voor alle formulieren, locatie- en adres-autocomplete, en een transportbrede goederendatabase.

### Toegevoegd

- **Formulieren-subwizard**: na de colli-invoer volgt één doorlopende wizard — eerst de **zendinggegevens** (partijen, route, referenties) die één keer worden ingevuld en in álle geselecteerde formulieren worden hergebruikt, daarna per formulier een eigen stap ("Formulier x van y") met uitsluitend de velden die dat formulier nog nodig heeft. Stappen zijn direct aanklikbaar en tonen met een groene/oranje stip of alle verplichte velden zijn ingevuld; formulieren zonder eigen velden worden benoemd als "gedekt door de zendinggegevens".
- **Adres-autocomplete**: bij adresvelden (afzender, geadresseerde) kan een adres worden gezocht en automatisch ingevuld via een Photon-geocoder op OpenStreetMap-data (instelbaar met `GEO_ADDRESS_API_URL`; valt stil zonder internettoegang, handmatig invullen blijft altijd mogelijk). Nieuw endpoint: `GET /api/geo/address`.
- **Locatie-autocomplete voor luchthavens, havens en treinstations**: route-velden (laadplaats, losplaats, ontvangst/aflevering, eindbestemming) zoeken live in meegeleverde open datasets — 4.500+ luchthavens met IATA/ICAO-code (OurAirports), 17.500+ havens met UN/LOCODE (UNECE) en 750+ Europese hoofdstations (Trainline EU). Per modaliteit wordt de juiste soort voorgesteld (lucht → luchthavens, zee/binnenvaart → havens, spoor → stations, weg/multimodaal → alles plus adressen). Nieuw endpoint: `GET /api/geo/locations`. Vrije tekst blijft altijd toegestaan.
- **Goederendatabase sterk uitgebreid**: van 18 naar **159 goederen** met (stort)dichtheden en NL/EN-aliassen — bouwmaterialen (cement, kalkzandsteen, baksteen, dakpannen, natuursteen, asfalt, granulaten, isolatie), metalen en schroot, houtsoorten en houtproducten, brandstoffen en vloeistoffen (diesel, kerosine, smeerolie, zuren, AdBlue), chemie en meststoffen, agrarische bulk (granen, zaden, aardappelen, veevoer, hooi/stro, koffie, cacao), levensmiddelen en dranken, papier en verpakking, ertsen en energie (ijzererts, steenkool, cokes), recycling en afvalstromen, textiel en stukgoed-praktijkgemiddelden (pallets, pakketten, meubels).
- Catalogus-zoeken toont goederen nu ook rechtstreeks als **materiaal-suggestie met dichtheid** (bijv. "Tarwe — 780 kg/m³"), naast de bestaande profiel- en materieelresultaten.
- **Gewichtsberekening voor blokvormige goederen**: een herkend materiaal met drie afmetingen wordt nu als massief blok op dichtheid doorgerekend (bijv. "baksteen 100x100x100cm" → 1.900 kg), ook zonder expliciet producttype als plaat of balk.

### Gewijzigd

- De stap "Zendinggegevens" heet in de voortgangsbalk nog steeds hetzelfde, maar bevat nu de sub-wizard met eigen navigatie; dubbele invoer van dezelfde gegevens over formulieren is volledig vervallen.
- Nieuwe environment variables: `GEO_ADDRESS_API_URL` en `GEO_ADDRESS_TIMEOUT_SECONDS`.

## [1.4.0] — 2026-07-13

CargoPilot is volledig civiel: militaire formulieren verwijderd.

### Verwijderd

- Het interne militaire formulier is volledig verwijderd: de wizardstap met vragen, het Excel-template, de export-endpoints, de PDF-weergave en alle verwijzingen in de interface. Voor militaire doeleinden komt een aparte private fork (CargoPilot MIL) met eigen formulieren.
- Militaire vlaggen en helpteksten (o.a. wapens, munitie, ITAR, TBB) en externe verwijzingen naar defensieportalen
- Oudere Docker-images bevatten het formulier nog; deze worden via de tag-opschoning van Docker Hub verwijderd

### Gewijzigd

- **Colli-invoer**: de stap "Review" heet nu **Colli**; per collo kan worden aangevinkt of het om gevaarlijke stoffen gaat. Bij een vinkje (of een herkend UN-nummer) volgt automatisch de gevaarlijke-stoffenstap.
- De gevaarlijke-stoffenstap, UN-detectie, ADR/IATA-nalevingscontroles en alle transportdocumenten blijven volledig behouden
- Per modaliteit is standaard het primaire vervoersdocument voorgeselecteerd (weg: CMR, spoor: CIM, lucht: AWB-instructies, zee: B/L-instructies)

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
- **Nieuwe documenten**: CMR (PDF), IATA (PDF), CIM (PDF), IMO Multimodal DG Form, VGM-verklaring (methode 1/2 met somcontrole), AWB Shipping Instructions, B/L / Sea Waybill Shipping Instructions, ADR/ADN-vervoersdocument, paklijst en afleverbon
- **Juridische disclaimer**: aparte disclaimer-pagina in de app (NL/EN), `DISCLAIMER.md`, een concept-waarschuwing bij export en een disclaimer in de metadata/voettekst van gegenereerde documenten. Aansprakelijkheid volledig uitgesloten; Apache License 2.0 met Commons Clause expliciet benoemd.
- Officiële regelgeving en vaste juridische teksten (CMR-paramountclausule, IATA-certificering/WARNING, IMO-verklaring, VGM SOLAS-referentie, ADR 5.4.1-omschrijvingsregel) plus links naar de officiële brontemplates per document
- **Zendinggegevens-stap**: gedeelde blokken (partijen, route, referenties) worden één keer ingevuld en hergebruikt in alle geselecteerde documenten
- **Documentstatussen in de samenvatting**: gereed voor export, concept, wacht op carriergegevens, geblokkeerd door veiligheidsvalidatie, niet van toepassing
- **Gevaarlijke-stoffenvalidatie per modaliteit** (ADR/RID/ADN/IMDG/IATA DGR): export van DG-verklaringen wordt geblokkeerd bij onvolledige classificatie (UN-nummer, Proper Shipping Name, klasse; voor IATA ook packing instruction, colli en hoeveelheid)
- Extra DG-velden bij IMO/IATA-formulieren: technische naam, marine pollutant, Cargo Aircraft Only, overpack, noodcontact, EmS-code
- Nieuwe API-endpoints: `GET /api/documents/registry`, `POST /api/documents/validate`, `POST /api/documents/export`

### Gewijzigd

- Wizard start met formulierenkeuze
- Handtekening-, carrier- en operationele velden worden nooit vooraf ingevuld; ze worden in de export als zodanig gemarkeerd
- Navigatie: het startpunt heet "Nieuwe zending" en begint bij de modaliteitskeuze
- Wizard-voortgangsbalk toont op mobiel iconen i.p.v. tekst (meer stappen passen op het scherm)

## [1.0.0] — 2026-07-11

Eerste stabiele release.

### Toegevoegd

- Wizard: review-first flow met materiaalcatalogus en synoniemen
- Gevaarlijke stoffen met ADR UN-lookup
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

