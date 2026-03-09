#!/usr/bin/env python3
"""
JAKALA GTM OS — Monday.com Account Sync
Synkroniserer account-filer til "Jakala DXP: Global Sales Pipeline 2025"

Brug:
  python3 scripts/monday_sync.py --dry-run     # Se hvad der oprettes
  python3 scripts/monday_sync.py               # Opret i Monday.com
  python3 scripts/monday_sync.py --folder kingfisher  # Kun ét account
"""

import os
import re
import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import date

# ─── KONFIGURATION ────────────────────────────────────────────────────────────

API_KEY  = os.environ.get("MONDAY_API_KEY", "")
BOARD_ID = "18402701202"   # Jakala DXP: Global Sales Pipeline 2025
API_URL  = "https://api.monday.com/v2"

ACCOUNTS_DIR = Path(__file__).parent.parent / "Accounts"

# ─── KOLONNE-MAPPING (bekræftet fra board) ────────────────────────────────────

COLS = {
    "account_name_text": "text_mkvt6sr0",       # Account Name (text)
    "region":            "color_mkv8eq2p",       # Region (status)
    "priority":          "color_mktg57fn",       # Hi/Med/Lo (status)
    "est_value_eur":     "numeric_mkt9xbj",      # Est Value EUR (number)
    "quarter_to_win":    "dropdown_mkthtqk1",    # Est Quarter to Win (dropdown)
    "new_existing":      "color_mkthc6pq",       # New/Existing (status)
    "last_update":       "date_mkt98htg",        # Last Update (date)
    "notes":             "text_mkw92yh7",        # Text (GTM strategy + buyer)
}

# Region-mapping: land → Monday status-label
REGION_MAP = {
    "uk": "UK",
    "united kingdom": "UK",
    "london": "UK",
    "france": "France",
    "paris": "France",
    "norway": "Nordics",
    "sweden": "Nordics",
    "denmark": "Nordics",
    "finland": "Nordics",
    "nordics": "Nordics",
    "nordic": "Nordics",
    "netherlands": "Benelux",
    "belgium": "Benelux",
    "germany": "DACH",
    "spain": "South Europe",
    "italy": "South Europe",
    "global": "Global",
}

# ─── PARSING ──────────────────────────────────────────────────────────────────

def parse_account(folder: Path):
    overview_path    = folder / "overview.md"
    strategy_path    = folder / "strategy.md"
    stakeholder_path = folder / "stakeholders.md"

    if not overview_path.exists():
        return None

    overview     = overview_path.read_text(encoding="utf-8")
    strategy     = strategy_path.read_text(encoding="utf-8") if strategy_path.exists() else ""
    stakeholders = stakeholder_path.read_text(encoding="utf-8") if stakeholder_path.exists() else ""

    def extract(pattern, text, default=""):
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else default

    # Firmanavn
    name = extract(r"^#\s+(.+?)\s+[—–\-]", overview)
    if not name:
        name = folder.name.replace("-", " ").title()

    # Land / region
    country = extract(r"\|\s*HQ\s*\|\s*(.+?)\s*\|", overview)
    if not country:
        country = extract(r"\|\s*Country\s*\|\s*(.+?)\s*\|", overview)
    region = map_region(country)

    # ICP + Deal score
    icp_m  = re.search(r"ICP Score[:\s]+(\d+)/10", overview, re.IGNORECASE)
    deal_m = re.search(r"Deal Score[:\s]+(\d+)/10", overview, re.IGNORECASE)
    icp    = int(icp_m.group(1))  if icp_m  else 0
    deal   = int(deal_m.group(1)) if deal_m else 0

    # Hi/Med/Lo baseret på deal score
    if deal >= 9:
        priority = "Hi"
    elif deal >= 7:
        priority = "Med"
    else:
        priority = "Lo"

    # GTM Strategy
    gtm = extract(r"GTM Strategy[:\s*#]+(.+)", strategy)
    if not gtm:
        gtm = extract(r"##\s*GTM Strategy[:\s]+(.+)", strategy)

    # Est. value → tal i EUR
    est_eur = extract_value_eur(strategy)

    # Named buyer
    buyer_name  = extract(r"###\s+(.+)", stakeholders)
    buyer_title = extract(r"\*\*Title:\*\*\s*(.+)", stakeholders)
    if buyer_name:
        named_buyer = f"{buyer_name} — {buyer_title}" if buyer_title else buyer_name
    else:
        named_buyer = "TBD"

    # Notes-felt: GTM + buyer
    notes = ""
    if gtm:
        notes += f"GTM: {gtm[:120]}"
    if named_buyer:
        notes += f" | Buyer: {named_buyer[:80]}"

    return {
        "name":        name,
        "country":     country,
        "region":      region,
        "icp":         icp,
        "deal":        deal,
        "priority":    priority,
        "est_eur":     est_eur,
        "gtm":         gtm,
        "named_buyer": named_buyer,
        "notes":       notes.strip(),
        "folder":      folder.name,
    }


def map_region(country: str) -> str:
    key = country.lower().strip().split("/")[0].strip()
    for k, v in REGION_MAP.items():
        if k in key:
            return v
    return "Global"


