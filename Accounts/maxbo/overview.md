# Maxbo — Account Overview

## Company

| Attribute | Detail |
|---|---|
| Legal entity | Løvenskiold Handel AS (part of Løvenskiold Group) |
| Revenue | ~$539M (2025) |
| Employees | ~1,500 |
| Founded | 1995 |
| Headquarters | Dokka, Norway |
| Sector | Specialty Retail / Home Improvement & DIY |
| Model | Omnichannel — physical stores + ecommerce + click-and-collect + home delivery |

Norway's largest home improvement retail chain. Operates with a stated offensive digital strategy focused on omnichannel customer experience.

---

## Digital Ecosystem

| Layer | Technology |
|---|---|
| Ecommerce | Magento |
| PIM (commerce) | Pimcore |
| PIM (master data) | Perfion |
| Cloud | Azure (Perfion → Azure → webshop pipeline) |
| Supply Chain | RELEX Solutions |
| In-Store Pricing | Pricer ESLs (rollout completed 2024) |

**Product catalog:** 1 million products / 7 million items / 500 million attribute values managed in Perfion, flowing through Azure into Magento/Pimcore.

**Key risk signal:** Multi-hop data pipeline (Perfion → Azure → Pimcore → Magento) creates high risk of data inconsistency at scale. No visible AI or personalization layer.

---

## ICP Score: 9/10 — Ideal ICP

| Criterion | Score | Rationale |
|---|---|---|
| Industry Fit | 2/2 | Retail, high-SKU ecommerce — exact ICP |
| Data Complexity | 2/2 | 1M+ products, multi-system pipeline |
| AI Potential | 1/2 | No visible AI initiatives, strong latent potential |
| Architecture Complexity | 2/2 | Magento + Pimcore + Perfion + Azure + RELEX + ESLs |
| Revenue Impact | 2/2 | $539M revenue, digital is core to strategy |

---

## Deal Score: 8/10 — Strong Opportunity

| Criterion | Score | Note |
|---|---|---|
| Strategic Fit | 2/2 | Textbook high-SKU retail ICP |
| Problem Urgency | 1.5/2 | Data pipeline fragmentation real but not stated as crisis |
| Entry Wedge Clarity | 2/2 | Data Revenue Diagnostic fits precisely |
| Buyer Strength | 1.5/2 | Buyer roles identifiable, no warm contact yet |
| Expansion Potential | 2/2 | Data → commerce optimization → AI → platform modernization |

---

## GTM Strategy

**Primary: Strategy 1 — Data Revenue Unlock**
**Secondary: Strategy 3 — Commerce Optimization**

At 1M products across a 3-layer pipeline, even marginal data quality degradation translates into significant revenue loss through failed search, poor discovery, and conversion drop-off.

**Entry offer:** Data Revenue Diagnostic

> "With 1 million products across a multi-system pipeline, product data inconsistency is silently costing you revenue in search, discovery, and conversion. A focused diagnostic will quantify where the leakage is and what fixing it is worth."

**Expansion path:** Commerce optimization → AI readiness → DXP / platform modernization (Magento succession)

---

## Buyer Map

| Role | Type | Priority |
|---|---|---|
| CTO / Head of Technology | Technical buyer | High — owns the data pipeline stack |
| Head of Ecommerce / Digital Director | Commercial buyer | High — owns omnichannel strategy and conversion |
| Head of Product Data / PIM Owner | Technical buyer | Medium — manages Perfion, likely aware of data quality issues |
| CEO / COO (Løvenskiold Handel) | Strategic sponsor | Low initially — needed for transformation sign-off |

---

## Status

- Stage: Research / Pre-outreach
- No active contact or meeting
- Last updated: 2026-03-07
