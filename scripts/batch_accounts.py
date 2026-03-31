#!/usr/bin/env python3
"""
JAKALA GTM OS — Batch Account Creator
Opretter account-mapper for alle norske target accounts.
"""

import os
from pathlib import Path
from datetime import date

TODAY = date.today().isoformat()
BASE  = Path(__file__).parent.parent / "Accounts"

# ─── ACCOUNT DEFINITIONER ────────────────────────────────────────────────────

ACCOUNTS = [

  # ── SPORT ────────────────────────────────────────────────────────────────
  {
    "folder": "sport-outlet",
    "name": "Sport Outlet",
    "country": "Norge",
    "industry": "Retail / Sports",
    "hq": "Oslo, Norge",
    "description": "Norsk sportsretailer med stort varesortiment innen sports- og fritidsutstyr. Konkurrerer med XXL og Intersport i det norske markedet.",
    "icp": 7, "deal": 7,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — produktdata-kvalitet og søk",
    "buyer": "Head of Ecommerce / Digital Director",
    "value": "€75K–€200K",
    "signals": "Konkurrerer i et presset norsk sportsmarked — digitalt løft er nødvendig for å forsvare markedsandeler mot XXL og Elkjøp.",
    "why_now": "Norsk sportsmarked konsolideres. Digitale vinnere tar markedsandeler.",
  },
  {
    "folder": "sports-holding",
    "name": "Sports Holding",
    "country": "Norge",
    "industry": "Retail / Sports (Holding)",
    "hq": "Norge",
    "description": "Holdingselskap for norske sportsretailkjeder. Potensielt morselskap for Sport Outlet og andre sportskjeder i Norge.",
    "icp": 7, "deal": 6,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — gruppe-level produktdata",
    "buyer": "CDO / Group Digital Director",
    "value": "€75K–€250K",
    "signals": "Holdingstruktur = felles data-infrastruktur er en naturlig entry. Multi-brand kompleksitet er JAKALAs styrke.",
    "why_now": "Konsolidering i norsk sports-retail skaper behov for felles digital plattform.",
  },
  {
    "folder": "helly-hansen",
    "name": "Helly Hansen",
    "country": "Norge",
    "industry": "Consumer Brand / Outdoor & Sports",
    "hq": "Oslo, Norge (eid av Canadian Tire Corp)",
    "description": "Ikonisk norsk outdoor- og seilermerke grunnlagt 1877. Internasjonalt premium brand med sterk DTC og B2B-kanal (ski-resorts, workwear). Eid av Canadian Tire Corporation.",
    "icp": 8, "deal": 8,
    "gtm": "Data Revenue Unlock",
    "entry": "Data Revenue Diagnostic — PIM, produktdata-kvalitet og DTC-kanal",
    "buyer": "VP Digital / Head of Ecommerce / CDO",
    "value": "€100K–€400K",
    "signals": "Premium international brand med kompleks produktdata (workwear + consumer), multi-kanal DTC + B2B. Eid av canadisk konsern = budsjett tilgjengelig.",
    "why_now": "DTC-vekst globalt krever skarp produktdata og personalisering på tvers av markeder.",
  },
  {
    "folder": "xxl-fraser-group",
    "name": "XXL (Fraser Group)",
    "country": "Norge / Norden",
    "industry": "Retail / Sports",
    "hq": "Oslo, Norge (eid av Frasers Group UK)",
    "description": "Nordisk ledende sportsretailer. Gikk gjennom restrukturering og ble kjøpt av britiske Frasers Group (Sports Direct) i 2024. Opererer i Norge, Sverige og Finland.",
    "icp": 8, "deal": 8,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — produktkatalog og søkekvalitet post-restrukturering",
    "buyer": "CTO / Head of Ecommerce",
    "value": "€100K–€350K",
    "signals": "Nytt eierskap (Frasers Group 2024) + restrukturering = ny ledelse, nye prioriteringer, åpent vindu. Post-M&A er JAKALAs beste entry-timing.",
    "why_now": "Ny eier vil modernisere — digitalt løft er første prioritet etter M&A.",
  },

  # ── INTERIØR ─────────────────────────────────────────────────────────────
  {
    "folder": "nille",
    "name": "Nille",
    "country": "Norge",
    "industry": "Retail / Interior & Gifts",
    "hq": "Norge",
    "description": "Norsk kjede for interiør, gaver og sesongvarer med 500+ butikker i Norden. Sterk sesongbasert sortiment og høyt SKU-volum.",
    "icp": 7, "deal": 7,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — sesongdata og produktkatalog-håndtering",
    "buyer": "Head of Ecommerce / Digital Director",
    "value": "€50K–€150K",
    "signals": "500+ butikker, høyt SKU-volum, sterk sesongvariasjon = produktdata-kompleksitet er høy.",
    "why_now": "Sesongbasert retail krever presis produktdata-timing og søk.",
  },

  # ── GLASS & SERVISE ───────────────────────────────────────────────────────
  {
    "folder": "christiania-glassmagasin",
    "name": "Christiania Glassmagasin",
    "country": "Norge",
    "industry": "Retail / Glass & Tableware",
    "hq": "Oslo, Norge",
    "description": "En av Norges eldste butikker (est. 1739). Spesialisert på glass, porselen, bestikk og borddekning. Premium posisjonering i norsk marked.",
    "icp": 6, "deal": 6,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — produktdata og digital discovery",
    "buyer": "Daglig leder / Head of Ecommerce",
    "value": "€30K–€100K",
    "signals": "Tradisjonell retailer med premium sortiment — digital transformasjon er nødvendig for å nå yngre målgrupper.",
    "why_now": "Premium retail taper til Amazon og nisjeaktører uten sterk digital tilstedeværelse.",
  },
  {
    "folder": "kitchen",
    "name": "Kitchen",
    "country": "Norge",
    "industry": "Retail / Kitchen & Lifestyle",
    "hq": "Norge",
    "description": "Norsk retailkjede for kjøkkenutstyr, kokekar og livsstilsprodukter. Konkurrerer med Jernia og internasjonale aktører.",
    "icp": 6, "deal": 6,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — produktkatalog og søk",
    "buyer": "Head of Ecommerce / Daglig leder",
    "value": "€30K–€100K",
    "signals": "Spesialisert kjøkkenretail med kompleks produktdata (materiale, kompatibilitet, merke).",
    "why_now": "Kjøkkenretail vinner på sterk produktdata og inspirasjonsdrevet discovery.",
  },

  # ── JERNVARE & VERKTØY ────────────────────────────────────────────────────
  {
    "folder": "jernia",
    "name": "Jernia",
    "country": "Norge",
    "industry": "Retail / Hardware & Tableware",
    "hq": "Norge",
    "description": "Norsk kjede for jernvare, verktøy, kjøkkenutstyr og husholdningsartikler. Bredt sortiment fra B2C og B2B. Nær 100 butikker.",
    "icp": 7, "deal": 7,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — teknisk produktdata og B2B-katalog",
    "buyer": "Head of Ecommerce / CTO",
    "value": "€75K–€200K",
    "signals": "Bredt sortiment (verktøy + kjøkken + hage) = høy produktdata-kompleksitet. B2B-kanal krever spesifikke tekniske specs.",
    "why_now": "B2B-kunder forventer presis teknisk produktinformasjon — gap er stort i norsk jernvare-retail.",
  },

  # ── MØBLER ───────────────────────────────────────────────────────────────
  {
    "folder": "bohus",
    "name": "Bohus",
    "country": "Norge / Sverige",
    "industry": "Retail / Furniture",
    "hq": "Norge",
    "description": "Skandinavisk møbelkjede med sterk tilstedeværelse i Norge og Sverige. Selger møbler, tekstiler og interiør. Konkurrerer med IKEA og Skeidar.",
    "icp": 7, "deal": 7,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — møbel-produktdata, varianter og konfigurasjon",
    "buyer": "Head of Ecommerce / Digital Director",
    "value": "€75K–€250K",
    "signals": "Møbler har ekstremt kompleks produktdata (dimensjoner, materiale, farge, konfigurasjon). Gap mellom fysisk og digital opplevelse er stort.",
    "why_now": "Post-COVID møbelmarked er digital-first. Svak produktdata taper kunder til IKEA.",
  },
  {
    "folder": "skeidar",
    "name": "Skeidar",
    "country": "Norge",
    "industry": "Retail / Furniture",
    "hq": "Norge",
    "description": "Norsk møbelkjede med fokus på sofa, seng og interiør. Norges største møbelkjede med 30+ varehus.",
    "icp": 7, "deal": 7,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — produktkatalog og digital konfigurasjon",
    "buyer": "Head of Ecommerce / Digital Director",
    "value": "€75K–€200K",
    "signals": "Norges største møbelkjede — høy SKU-kompleksitet, varianter og leveringstid-data.",
    "why_now": "Møbelkunder forventer digital konfigurasjon og presis produktinfo.",
  },
  {
    "folder": "møbelringen",
    "name": "Møbelringen",
    "country": "Norge",
    "industry": "Retail / Furniture",
    "hq": "Norge",
    "description": "Norsk møbelkjede og franchise-nettverk. Bredt norsk fotavtrykk.",
    "icp": 6, "deal": 6,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — franchise-katalog harmonisering",
    "buyer": "Digital Director / Head of Ecommerce",
    "value": "€50K–€150K",
    "signals": "Franchise-struktur = inkonsistent produktdata på tvers av butikker.",
    "why_now": "Franchise-retail trenger sentralisert produktdata for digital skalerbarhet.",
  },

  # ── KJØKKEN ───────────────────────────────────────────────────────────────
  {
    "folder": "huseby",
    "name": "Huseby",
    "country": "Norge",
    "industry": "Retail / Kitchen",
    "hq": "Norge",
    "description": "Norsk kjøkkensenter med showroom-basert salg.",
    "icp": 6, "deal": 5,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — digital showroom og produktkonfigurasjon",
    "buyer": "Daglig leder / Digital ansvarlig",
    "value": "€30K–€100K",
    "signals": "Kjøkken er high-consideration purchase — digital konfigurasjon og produktdata er avgjørende.",
    "why_now": "Kjøkkenkunder starter research digitalt — svak digital tilstedeværelse taper leads.",
  },
  {
    "folder": "drømmekjøkkenet",
    "name": "Drømmekjøkkenet",
    "country": "Norge",
    "industry": "Retail / Kitchen",
    "hq": "Norge",
    "description": "Norsk kjøkkenspesialist og showroom-kjede.",
    "icp": 6, "deal": 5,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — digital konfigurasjon og lead-generering",
    "buyer": "Daglig leder / Marketing Director",
    "value": "€30K–€100K",
    "signals": "Premium kjøkkenmarked — digital lead-generering og produktvisualisering er nøkkelen.",
    "why_now": "High-end kjøkken selges gjennom inspirasjon. Svak digital er tapte leads.",
  },
  {
    "folder": "sigdal",
    "name": "Sigdal",
    "country": "Norge",
    "industry": "Manufacturer & Retail / Kitchen",
    "hq": "Eggedal, Norge",
    "description": "Norsk produsent og selger av kjøkken. Et av Norges ledende kjøkkenmerker med eget produksjonsanlegg. Selger gjennom egne butikker og forhandlere.",
    "icp": 7, "deal": 6,
    "gtm": "Data Revenue Unlock",
    "entry": "Data Revenue Diagnostic — PIM og forhandler-katalog",
    "buyer": "Salgs- og markedsdirektør / Digital Director",
    "value": "€50K–€150K",
    "signals": "Produsent + retail = kompleks PIM-utfordring. Forhandlerkanal krever konsistent produktdata.",
    "why_now": "Produsenter taper digitalt til rene retailere uten sterk PIM-strategi.",
  },
  {
    "folder": "stray",
    "name": "Stray",
    "country": "Norge",
    "industry": "Retail / Kitchen",
    "hq": "Norge",
    "description": "Norsk kjøkkenretailer og interiørspesialist.",
    "icp": 6, "deal": 5,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot",
    "buyer": "Daglig leder / Head of Ecommerce",
    "value": "€30K–€100K",
    "signals": "Spesialisert kjøkkenretail med kompleks produktdata.",
    "why_now": "Digital kjøkken-søk øker — produktdata-kvalitet avgjør hvem som vinner.",
  },
  {
    "folder": "norema",
    "name": "Norema",
    "country": "Norge",
    "industry": "Manufacturer & Retail / Kitchen",
    "hq": "Stord, Norge",
    "description": "Norsk kjøkkenprodusent med lang historie. Selger gjennom eget nettverk av forhandlere og egne showrooms. Et av Norges mest kjente kjøkkenmerker.",
    "icp": 7, "deal": 6,
    "gtm": "Data Revenue Unlock",
    "entry": "Data Revenue Diagnostic — forhandler-PIM og digital produktkonfigurasjon",
    "buyer": "Markedsdirektør / Digital Director",
    "value": "€50K–€150K",
    "signals": "Produsent med forhandlernettverk = distribuert produktdata-problem. Nasjonal kjennskap men svak digital.",
    "why_now": "Kjøkkenmarkedet er i sterk digital vekst — produsenter uten PIM taper markedsandeler.",
  },

  # ── KLÆR ─────────────────────────────────────────────────────────────────
  {
    "folder": "gant-norway",
    "name": "GANT Norway",
    "country": "Norge",
    "industry": "Retail / Fashion",
    "hq": "Oslo, Norge (globalt brand, norsk drift)",
    "description": "GANT i Norge — premium preppy fashion brand med butikker og netthandel. Internasjonalt brand med norsk retail-drift.",
    "icp": 7, "deal": 6,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — produktdata og digital merchandising",
    "buyer": "Country Manager / Head of Ecommerce",
    "value": "€50K–€150K",
    "signals": "Premium fashion krever sterk produktbeskrivelse og stilkonfigurasjon. International brand, local execution gap.",
    "why_now": "Fashion DTC vokser. Premium kunder forventer premium digital opplevelse.",
  },
  {
    "folder": "ferner-jacobsen",
    "name": "Ferner Jacobsen",
    "country": "Norge",
    "industry": "Retail / Fashion",
    "hq": "Oslo, Norge",
    "description": "Etablert norsk motehus med lang tradisjon. Spesialiserer seg på premium og luksus fashion i det norske markedet.",
    "icp": 6, "deal": 6,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — digital produktpresentasjon og discovery",
    "buyer": "Daglig leder / Head of Ecommerce",
    "value": "€30K–€100K",
    "signals": "Premium norsk motetradisjon — digital er underinvestert sammenlignet med butikkopplevelse.",
    "why_now": "Luksus- og premium fashion vinner digitalt med rik produktdata.",
  },
  {
    "folder": "follestad",
    "name": "Follestad",
    "country": "Norge",
    "industry": "Retail / Fashion",
    "hq": "Norge",
    "description": "Norsk motekjede med bredt sortiment. Selger klær og tilbehør til norske kunder.",
    "icp": 6, "deal": 6,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — søk og produktdata",
    "buyer": "Head of Ecommerce / Digital Director",
    "value": "€30K–€100K",
    "signals": "Bred norsk motekjede — digitalt konverteringsrate henger etter bransjens beste.",
    "why_now": "Fast fashion konsolideres digitalt — de uten sterk produktdata taper.",
  },

  # ── BANK ─────────────────────────────────────────────────────────────────
  {
    "folder": "sparebanken-norge",
    "name": "Sparebanken Norge",
    "country": "Norge",
    "industry": "Banking / Financial Services",
    "hq": "Norge",
    "description": "Norsk sparebank. Del av det norske sparebanksystemet.",
    "icp": 6, "deal": 6,
    "gtm": "AI Readiness Accelerator",
    "entry": "AI Readiness Diagnostic — kundedata og personaliseringsreadiness",
    "buyer": "CTO / CDO / Head of Digital",
    "value": "€75K–€200K",
    "signals": "Norske sparebanker er under press fra neobanker (Bulder, Nordea). AI og personalisering er nøkkelen til å beholde kunder.",
    "why_now": "Open banking og neobanker tvinger tradisjonelle banker til AI-investering.",
  },
  {
    "folder": "bulder-bank",
    "name": "Bulder Bank",
    "country": "Norge",
    "industry": "Banking / Neobank",
    "hq": "Stavanger, Norge (datterselskap av Sparebanken Vest)",
    "description": "Norsk neobank lansert 2019. Heldigital bank uten fysiske filialer. Datterselskap av Sparebanken Vest. Fokus på unge og tech-savvy kunder.",
    "icp": 7, "deal": 7,
    "gtm": "AI Readiness Accelerator",
    "entry": "AI Readiness Diagnostic — dataplattform og AI-personalisering",
    "buyer": "CTO / Head of Product",
    "value": "€75K–€200K",
    "signals": "Neobank = digital-first, datadrevet. Rask vekst krever skalerbar data-arkitektur og AI-personalisering.",
    "why_now": "Neobanker vinner kunder på personalisering. Data-arkitektur er konkurransefortrinnet.",
  },
  {
    "folder": "sparebanken-sor",
    "name": "Sparebanken Sør",
    "country": "Norge",
    "industry": "Banking / Financial Services",
    "hq": "Kristiansand, Norge",
    "description": "Regional norsk sparebank med sterk tilstedeværelse på Sørlandet og Vestlandet.",
    "icp": 6, "deal": 6,
    "gtm": "AI Readiness Accelerator",
    "entry": "AI Readiness Diagnostic — kundedata og digital kanal",
    "buyer": "CTO / CDO",
    "value": "€75K–€200K",
    "signals": "Regional sparebank under digitaliseringspress. Kundelojalitet er truet av neobanker.",
    "why_now": "Bankene som ikke investerer i AI og personalisering i 2026 taper unge kunder permanent.",
  },
  {
    "folder": "kredittbanken",
    "name": "Kredittbanken",
    "country": "Norge",
    "industry": "Banking / Financial Services",
    "hq": "Norge",
    "description": "Norsk bank med fokus på kreditt og personlig økonomi.",
    "icp": 6, "deal": 5,
    "gtm": "AI Readiness Accelerator",
    "entry": "AI Readiness Diagnostic",
    "buyer": "CTO / Digital Director",
    "value": "€50K–€150K",
    "signals": "Kredittfokusert bank — AI-scoring og personalisering er strategisk kritisk.",
    "why_now": "Kredittprodukter digitaliseres. AI-modeller for risiko og personalisering er nøkkelen.",
  },

  # ── DAGLIGVARE ────────────────────────────────────────────────────────────
  {
    "folder": "coop-norge",
    "name": "COOP Norge",
    "country": "Norge",
    "industry": "Retail / Grocery",
    "hq": "Oslo, Norge",
    "description": "Norges nest største dagligvarekjede med ca. 30% markedsandel. Kooperativ struktur med merker som Coop Obs!, Coop Extra, Coop Marked og Prix. 1.6 millioner medlemmer.",
    "icp": 9, "deal": 8,
    "gtm": "Data Revenue Unlock",
    "entry": "Data Revenue Diagnostic — medlemsdata, personalisering og produktkatalog",
    "buyer": "CDO / Head of Digital / CTO",
    "value": "€150K–€600K",
    "signals": "1.6M medlemmer, 30% markedsandel, kooperativ struktur med multi-format (hypermarked, convenience, discount). Enorm datamengde underutnyttet.",
    "why_now": "NorgesGruppen presser med Trumf-personalisering. COOP må svare med sin egen data-strategi.",
  },
  {
    "folder": "norgesgruppen",
    "name": "NorgesGruppen",
    "country": "Norge",
    "industry": "Retail / Grocery",
    "hq": "Oslo, Norge",
    "description": "Norges største dagligvarekonsern med ca. 40% markedsandel. Eier Kiwi, MENY, Spar, Joker og Nærbutikken. Også eier av Trumf lojalitetsprogram.",
    "icp": 9, "deal": 9,
    "gtm": "Data Revenue Unlock",
    "entry": "Data Revenue Diagnostic — personalisering, handelsdata og AI-anbefalinger",
    "buyer": "CDO / Head of Data / CTO",
    "value": "€200K–€800K",
    "signals": "40% markedsandel, Trumf-data på millioner av nordmenn, multi-format. Største enkeltaktør i norsk dagligvare.",
    "why_now": "Trumf er Norges mest verdifulle lojalitetsdataset. Personalisering og AI-anbefalinger er neste steg.",
  },
  {
    "folder": "trumf",
    "name": "Trumf (NorgesGruppen)",
    "country": "Norge",
    "industry": "Loyalty / Data",
    "hq": "Oslo, Norge",
    "description": "NorgesGruppens lojalitetsprogram — Norges største med over 3 millioner aktive medlemmer. Brukes på tvers av Kiwi, MENY, Spar og Joker. Rik transaksjons- og atferdsdata.",
    "icp": 9, "deal": 9,
    "gtm": "Data Revenue Unlock",
    "entry": "Data Revenue Diagnostic — lojalitetsdata, personalisering og datamonetering",
    "buyer": "Head of Loyalty / CDO / Chief Data Officer",
    "value": "€200K–€700K",
    "signals": "3M+ aktive medlemmer, transaksjonsdata på tvers av alle NorgesGruppen-kjeder. En av Norges rikeste kommersielle data-assets.",
    "why_now": "Trumf-data er undermonetered. Personalisert kommunikasjon og AI-anbefalinger basert på kjøpsmønstre er åpenbar neste steg.",
  },

  # ── UTDANNING ─────────────────────────────────────────────────────────────
  {
    "folder": "bi-handelshoyskolen",
    "name": "Handelshøyskolen BI",
    "country": "Norge",
    "industry": "Education / Private University",
    "hq": "Oslo, Norge",
    "description": "Norges største private handelshøyskole med ca. 20,000 studenter. Tilbyr bachelor, master og executive education. Sterk merkevare i norsk næringsliv.",
    "icp": 7, "deal": 6,
    "gtm": "Experience Transformation",
    "entry": "Executive digital experience strategy — student journey og digital kanaler",
    "buyer": "Rektor / Digital Director / CMO",
    "value": "€75K–€250K",
    "signals": "Private høyskoler konkurrerer globalt om studenter. Digital student-opplevelse er avgjørende for rekruttering.",
    "why_now": "Internasjonal konkurranse om studenter krever best-in-class digital opplevelse og personalisering.",
  },
  {
    "folder": "kristiania-hoyskole",
    "name": "Kristiania Høyskole",
    "country": "Norge",
    "industry": "Education / Private University",
    "hq": "Oslo, Norge",
    "description": "Norsk privat høyskole med fokus på kreative fag, mediefag og business. Ca. 13,000 studenter.",
    "icp": 6, "deal": 6,
    "gtm": "Experience Transformation",
    "entry": "Digital experience strategy — student rekruttering og digital kanal",
    "buyer": "Digital Director / CMO",
    "value": "€50K–€150K",
    "signals": "Kreativ høyskole konkurrerer om studenter i en digital-first rekrutteringsarena.",
    "why_now": "Søkertall avgjøres av digital synlighet og opplevelse.",
  },
  {
    "folder": "den-nye-hoyskole",
    "name": "Den Nye Høyskole",
    "country": "Norge",
    "industry": "Education / Private University",
    "hq": "Oslo, Norge",
    "description": "Norsk privat høyskole.",
    "icp": 5, "deal": 5,
    "gtm": "Experience Transformation",
    "entry": "Digital experience — student journey",
    "buyer": "Digital Director / Rektor",
    "value": "€30K–€100K",
    "signals": "Mindre privat høyskole — trenger digital differensiering.",
    "why_now": "Studenter velger digitalt. Svak digital er tapte søkere.",
  },

  # ── SPESIELLE AKTØRER ────────────────────────────────────────────────────
  {
    "folder": "vinmonopolet",
    "name": "Vinmonopolet",
    "country": "Norge",
    "industry": "Retail / Government Monopoly (Wine & Spirits)",
    "hq": "Oslo, Norge",
    "description": "Statlig norsk monopol for salg av alkohol over 4.7%. Eneste lovlige detaljist for vin og brennevin i Norge. Ca. 350 butikker og nettbutikk. Forvalter et av Norges rikeste produktkatalog-datasets.",
    "icp": 8, "deal": 7,
    "gtm": "Commerce Optimization",
    "entry": "Commerce Optimization Pilot — produktsøk, smaksprofil-data og AI-anbefalinger",
    "buyer": "IT-direktør / Digital Director / CDO",
    "value": "€100K–€350K",
    "signals": "Monopolist med 350 butikker og netthandel. Rikt produktdata-univers (druetype, region, smaksprofil, matparing). AI-anbefalinger basert på smaksprofil er åpenbar mulighet.",
    "why_now": "Vinmonopolet er under press for å modernisere digitalt. AI-anbefalinger og personalisering er neste naturlige steg.",
  },
  {
    "folder": "naf",
    "name": "NAF (Norges Automobil-Forbund)",
    "country": "Norge",
    "industry": "Membership Organization / Automotive",
    "hq": "Oslo, Norge",
    "description": "Norges bilistorganisasjon og motorvognforbund. Ca. 600,000 medlemmer. Tilbyr veihjelp, forsikring, bilinspeksjon og reiseassistanse. Norges svar på AA/ADAC.",
    "icp": 7, "deal": 7,
    "gtm": "Data Revenue Unlock",
    "entry": "Data Revenue Diagnostic — medlemsdata, personalisering og tilleggsservice",
    "buyer": "CDO / Digital Director / Head of Digital Products",
    "value": "€75K–€250K",
    "signals": "600K medlemmer, transaksjonsdata på veihjelp og forsikring. Potensiell datamonetering og personalisert service-tilbud.",
    "why_now": "EV-revolusjonen endrer NAF-relevant tjenestetilbud. Digital personalisering av service er kritisk for relevans.",
  },
  {
    "folder": "varner-group",
    "name": "Varner Group",
    "country": "Norge / Norden",
    "industry": "Retail / Fashion (Multi-brand)",
    "hq": "Billingstad, Norge",
    "description": "Norges største motedetaljist og et av Nordens største motekonserner. Eier Cubus, Dressmann, Bik Bok, Carlings, Volt, Urban og Vivikes. Ca. 1,300 butikker i 8 land.",
    "icp": 9, "deal": 9,
    "gtm": "Data Revenue Unlock",
    "entry": "Data Revenue Diagnostic — multi-brand PIM, personalisering og produktdata på tvers av 7 merker",
    "buyer": "CDO / CTO / Group Digital Director",
    "value": "€200K–€700K",
    "signals": "7 merker, 1,300 butikker, 8 land — multi-brand kompleksitet er JAKALAs spesialitet. Hvert merke har eget sortiment, men deler infrastruktur.",
    "why_now": "Multi-brand fashion trenger sentralisert PIM og differensiert digital opplevelse per merke. Ingen gjør dette bedre enn JAKALA.",
  },

]

