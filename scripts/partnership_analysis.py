#!/usr/bin/env python3
"""
JAKALA GTM OS — Monthly Partnership Analysis
Runs first Monday of each month via GitHub Actions.
Generates intelligence/partnerships/monthly-YYYY-MM.md

Usage:
  python3 scripts/partnership_analysis.py
  python3 scripts/partnership_analysis.py --dry-run
"""

import os
import re
import sys
import argparse
from pathlib import Path
from datetime import date

import anthropic

BASE_DIR  = Path(__file__).parent.parent
INTEL_DIR = BASE_DIR / "intelligence"
OUT_DIR   = INTEL_DIR / "partnerships"

JAKALA_CONTEXT = """
JAKALA Nordic — GTM OS context:
- Geographic scope: Denmark (DK), Norway (NO), Sweden (SE)
- Core services: Commerce Experience (Shopify, commercetools), Product Experience / Speedtrain PIM,
  DXP / composable architecture, Generative AI Transformation, CDP/CRM, BI & Data Visualization,
  Data Architecture & Cloud, Pricing & Revenue Management, Hello Growth (SaaS)
- GTM strategies: Data Revenue Unlock · AI Readiness Accelerator · Commerce Optimization · Experience Transformation
- Buyer personas: CTO, CDO, CMO, Head of Ecommerce, Head of Data, CFO
- Active delivery: Maxbo (NO) — Speedtrain onboarding with Enterspeed
- Key accounts: Elkjøp, H&M, Matas, Trumf, Varner Group, Clas Ohlson, Boozt, Vinmonopolet, Skeidar, Jernia,
  Dustin Group, Ahlsell, Apotea, Salling Group, JYSK, Pandora, Bestseller

PARTNERSHIP SCORING CRITERIA (each 1-10):
1. GTM Fit — same buyer personas, complementary GTM strategies
2. Revenue Potential — joint pipeline, referrals, co-delivery, new account access
3. Market Positioning — enhances JAKALA credibility/reach in Nordic market
4. Channel Conflict Risk — lower score = more conflict (higher is better/safer)
5. Activation Speed — how fast to first tangible result
"""

PARTNER_CATEGORIES = {
    "Technology — Commerce Platforms": [
        "Shopify", "commercetools", "Salesforce Commerce Cloud", "Adobe Commerce / Magento",
        "Centra", "Fabric", "VTEX",
    ],
    "Technology — PIM / DAM": [
        "Akeneo", "inRiver", "Pimcore", "Stibo Systems", "Contentserv", "Bynder",
    ],
    "Technology — Composable / DXP": [
        "Contentful", "Contentstack", "Sanity", "Storyblok", "Optimizely", "Sitecore",
    ],
    "Technology — Search & Discovery": [
        "Algolia", "Elasticsearch / Elastic", "Constructor.io", "Bloomreach",
    ],
    "Technology — Personalisation / CDP": [
        "Dynamic Yield", "Bloomreach Engagement", "Segment", "mParticle", "Tealium", "Lytics",
    ],
    "Technology — AI / Data": [
        "Databricks", "Snowflake", "Azure AI / Microsoft", "Google Cloud AI",
        "SymphonyAI", "Vertex AI",
    ],
    "Technology — Nordic Specific": [
        "Enterspeed", "Sitoo", "RELEX Solutions", "Pricer", "Voyado", "Rule",
    ],
    "Platform — Marketplaces": [
        "Azure Marketplace (Microsoft)", "Google Cloud Marketplace", "AWS Marketplace",
    ],
    "Consulting / SI — Complementary": [
        "Capgemini", "Accenture (selected practices)", "PwC Digital", "McKinsey Digital",
    ],
}


def read(rel):
    p = BASE_DIR / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def get_pipeline_accounts():
    lines = []
    accounts_dir = BASE_DIR / "Accounts"
    for folder in sorted(accounts_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        ov = (folder / "overview.md").read_text(encoding="utf-8") if (folder / "overview.md").exists() else ""
        icp_m = re.search(r"ICP Score[:\s]+(\d+)/10", ov, re.I)
        icp   = int(icp_m.group(1)) if icp_m else 0
        if icp >= 7:
            lines.append(folder.name.replace("-", " ").title())
    return ", ".join(lines[:30])


def generate_analysis(today_str: str, dry_run: bool):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client   = anthropic.Anthropic(api_key=api_key)
    accounts = get_pipeline_accounts()
    month    = today_str[:7]  # YYYY-MM

    categories_str = "\n".join(
        f"**{cat}:** {', '.join(partners)}"
        for cat, partners in PARTNER_CATEGORIES.items()
    )

    prompt = f"""You are a senior JAKALA partnership strategist.
TODAY: {today_str}

{JAKALA_CONTEXT}

NORDIC PIPELINE ACCOUNTS (ICP 7+):
{accounts}

PARTNER UNIVERSE TO ANALYSE:
{categories_str}

Generate a monthly partnership analysis report in markdown. Structure:

# JAKALA Nordic — Monthly Partnership Analysis
## {month}

---

## Executive Summary
[3-4 sentences: top 3 recommended partnerships this month, total opportunity assessment]

---

## 🇳🇴 Norway — Top 3 Partner Opportunities

For each partner:
### [Partner Name] — [Partner Type]
**Score:** X/10 | **GTM match:** [strategies] | **Revenue type:** [referral/co-delivery/joint-pipeline]
**Why now:** [1-2 sentences specific to Norwegian market and pipeline]
**Best account fit:** [2-3 accounts from Norwegian pipeline]
**Joint offer:** [Specific combined offering]
**First step:** [Concrete action]

---

## 🇸🇪 Sweden — Top 3 Partner Opportunities
[Same format]

---

## 🇩🇰 Denmark — Top 3 Partner Opportunities
[Same format]

---

## 🌐 Nordic-Wide — Top 2 Strategic Partnerships
[Partners with pan-Nordic value — same format]

---

## Partnership Scorecard Summary

| Partner | Market | GTM Fit | Revenue | Positioning | Conflict Risk | Activation | Overall |
|---------|--------|---------|---------|-------------|---------------|------------|---------|
[Table with top 8 partners, scores 1-10 each, overall avg]

---

## Partners to Avoid This Quarter
[2-3 partners that seem obvious but carry channel conflict or positioning risk — explain why]

---

## Recommended Next Actions
1. [Most important partnership action this month]
2. [Second]
3. [Third]

---

Rules:
- Be specific — use real partner company names and capabilities
- Base account fit on the Nordic pipeline accounts listed
- Revenue type must be one of: referral, co-delivery, joint-pipeline, reseller, technology-integration
- Channel conflict risk: be honest — SI partners overlap with JAKALA delivery
- Keep total length readable in 5 minutes
- Prioritise partners that unlock H&M, Matas, Trumf, Elkjøp, or Boozt pipeline"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.content[0].text.strip()

    if dry_run:
        print(content)
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = OUT_DIR / f"monthly-{month}.md"
    fname.write_text(content, encoding="utf-8")
    print(f"  ✓  Partnership analysis written: {fname}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--date",    type=str, default=date.today().isoformat())
    args = parser.parse_args()

    print(f"\n  JAKALA GTM OS — Monthly Partnership Analysis")
    print(f"  Date: {args.date}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}\n")

    generate_analysis(args.date, args.dry_run)
    print()


if __name__ == "__main__":
    main()
