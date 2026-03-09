# Maxbo — Commercial Roadmap

Last updated: 2026-03-07

---

## Situasjon

Maxbo er i aktiv leveranse. Speedtrain onboarding starter mandag 09.03. To åpne scope-spørsmål blokkerer fremdrift: produktkategorisering (utenfor scope i dag) og Perfion write-back (tekniske krav ikke kartlagt). Ingen AI-lag eller personalisering er aktiv i dag.

**Pipeline:** €0 confirmed · Ekspansjonspotensial: €500K–900K over 18 måneder

---

## Roadmap — Fire Faser

---

### Fase 0 — Stabilisering (Nå → April 2026)

**Mål:** Få Speedtrain til å fungere i praksis og avklare scope-konflikten.

| Aksjon | Eier | Frist | Status |
|--------|------|-------|--------|
| Speedtrain walkthrough med Lars | Jacob + Lars | 09.03 | Planlagt |
| Avklare kategorisering: inn eller ut av scope? | Jacob + Enterspeed | Snarest | Åpen |
| Ny SOW / endringsordre ved scope-utvidelse | Jacob + Enterspeed | Etter avklaring | Venter |
| Kartlegge Perfion write-back krav | Jacob + Maxbo tech | Mars 2026 | Åpen |
| Bekrefte Perfion → Azure write-back løsning | Jacob + Enterspeed | April 2026 | Ikke startet |

**Suksesskriterium:** Lars jobber selvstendig i Speedtrain. Scope-konflikt løst. Perfion write-back i gang.

---

### Fase 1 — Data Revenue Diagnostic (April → Juni 2026)

**Mål:** Kvantifisere hvor produktdata-svikt koster Maxbo omsetning. Konvertere leveranseforholdet til et rådgivningsforhold.

**Kontekst:** 1 million produkter fordelt på et fire-lags system (Perfion → Azure → Pimcore → Magento). Selv liten datakvalitetssvikt på dette volumet gir målbar omsetningslekkasje i søk, discovery og konvertering.

| Aktivitet | Innhold |
|-----------|---------|
| Produktdata-revisjon | Kartlegg datakvalitet og fullstendighet per kategori |
| Pipeline-analyse | Identifiser tap-punkter i Perfion → Azure → Pimcore → Magento |
| Søk og discovery-test | Mål søkerelevans og konverteringseffekt av datasvikt |
| Revenue impact-estimat | Beregn NOK-verdien av identifiserte gap |
| Rapport og presentasjon | Lever funn til CTO / Head of Ecommerce |

**Forventet verdi:** €80–150K
**Neste buyer:** CTO eller Head of Ecommerce (i tillegg til Lars)

**Suksesskriterium:** Maxbo godkjenner diagnostikkrapport og etterspør neste fase.

---

### Fase 2 — Commerce Optimization (Juni → Oktober 2026)

**Mål:** Fikse de identifiserte data-gapene og forbedre søk, discovery og konvertering i nettbutikken.

| Aktivitet | Innhold |
|-----------|---------|
| Produktdata-enrichment i skala | Bruk Speedtrain til å berike og standardisere produktdata |
| Søkeoptimalisering | Forbedre relevans basert på riktig attributtdata |
| Kategorihierarki | Implementer produktkategorisering (Speedtrain-funksjon) |
| PIM-kvalitetsstyring | Etabler løpende datakvalitetsprosess i Perfion |
| Konverteringsmåling | Dokumenter omsetningseffekt av forbedringer |

**Forventet verdi:** €200–350K
**Expansion trigger:** Vellykket Fase 1 → naturlig utvidelse uten ny salgsprosess

**Suksesskriterium:** Målbar forbedring i søkerelevans og konvertering. CTO / Head of Ecommerce engasjert som kommersielle sponsorer.

---

### Fase 3 — AI Readiness (Oktober 2026 → Q1 2027)