def extract_value_eur(text: str) -> int:
    """Uddrager første EUR-beløb fra strategy.md og konverterer til heltal."""
    # Match mønstre som €75K, €900K, €1.2M, €50–100K
    patterns = [
        r"€([\d.]+)M",    # €1.2M
        r"€([\d,]+)K",    # €900K eller €75K
        r"€([\d,]+)",     # €50000
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "")
            val = float(raw)
            if "M" in p:
                return int(val * 1_000_000)
            elif "K" in p:
                return int(val * 1_000)
            else:
                return int(val)
    return 0


def load_all_accounts() -> list[dict]:
    accounts = []
    for folder in sorted(ACCOUNTS_DIR.iterdir()):
        if folder.is_dir() and not folder.name.startswith(".") and folder.name != "target-account-list.md":
            data = parse_account(folder)
            if data and data["name"]:
                accounts.append(data)
    return accounts


# ─── MONDAY.COM API ───────────────────────────────────────────────────────────

def gql(query: str, variables: dict = None) -> dict:
    headers = {
        "Authorization": API_KEY,
        "Content-Type":  "application/json",
        "API-Version":   "2024-01",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    r = requests.post(API_URL, headers=headers, json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()

    if "errors" in data:
        for e in data["errors"]:
            print(f"  ✗ API fejl: {e.get('message', e)}")
        return {}
    return data.get("data", {})


def get_existing_items() -> set[str]:
    query = """
    query ($board_id: ID!) {
      boards(ids: [$board_id]) {
        items_page(limit: 500) { items { name } }
      }
    }
    """
    data = gql(query, {"board_id": BOARD_ID})
    items = data.get("boards", [{}])[0].get("items_page", {}).get("items", [])
    return {item["name"] for item in items}


def build_column_values(account: dict) -> dict:
    today = date.today().isoformat()

    # Start med kun sikre felter (tekst, tal, dato)
    col_vals = {
        COLS["account_name_text"]: account["name"],
        COLS["last_update"]:       {"date": today},
    }

    if account["est_eur"] > 0:
        col_vals[COLS["est_value_eur"]] = account["est_eur"]

    if account["notes"]:
        col_vals[COLS["notes"]] = account["notes"][:500]

    return col_vals


def create_item(account: dict):
    mutation = """
    mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
      create_item(
        board_id: $board_id,
        item_name: $item_name,
        column_values: $column_values
      ) { id }
    }
    """
    col_vals = build_column_values(account)
    data = gql(mutation, {
        "board_id":      BOARD_ID,
        "item_name":     account["name"],
        "column_values": json.dumps(col_vals),
    })
    return data.get("create_item", {}).get("id")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",       action="store_true")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--folder",        type=str)
    args = parser.parse_args()

    accounts = load_all_accounts()
    if args.folder:
        accounts = [a for a in accounts if a["folder"] == args.folder]
        if not accounts:
            print(f"\n  ✗ Ingen account med folder-navn: {args.folder}\n")
            sys.exit(1)

    print(f"\n  JAKALA GTM OS → Monday.com")
    print(f"  Board: Jakala DXP: Global Sales Pipeline 2025 ({BOARD_ID})")
    print(f"  Accounts klar til sync: {len(accounts)}")
    print(f"  Mode: {'DRY RUN — ingenting oprettes' if args.dry_run else 'LIVE'}\n")

    if args.dry_run:
        print(f"  {'Account':<35} {'Region':<12} {'Deal':<6} {'Priority':<8} {'Est EUR':<12} {'Buyer'}")
        print(f"  {'-'*35} {'-'*12} {'-'*6} {'-'*8} {'-'*12} {'-'*35}")
        for a in accounts:
            est = f"€{a['est_eur']:,}" if a['est_eur'] else "—"
            buyer = (a['named_buyer'][:33] + "…") if len(a['named_buyer']) > 35 else a['named_buyer']
            print(f"  {a['name']:<35} {a['region']:<12} {a['deal']:<6} {a['priority']:<8} {est:<12} {buyer}")
        print(f"\n  Kør uden --dry-run for at oprette {len(accounts)} items.\n")
        return

    print("  Henter eksisterende items...")
    existing = get_existing_items()
    print(f"  {len(existing)} eksisterende items fundet.\n")

    created = skipped = failed = 0

    for account in accounts:
        if args.skip_existing and account["name"] in existing:
            print(f"  ↷  Springer over: {account['name']}")
            skipped += 1
            continue

        item_id = create_item(account)
        if item_id:
            est = f"€{account['est_eur']:,}" if account['est_eur'] else "—"
            print(f"  ✓  [{item_id}] {account['name']} · {account['region']} · {account['priority']} · {est}")
            created += 1
        else:
            print(f"  ✗  Fejl: {account['name']}")
            failed += 1

    print(f"\n  ─────────────────────────────────────")
    print(f"  Oprettet:       {created}")
    print(f"  Sprunget over:  {skipped}")
    print(f"  Fejl:           {failed}")
    print(f"  ─────────────────────────────────────\n")


if __name__ == "__main__":
    main()