# ─── GENERATOR ───────────────────────────────────────────────────────────────

def icp_label(score):
    if score >= 9: return "Tier 1 — Høyeste prioritet"
    if score >= 8: return "Tier 2 — Høy prioritet"
    if score >= 7: return "Tier 3 — Aktiv overvåking"
    return "Tier 4 — Langsiktig"

def priority_label(deal):
    if deal >= 8: return "Hi"
    if deal >= 6: return "Med"
    return "Lo"

def create_account(a):
    folder = BASE / a["folder"]
    folder.mkdir(parents=True, exist_ok=True)

    # overview.md
    (folder / "overview.md").write_text(f"""# {a['name']} — Account Overview

Last updated: {TODAY}

---

## Company Profile

| Field | Detail |
|-------|--------|
| HQ | {a['hq']} |
| Country | {a['country']} |
| Industry | {a['industry']} |
| Type | Target account — pre-engagement |

---

## Digital Snapshot

{a['description']}

---

## Key Signals

{a['signals']}

---

## ICP Score: {a['icp']}/10 | Deal Score: {a['deal']}/10

- Tier: {icp_label(a['icp'])}
- Priority: {priority_label(a['deal'])}
- GTM Strategy: {a['gtm']}
- Entry offer: {a['entry']}
- Est. value: {a['value']}

---

*Research needed: Stakeholder identification, tech stack, recent news signals.*
""", encoding="utf-8")

    # strategy.md
    (folder / "strategy.md").write_text(f"""# {a['name']} — Commercial Strategy

Last updated: {TODAY}

---

## GTM Strategy: {a['gtm']}

---

## Entry Offer

**{a['entry']}**

**Est. value:** {a['value']}

---

## Why Now

{a['why_now']}

---

## Likely Buyer

{a['buyer']}

---

## Expansion Path

```
Entry diagnostic (€50–100K)
  → Data/commerce assessment (€150–300K)
    → Full programme (€300K+)
```

---

## Do Not

- Lead med DXP eller plattformerstatning i første kontakt
- Bruk generiske AI-buzz-ord
- Kontakt uten å ha gjort research på kjøperen
""", encoding="utf-8")

    # stakeholders.md
    (folder / "stakeholders.md").write_text(f"""# {a['name']} — Stakeholders

Last updated: {TODAY}

---

## Primary Contact

**Status: TBD — research needed**

Likely buyer: {a['buyer']}

| Field | Detail |
|-------|--------|
| Name | TBD |
| Title | {a['buyer']} |
| LinkedIn | TBD — research needed |
| Background | TBD |
| Outreach angle | {a['entry']} |

---

## Next Step

Identifiser named buyer via LinkedIn og {a['name'].lower().replace(' ', '')}.no/ledelse eller årsrapport.
""", encoding="utf-8")

    # next-actions.md
    (folder / "next-actions.md").write_text(f"""# {a['name']} — Next Actions

Last updated: {TODAY}

---

## Priority Actions

| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| 1 | Identifiser named buyer ({a['buyer']}) via LinkedIn og selskapets nettside | Jacob | Denne uken | Open |
| 2 | Research: siste nyheter, årsrapport, digital-strategi signaler | Jacob | Denne uken | Open |
| 3 | Vurder om account kvalifiserer for /account-setup for full research | Jacob | Uke 12 | Open |

---

## ICP / Deal Score

ICP: {a['icp']}/10 | Deal: {a['deal']}/10 | Prioritet: {priority_label(a['deal'])}

---

## Entry Offer

{a['entry']}
Est. verdi: {a['value']}
""", encoding="utf-8")

    # meetings.md
    (folder / "meetings.md").write_text(f"""# {a['name']} — Meetings

Last updated: {TODAY}

---

No meetings booked yet.

Status: Pre-outreach. Buyer not yet identified.

---

## Meeting Log

*(tom — ingen kontakt etablert)*
""", encoding="utf-8")

    return folder.name

# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n  JAKALA GTM OS — Batch Account Creator")
    print(f"  Oppretter {len(ACCOUNTS)} accounts i Accounts/\n")

    created = skipped = 0
    for a in ACCOUNTS:
        folder = BASE / a["folder"]
        if (folder / "overview.md").exists():
            # Sjekk om det allerede er en rik fil (ikke bare placeholder)
            content = (folder / "overview.md").read_text()
            if "research needed" not in content.lower() and len(content) > 500:
                print(f"  ↷  Springer over (eksisterer): {a['name']}")
                skipped += 1
                continue
        name = create_account(a)
        print(f"  ✓  {a['name']} ({a['country']}) — ICP {a['icp']} · Deal {a['deal']} · {a['gtm']}")
        created += 1

    print(f"\n  ──────────────────────────────────────")
    print(f"  Opprettet: {created} | Sprunget over: {skipped}")
    print(f"  ──────────────────────────────────────\n")