**Mål:** Forberede Maxbo for AI-drevet personalisering og etterspørselsprognoser. Posisjonere JAKALA som strategisk partner for neste teknologigenerasjon.

**Kontekst:** Maxbo har ingen AI-lag i dag. RELEX brukes til supply chain. Pricer ESL-er er rullert ut. Grunnlaget for AI — ren, konsistent produktdata — bygges i Fase 1 og 2.

| Aktivitet | Innhold |
|-----------|---------|
| AI Readiness Diagnostic | Vurder beredskap for personalisering og AI-drevet søk |
| Personaliserings-roadmap | Definer use cases: produktanbefalinger, søk, kampanjer |
| Arkitekturvurdering | Vurder Magento-suksesjon og headless-strategi |
| Pilotdesign | Design og lever ett AI-drevet personaliserings-use case |

**Forventet verdi:** €250–400K
**Trigger:** Vellykket Fase 2 + intern AI-diskusjon hos Maxbo

**Suksesskriterium:** Maxbo vedtar AI-roadmap med JAKALA som leverandør av første use case.

---

### Fase 4 — Platform Modernization / DXP (2027+)

**Mål:** Magento-suksesjon og/eller DXP-transformasjon. Full omnichannel-plattform som understøtter Maxbos digitale ambisjon.

**Kontekst:** Magento er end-of-life i retning av Magento Open Source / Adobe Commerce veiskille. For en aktør med 1M produkter og et offensivt digitalt mål er plattformvalg et strategisk spørsmål.

| Aktivitet | Innhold |
|-----------|---------|
| Platform-evaluering | Vurder Adobe Commerce, Commercetools, eller headless alternativ |
| Arkitektur-blueprint | Design fremtidig tech-stack |
| Migreringsplan | Fase ut Magento / Pimcore til ny arkitektur |
| Implementering | DXP-program med JAKALA som lead |

**Forventet verdi:** €400–600K+
**Avhengighet:** Fase 3 fullført, C-suite sponsor (CEO/COO Løvenskiold Handel) aktivert

---

## Samlet Ekspansjonspotensial

| Fase | Tidsramme | Estimert Verdi |
|------|-----------|----------------|
| Fase 0 — Stabilisering | Nå → April 2026 | Inkludert i eksisterende avtale |
| Fase 1 — Data Revenue Diagnostic | April → Juni 2026 | €80–150K |
| Fase 2 — Commerce Optimization | Juni → Oktober 2026 | €200–350K |
| Fase 3 — AI Readiness | Oktober 2026 → Q1 2027 | €250–400K |
| Fase 4 — Platform Modernization | 2027+ | €400–600K+ |
| **Total 18-måneders potensial** | | **€530K–900K** |

---

## Kritiske Suksessfaktorer

1. **Lars må lykkes med Speedtrain** — Fase 0 er fundamentet. Feiler onboardingen, mister vi troverdighet.
2. **Scope-konflikt må løses** — Kategoriseringsspørsmålet må avklares av Jacob + Enterspeed nå, ikke utsettes.
3. **Nå CTO / Head of Ecommerce** — Lars er operasjonell kontakt. Vi trenger en kommersiell sponsor for Fase 1+.
4. **Koble leveranse til omsetning** — Posisjonér alt vi gjør som en revenue-diskusjon, ikke en IT-diskusjon.

---

## Risikoer

| Risiko | Sannsynlighet | Konsekvens | Tiltak |
|--------|---------------|------------|--------|
| Speedtrain-onboarding mislykkes | Lav | Høy | Grundig forberedelse til 09.03 |
| Kategorisering forblir utenfor scope | Medium | Medium | Ny SOW klar å presentere |
| Perfion write-back er mer kompleks enn antatt | Medium | Medium | Kartlegg tekniske krav tidlig |
| Lars mangler kapasitet til å prioritere | Medium | Høy | Sett klare milepæler og forvent framdrift |
| Ingen kommersiell sponsor over Lars | Medium | Høy | Mål å møte CTO i løpet av Fase 1 |
