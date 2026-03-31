#!/usr/bin/env python3
"""
JAKALA GTM OS — CEO Morning Brief
Runs every Monday at 07:00 CET via GitHub Actions.
Reads all pipeline/account data, calls Claude API to synthesise,
formats as a beautiful HTML email and sends via SendGrid.

Usage:
  python3 scripts/morning_brief.py              # Generate + send
  python3 scripts/morning_brief.py --dry-run    # Print HTML to stdout, no send
  python3 scripts/morning_brief.py --preview    # Save HTML to /tmp/brief-preview.html
"""

import os, re, sys, argparse, json
from pathlib import Path
from datetime import date, timedelta
import anthropic

BASE_DIR     = Path(__file__).parent.parent
ACCOUNTS_DIR = BASE_DIR / "Accounts"
INTEL_DIR    = BASE_DIR / "intelligence"
LEADS_DIR    = INTEL_DIR / "daily-leads"

TODAY        = date.today()
WEEK_NUM     = TODAY.isocalendar()[1]
MONDAY_DATE  = TODAY - timedelta(days=TODAY.weekday())  # This Monday

def read(rel):
    p = BASE_DIR / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""

# ─── 1. Gather intelligence ───────────────────────────────────────────────────

def load_context():
    parts = []

    # Core intelligence files
    for f in ["intelligence/top-opportunities.md",
              "intelligence/weekly-summary.md",
              "intelligence/pipeline-dashboard.md"]:
        content = read(f)
        if content:
            parts.append(f"=== {f} ===\n{content}\n")

    # 3 most recent daily leads
    lead_files = sorted(LEADS_DIR.glob("*.md"), reverse=True)[:3]
    for lf in lead_files:
        parts.append(f"=== daily-leads/{lf.name} ===\n{lf.read_text()}\n")

    # Active account summaries (ICP 7+ only)
    account_summaries = []
    for folder in sorted(ACCOUNTS_DIR.iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        ov_path = folder / "overview.md"
        na_path = folder / "next-actions.md"
        st_path = folder / "strategy.md"

        if not ov_path.exists():
            continue

        ov = ov_path.read_text(encoding="utf-8")
        icp_m  = re.search(r"ICP Score[:\s]+(\d+)/10", ov, re.I)
        deal_m = re.search(r"Deal Score[:\s]+(\d+)/10", ov, re.I)
        icp  = int(icp_m.group(1)) if icp_m else 0
        deal = int(deal_m.group(1)) if deal_m else 0

        if icp < 7 and deal < 7:
            continue

        na = na_path.read_text(encoding="utf-8") if na_path.exists() else ""
        st = st_path.read_text(encoding="utf-8") if st_path.exists() else ""

        # Extract deal value
        val_m = re.search(r"€[\d\w\s\–\-\.K]+", st)
        value = val_m.group(0).strip() if val_m else "TBD"

        # Extract buyer
        buyer = "TBD"
        bm = re.search(r"\*\*(.+?)\*\*.*?(?:CDO|CMO|CTO|CEO|Director|MD|Head)", st)
        if bm:
            buyer = bm.group(0)[:60]

        account_summaries.append(
            f"Account: {folder.name} | ICP: {icp} | Deal: {deal} | Value: {value}\n"
            f"Next actions:\n{na[:400]}\n"
        )

    if account_summaries:
        parts.append("=== ACTIVE ACCOUNTS (ICP 7+) ===\n" + "\n---\n".join(account_summaries))

    return "\n\n".join(parts)


# ─── 2. Generate brief with Claude ───────────────────────────────────────────

PROMPT = """You are the Chief Commercial Officer of JAKALA Nordic (Denmark, Norway, Sweden only).
Today is {today}. It is Monday morning — Week {week}.

Læs alle pipeline- og account-data nedenfor og skriv et CEO Morning Brief.
Det sendes til CCO og MD hver mandag kl. 07:00.
Det skal være skarpt, board-klart og læsbart på under 3 minutter.
SKRIV ALT INDHOLD PÅ DANSK — alle sætninger, beskrivelser og handlinger skal være på dansk.

OUTPUT FORMAT — Return valid JSON only. No markdown, no explanation. Just JSON.

{{
  "status": "Green|Amber|Red",
  "status_reason": "Én sætning på dansk",
  "pipeline_total": "€X",
  "pipeline_weighted": "€X",
  "base_case_forecast": "€X",
  "week_headline": "Én skarp sætning på dansk — hvad er den kommercielle situation denne uge?",
  "situation_60s": "Maks 3 sætninger på dansk. Hvor er vi? Hvad er den vigtigste risiko eller mulighed? Hvad skal ske denne uge?",
  "top_priorities": [
    {{"rank": 1, "account": "", "action": "dansk handlingsbeskrivelse", "owner": "Jacob Skaue", "by_when": "dansk ugedag", "why": "dansk begrundelse"}},
    {{"rank": 2, "account": "", "action": "dansk handlingsbeskrivelse", "owner": "Jacob Skaue", "by_when": "dansk ugedag", "why": "dansk begrundelse"}},
    {{"rank": 3, "account": "", "action": "dansk handlingsbeskrivelse", "owner": "Jacob Skaue", "by_when": "dansk ugedag", "why": "dansk begrundelse"}}
  ],
  "hot_signals": [
    {{"account": "", "signal": "dansk beskrivelse", "action": "dansk handling", "urgency": "I dag|Denne uge|Denne måned"}},
    {{"account": "", "signal": "dansk beskrivelse", "action": "dansk handling", "urgency": "I dag|Denne uge|Denne måned"}},
    {{"account": "", "signal": "dansk beskrivelse", "action": "dansk handling", "urgency": "I dag|Denne uge|Denne måned"}}
  ],
  "pipeline_scorecard": [
    {{"account": "", "win_pct": "", "weighted": "", "status": "Active|Stalled|Ready", "next_action": "dansk handling"}},
    {{"account": "", "win_pct": "", "weighted": "", "status": "Active|Stalled|Ready", "next_action": "dansk handling"}},
    {{"account": "", "win_pct": "", "weighted": "", "status": "Active|Stalled|Ready", "next_action": "dansk handling"}},
    {{"account": "", "win_pct": "", "weighted": "", "status": "Active|Stalled|Ready", "next_action": "dansk handling"}},
    {{"account": "", "win_pct": "", "weighted": "", "status": "Active|Stalled|Ready", "next_action": "dansk handling"}},
    {{"account": "", "win_pct": "", "weighted": "", "status": "Active|Stalled|Ready", "next_action": "dansk handling"}}
  ],
  "biggest_risk": "Én sætning på dansk — specifik account, specifik trussel",
  "biggest_opportunity": "Én sætning på dansk — specifik account, specifik handling der kan tages i dag",
  "verdict": "Én sætning på dansk — det vigtigste at gøre denne uge",
  "forecast": {{
    "best_case": "€X",
    "base_case": "€X",
    "worst_case": "€X",
    "confidence": "Høj|Medium|Lav",
    "confidence_note": "Én sætning på dansk om hvad der ændrer tallet"
  }}
}}

REGLER:
- Kun Norden (NO, DK, SE). Medtag ikke UK eller Frankrig.
- Opfind aldrig signaler — brug kun hvad der er i data.
- Status Rød = base case i fare. Amber = én stor deal stalled. Grøn = på sporet.
- Vær brutalt ærlig. En CCO læser dette kl. 07:00 og skal beslutte hvad der sker i dag.

=== PIPELINE AND ACCOUNT DATA ===
{context}
"""

def generate_brief(context: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": PROMPT.format(
                today=TODAY.strftime("%A %d %B %Y"),
                week=WEEK_NUM,
                context=context[:80000],
            )
        }]
    )
    raw = msg.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


# ─── 3. Render HTML email ─────────────────────────────────────────────────────

STATUS_COLORS = {"Green": "#1a7a4a", "Amber": "#b87800", "Red": "#c0392b"}
STATUS_BG     = {"Green": "#edfaf3", "Amber": "#fff8e6", "Red": "#fdf0ef"}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="da">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>JAKALA Nordic — CCO Briefing</title>
<style>
  @page {{ size:A4; margin:0; }}
  *  {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:#ffffff;
    color:#0f0f1a;
    font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
    font-size:13px;
    line-height:1.6;
    -webkit-print-color-adjust:exact;
    print-color-adjust:exact;
  }}
  .page {{ max-width:760px; margin:0 auto; }}

  /* ══ COVER HEADER ══ */
  .cover {{
    background:#020266;
    padding:32px 44px 30px;
    position:relative;
    overflow:hidden;
  }}
  .cover::before {{
    content:'';
    position:absolute;
    top:0; right:0;
    width:340px; height:100%;
    background:linear-gradient(135deg, rgba(21,62,237,0.18) 0%, transparent 60%);
    pointer-events:none;
  }}
  .cover-top {{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    margin-bottom:28px;
  }}
  .wordmark {{
    font-size:17px;
    font-weight:800;
    color:#ffffff;
    letter-spacing:3px;
    text-transform:uppercase;
  }}
  .wordmark span {{ color:#153EED; }}
  .cover-meta {{
    text-align:right;
  }}
  .cover-meta .label {{
    font-size:9px;
    font-weight:700;
    color:rgba(255,255,255,0.45);
    text-transform:uppercase;
    letter-spacing:2px;
    margin-bottom:3px;
  }}
  .cover-meta .week-date {{
    font-size:12px;
    color:rgba(255,255,255,0.85);
    font-weight:500;
  }}

  .cover-headline {{
    font-size:26px;
    font-weight:800;
    color:#ffffff;
    line-height:1.25;
    max-width:600px;
    margin-bottom:22px;
    letter-spacing:-0.3px;
  }}

  .status-row {{
    display:flex;
    align-items:center;
    gap:16px;
  }}
  .status-chip {{
    display:inline-flex;
    align-items:center;
    gap:7px;
    background:rgba(255,255,255,0.1);
    border:1px solid rgba(255,255,255,0.2);
    border-radius:20px;
    padding:5px 13px 5px 9px;
  }}
  .dot {{
    width:7px; height:7px;
    border-radius:50%;
    flex-shrink:0;
  }}
  .dot-green  {{ background:#22DD88; box-shadow:0 0 6px rgba(34,221,136,0.7); }}
  .dot-amber  {{ background:#FFBB33; box-shadow:0 0 6px rgba(255,187,51,0.7); }}
  .dot-red    {{ background:#F6574A; box-shadow:0 0 6px rgba(246,87,74,0.7); }}
  .chip-status {{
    font-size:10px;
    font-weight:800;
    color:#ffffff;
    text-transform:uppercase;
    letter-spacing:0.8px;
  }}
  .chip-reason {{
    font-size:12px;
    color:rgba(255,255,255,0.7);
    margin-left:2px;
  }}

  /* ══ KPI STRIP ══ */
  .kpi-strip {{
    display:flex;
    border-bottom:1px solid #ebebf5;
  }}
  .kpi-cell {{
    flex:1;
    padding:22px 24px;
    border-right:1px solid #ebebf5;
    position:relative;
  }}
  .kpi-cell:last-child {{ border-right:none; }}
  .kpi-cell::before {{
    content:'';
    position:absolute;
    top:0; left:24px; right:24px;
    height:2px;
  }}
  .kpi-cell.blue::before  {{ background:#153EED; }}
  .kpi-cell.amber::before {{ background:#b87800; }}
  .kpi-cell.green::before {{ background:#1a7a4a; }}
  .kpi-num {{
    font-size:28px;
    font-weight:800;
    letter-spacing:-0.5px;
    line-height:1;
    margin-bottom:5px;
  }}
  .kpi-cell.blue  .kpi-num {{ color:#153EED; }}
  .kpi-cell.amber .kpi-num {{ color:#b87800; }}
  .kpi-cell.green .kpi-num {{ color:#1a7a4a; }}
  .kpi-lbl {{
    font-size:9.5px;
    font-weight:600;
    color:#999;
    text-transform:uppercase;
    letter-spacing:1px;
  }}

  /* ══ BODY SECTIONS ══ */
  .body-section {{
    padding:26px 44px;
    border-bottom:1px solid #ebebf5;
  }}
  .body-section:last-child {{ border-bottom:none; }}

  .sec-label {{
    font-size:8.5px;
    font-weight:800;
    color:#153EED;
    text-transform:uppercase;
    letter-spacing:2.5px;
    margin-bottom:16px;
    display:flex;
    align-items:center;
    gap:10px;
  }}
  .sec-label::after {{
    content:'';
    flex:1;
    height:1px;
    background:#ebebf5;
  }}

  /* ══ SITUATION ══ */
  .situation-text {{
    font-size:14.5px;
    color:#1a1a2e;
    line-height:1.8;
    max-width:640px;
  }}

  /* ══ PRIORITIES ══ */
  .priority-item {{
    display:flex;
    gap:18px;
    padding:13px 0;
    border-bottom:1px solid #f4f4fa;
    align-items:flex-start;
  }}
  .priority-item:last-child {{ border-bottom:none; }}
  .p-num {{
    font-size:22px;
    font-weight:800;
    color:#e0e4f8;
    line-height:1;
    min-width:28px;
    padding-top:2px;
  }}
  .p-bar {{
    width:2px;
    min-height:48px;
    background:#153EED;
    border-radius:1px;
    flex-shrink:0;
    margin-top:3px;
  }}
  .p-content {{ flex:1; }}
  .p-account {{
    font-size:14px;
    font-weight:800;
    color:#0f0f1a;
    margin-bottom:3px;
  }}
  .p-action {{
    font-size:13px;
    color:#3a3a5e;
    line-height:1.5;
  }}
  .p-meta {{
    font-size:10.5px;
    color:#aaa;
    margin-top:4px;
  }}
  .p-when {{
    font-size:10.5px;
    font-weight:700;
    color:#153EED;
    text-align:right;
    white-space:nowrap;
    padding-top:2px;
  }}

  /* ══ SIGNALS ══ */
  .signal-item {{
    display:flex;
    gap:14px;
    padding:11px 0;
    border-bottom:1px solid #f4f4fa;
    align-items:flex-start;
  }}
  .signal-item:last-child {{ border-bottom:none; }}
  .signal-dot {{
    width:8px; height:8px;
    border-radius:50%;
    flex-shrink:0;
    margin-top:5px;
  }}
  .signal-content {{ flex:1; }}
  .sig-top {{ display:flex; align-items:center; gap:8px; margin-bottom:3px; }}
  .sig-account {{ font-size:13px; font-weight:700; color:#0f0f1a; }}
  .sig-text   {{ font-size:12px; color:#4a4a6a; line-height:1.5; }}
  .sig-action {{ font-size:12px; color:#153EED; font-weight:600; margin-top:4px; }}

  /* ══ BADGES ══ */
  .badge {{
    display:inline-block;
    padding:2px 9px;
    border-radius:10px;
    font-size:9px;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:0.5px;
  }}
  .b-red   {{ background:#fdf0ef; color:#c0392b; border:1px solid rgba(192,57,43,0.2); }}
  .b-amber {{ background:#fff8e6; color:#b87800; border:1px solid rgba(184,120,0,0.2); }}
  .b-blue  {{ background:#eff3ff; color:#153EED; border:1px solid rgba(21,62,237,0.2); }}
  .b-green {{ background:#edfaf3; color:#1a7a4a; border:1px solid rgba(26,122,74,0.2); }}

  /* ══ SCORECARD ══ */
  .scorecard {{ width:100%; border-collapse:collapse; }}
  .scorecard thead tr {{
    border-bottom:2px solid #0f0f1a;
  }}
  .scorecard th {{
    padding:7px 10px;
    text-align:left;
    font-size:9px;
    font-weight:800;
    color:#999;
    text-transform:uppercase;
    letter-spacing:1px;
  }}
  .scorecard tbody tr {{
    border-bottom:1px solid #f4f4fa;
    transition:background 0.1s;
  }}
  .scorecard tbody tr:last-child {{ border-bottom:none; }}
  .scorecard tbody tr:nth-child(even) {{ background:#fafafe; }}
  .scorecard td {{
    padding:10px 10px;
    font-size:12.5px;
    color:#2a2a3e;
    vertical-align:middle;
  }}
  .sc-account {{ font-weight:700; color:#0f0f1a; }}
  .sc-value   {{ font-weight:700; color:#153EED; }}

  /* ══ RISK + OPP ══ */
  .risk-opp-row {{ display:flex; gap:14px; }}
  .callout {{
    flex:1;
    padding:14px 16px;
    border-radius:6px;
  }}
  .callout-r {{
    background:#fdf0ef;
    border-left:3px solid #c0392b;
  }}
  .callout-g {{
    background:#edfaf3;
    border-left:3px solid #1a7a4a;
  }}
  .callout-label {{
    font-size:8.5px;
    font-weight:800;
    text-transform:uppercase;
    letter-spacing:1.5px;
    margin-bottom:6px;
  }}
  .callout-r .callout-label {{ color:#c0392b; }}
  .callout-g .callout-label {{ color:#1a7a4a; }}
  .callout-text {{
    font-size:12.5px;
    line-height:1.6;
    color:#2a2a3e;
  }}

  /* ══ FORECAST ══ */
  .forecast-nums {{
    display:flex;
    margin-top:16px;
  }}
  .fc-cell {{
    flex:1;
    text-align:center;
    padding:14px 10px;
    border-radius:6px;
  }}
  .fc-cell.fc-base {{
    background:#f0f3ff;
    border:1.5px solid #153EED;
    transform:scale(1.02);
  }}
  .fc-num {{
    font-size:22px;
    font-weight:800;
    line-height:1;
    letter-spacing:-0.5px;
  }}
  .fc-cell.fc-worst .fc-num {{ color:#c0392b; }}
  .fc-cell.fc-base  .fc-num {{ color:#153EED; font-size:26px; }}
  .fc-cell.fc-best  .fc-num {{ color:#1a7a4a; }}
  .fc-lbl {{
    font-size:9px;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:1px;
    margin-top:5px;
    color:#999;
  }}
  .fc-note {{
    font-size:11px;
    color:#bbb;
    font-style:italic;
    margin-top:12px;
    text-align:center;
  }}

  /* ══ VERDICT ══ */
  .verdict-box {{
    background:#020266;
    padding:24px 30px;
    border-radius:6px;
    display:flex;
    align-items:flex-start;
    gap:18px;
  }}
  .verdict-accent {{
    width:3px;
    min-height:48px;
    background:#153EED;
    border-radius:2px;
    flex-shrink:0;
  }}
  .verdict-inner {{ flex:1; }}
  .verdict-label {{
    font-size:8.5px;
    font-weight:800;
    color:rgba(255,255,255,0.45);
    text-transform:uppercase;
    letter-spacing:2px;
    margin-bottom:8px;
  }}
  .verdict-text {{
    font-size:16px;
    font-weight:700;
    color:#ffffff;
    line-height:1.5;
  }}

  /* ══ FOOTER ══ */
  .footer {{
    padding:14px 44px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    border-top:1px solid #ebebf5;
    background:#fafafe;
  }}
  .footer-left {{ font-size:11px; font-weight:800; color:#020266; letter-spacing:1.5px; }}
  .footer-right {{ font-size:10px; color:#bbb; }}
</style>
</head>
<body>
<div class="page">

  <!-- ══ COVER ══ -->
  <div class="cover">
    <div class="cover-top">
      <div class="wordmark">JAK<span>A</span>LA</div>
      <div class="cover-meta">
        <div class="label">CCO Briefing &nbsp;·&nbsp; Uge {week_num}</div>
        <div class="week-date">{date_str}</div>
      </div>
    </div>
    <div class="cover-headline">{week_headline}</div>
    <div class="status-row">
      <div class="status-chip">
        <div class="dot dot-{status_dot}"></div>
        <span class="chip-status">{status}</span>
        <span class="chip-reason">&nbsp;—&nbsp;{status_reason}</span>
      </div>
    </div>
  </div>

  <!-- ══ KPI STRIP ══ -->
  <div class="kpi-strip">
    <div class="kpi-cell blue">
      <div class="kpi-num">{pipeline_total}</div>
      <div class="kpi-lbl">Total pipeline</div>
    </div>
    <div class="kpi-cell amber">
      <div class="kpi-num">{pipeline_weighted}</div>
      <div class="kpi-lbl">Sandsynlighedsvægtet</div>
    </div>
    <div class="kpi-cell green">
      <div class="kpi-num">{base_case_forecast}</div>
      <div class="kpi-lbl">Base case Q2</div>
    </div>
  </div>

  <!-- ══ PIPELINE VIZ ══ -->
  <div class="body-section" style="padding-bottom:18px;">
    <div class="sec-label">Pipeline</div>
    {svg_funnel}
    <div style="margin-top:12px;">{svg_quarter}</div>
  </div>

  <!-- ══ SITUATION ══ -->
  <div class="body-section">
    <div class="sec-label">Situationen &mdash; 60 sekunder</div>
    <div class="situation-text">{situation_60s}</div>
  </div>

  <!-- ══ PRIORITETER ══ -->
  <div class="body-section">
    <div class="sec-label">Top 3 prioriteter denne uge</div>
    {priorities_html}
  </div>

  <!-- ══ SIGNALER ══ -->
  <div class="body-section">
    <div class="sec-label">Varme signaler</div>
    {signals_html}
  </div>

  <!-- ══ SCORECARD ══ -->
  <div class="body-section">
    <div class="sec-label">Pipeline Scorecard</div>
    <table class="scorecard">
      <thead><tr>
        <th>Account</th><th>Win %</th><th>Vægtet</th><th>Status</th><th>Næste skridt</th>
      </tr></thead>
      <tbody>{scorecard_rows}</tbody>
    </table>
  </div>

  <!-- ══ RISIKO & MULIGHED ══ -->
  <div class="body-section">
    <div class="sec-label">Risiko &amp; Mulighed</div>
    <div class="risk-opp-row">
      <div class="callout callout-r">
        <div class="callout-label">Største risiko</div>
        <div class="callout-text">{biggest_risk}</div>
      </div>
      <div class="callout callout-g">
        <div class="callout-label">Største mulighed</div>
        <div class="callout-text">{biggest_opportunity}</div>
      </div>
    </div>
  </div>

  <!-- ══ FORECAST ══ -->
  <div class="body-section">
    <div class="sec-label">Forecast</div>
    {svg_forecast}
    <div class="forecast-nums">
      <div class="fc-cell fc-worst">
        <div class="fc-num">{forecast_worst}</div>
        <div class="fc-lbl">Worst case</div>
      </div>
      <div class="fc-cell fc-base">
        <div class="fc-num">{forecast_base}</div>
        <div class="fc-lbl">Base case &nbsp;<span class="badge b-{confidence_badge}">{forecast_confidence}</span></div>
      </div>
      <div class="fc-cell fc-best">
        <div class="fc-num">{forecast_best}</div>
        <div class="fc-lbl">Best case</div>
      </div>
    </div>
    <div class="fc-note">{confidence_note}</div>
  </div>

  <!-- ══ VERDICT ══ -->
  <div class="body-section">
    <div class="sec-label">Verdict</div>
    <div class="verdict-box">
      <div class="verdict-accent"></div>
      <div class="verdict-inner">
        <div class="verdict-label">Det vigtigste at gøre denne uge</div>
        <div class="verdict-text">{verdict}</div>
      </div>
    </div>
  </div>

  <!-- ══ FOOTER ══ -->
  <div class="footer">
    <div class="footer-left">JAKALA &nbsp;NORDIC</div>
    <div class="footer-right">Auto-genereret {date_str} &nbsp;·&nbsp; Fortroligt &nbsp;·&nbsp; Kun til intern brug</div>
  </div>

</div>
</body>
</html>"""


# ─── SVG Visualisations ───────────────────────────────────────────────────────

def parse_eur(s: str) -> float:
    """Parse '€1.62M' → 1_620_000, '€420K' → 420_000, '€420' → 420"""
    s = str(s).replace("€","").replace(",","").strip()
    try:
        if s.upper().endswith("M"): return float(s[:-1]) * 1_000_000
        if s.upper().endswith("K"): return float(s[:-1]) * 1_000
        return float(s)
    except ValueError:
        return 0.0

def fmt_eur(v: float) -> str:
    if v >= 1_000_000: return f"€{v/1_000_000:.1f}M"
    if v >= 1_000:     return f"€{v/1_000:.0f}K"
    return f"€{v:.0f}"

def svg_pipeline_funnel(total: str, weighted: str, base_case: str) -> str:
    """Horizontal funnel — light theme"""
    W, H = 668, 118
    BAR_H, GAP, BAR_X = 26, 12, 160

    t = parse_eur(total);    t_label = fmt_eur(t)
    w = parse_eur(weighted); w_label = fmt_eur(w)
    b = parse_eur(base_case);b_label = fmt_eur(b)
    peak = max(t, 1)
    MAX_W = W - BAR_X - 10

    bars = [
        (t, t_label, "#153EED", "Total pipeline"),
        (w, w_label, "#b87800", "Sandsynlighedsvægtet"),
        (b, b_label, "#1a7a4a", "Base case forecast"),
    ]
    track_colors = ["#e8eeff", "#fff8e6", "#edfaf3"]

    svg  = f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:Helvetica Neue,Arial,sans-serif;">'
    for i, ((val, label_val, color, label_text), track_c) in enumerate(zip(bars, track_colors)):
        y = 10 + i * (BAR_H + GAP)
        bar_w = max(int((val / peak) * MAX_W), 4)

        svg += f'<rect x="{BAR_X}" y="{y}" width="{MAX_W}" height="{BAR_H}" fill="{track_c}" rx="4"/>'
        svg += f'<rect x="{BAR_X}" y="{y}" width="{bar_w}" height="{BAR_H}" fill="{color}" rx="4" opacity="0.85"/>'
        # label left
        svg += f'<text x="{BAR_X - 8}" y="{y + BAR_H//2 + 5}" fill="#555" font-size="11" text-anchor="end">{label_text}</text>'
        # value right of bar
        v_x = BAR_X + bar_w + 8
        svg += f'<text x="{v_x}" y="{y + BAR_H//2 + 5}" fill="{color}" font-size="12" font-weight="bold">{label_val}</text>'
        # pct inside if wide enough
        if bar_w > 60:
            pct_val = int(val / peak * 100)
            svg += f'<text x="{BAR_X + bar_w - 8}" y="{y + BAR_H//2 + 4}" fill="rgba(255,255,255,0.7)" font-size="9" text-anchor="end">{pct_val}%</text>'

    svg += '</svg>'
    return svg


def svg_forecast_range(worst: str, base: str, best: str) -> str:
    """Forecast range bar — light theme"""
    W, H = 668, 68
    TRACK_Y, TRACK_H = 22, 10
    TRACK_X, TRACK_W = 50, 568

    w_val = parse_eur(worst)
    b_val = parse_eur(base)
    g_val = parse_eur(best)
    peak  = max(g_val, 1)

    def px(v): return TRACK_X + int((v / peak) * TRACK_W)
    w_px = px(w_val); b_px = px(b_val); g_px = px(g_val)

    svg  = f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:Helvetica Neue,Arial,sans-serif;">'
    svg += '<defs>'
    svg += '<linearGradient id="fgr" x1="0%" y1="0%" x2="100%" y2="0%">'
    svg += '<stop offset="0%" style="stop-color:#c0392b;stop-opacity:0.3"/>'
    svg += '<stop offset="50%" style="stop-color:#b87800;stop-opacity:0.35"/>'
    svg += '<stop offset="100%" style="stop-color:#1a7a4a;stop-opacity:0.4"/>'
    svg += '</linearGradient></defs>'

    # Track
    svg += f'<rect x="{TRACK_X}" y="{TRACK_Y}" width="{TRACK_W}" height="{TRACK_H}" fill="#f0f0f8" rx="5"/>'
    svg += f'<rect x="{w_px}" y="{TRACK_Y}" width="{g_px - w_px}" height="{TRACK_H}" fill="url(#fgr)" rx="5"/>'

    # Base marker (vertical line + diamond)
    mid_y = TRACK_Y + TRACK_H // 2
    svg += f'<rect x="{b_px - 1}" y="{TRACK_Y - 4}" width="3" height="{TRACK_H + 8}" fill="#153EED" rx="1"/>'
    svg += f'<circle cx="{b_px}" cy="{mid_y}" r="6" fill="#153EED"/>'

    # Values
    for val_px, label, color, anchor in [
        (w_px, fmt_eur(w_val), "#c0392b", "middle"),
        (b_px, fmt_eur(b_val), "#153EED", "middle"),
        (g_px, fmt_eur(g_val), "#1a7a4a", "middle"),
    ]:
        svg += f'<text x="{val_px}" y="{TRACK_Y + TRACK_H + 16}" fill="{color}" font-size="11" font-weight="bold" text-anchor="{anchor}">{label}</text>'
    for val_px, lbl, anchor in [
        (w_px, "Worst case", "middle"),
        (b_px, "Base case", "middle"),
        (g_px, "Best case", "middle"),
    ]:
        svg += f'<text x="{val_px}" y="{TRACK_Y + TRACK_H + 30}" fill="#aaa" font-size="9" text-anchor="{anchor}">{lbl}</text>'

    svg += '</svg>'
    return svg


def svg_probability_bar(pct_str: str) -> str:
    """Inline probability bar — light theme"""
    W, H = 90, 14
    try:
        pct = float(str(pct_str).replace("%","").strip()) / 100
    except ValueError:
        pct = 0.0
    color     = "#1a7a4a" if pct >= 0.6 else ("#b87800" if pct >= 0.4 else "#c0392b")
    track_col = "#edfaf3" if pct >= 0.6 else ("#fff8e6" if pct >= 0.4 else "#fdf0ef")
    fill_w = max(int(pct * W), 2)
    svg  = f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;margin-right:6px;">'
    svg += f'<rect width="{W}" height="{H}" fill="{track_col}" rx="3"/>'
    svg += f'<rect width="{fill_w}" height="{H}" fill="{color}" rx="3" opacity="0.8"/>'
    svg += f'<text x="{W//2}" y="{H - 3}" fill="{"#fff" if fill_w > 40 else color}" font-size="8" font-weight="bold" text-anchor="middle">{pct_str}</text>'
    svg += '</svg>'
    return svg


def svg_quarter_progress() -> str:
    """Quarter progress — light theme"""
    import calendar
    W, H = 668, 38
    TRACK_X, TRACK_W, TRACK_Y, TRACK_H = 0, 668, 22, 7

    m = TODAY.month
    q = (m - 1) // 3 + 1
    q_start     = date(TODAY.year, (q-1)*3 + 1, 1)
    q_end_month = q * 3
    last_day    = calendar.monthrange(TODAY.year, q_end_month)[1]
    q_end       = date(TODAY.year, q_end_month, last_day)
    total_days  = (q_end - q_start).days + 1
    elapsed     = (TODAY - q_start).days + 1
    pct         = min(elapsed / total_days, 1.0)
    fill_w      = int(pct * TRACK_W)
    q_week_num  = ((TODAY - q_start).days // 7) + 1
    q_total_wks = round(total_days / 7)

    color = "#1a7a4a" if pct < 0.5 else ("#b87800" if pct < 0.75 else "#c0392b")
    label = f"Uge {q_week_num} af {q_total_wks} · Q{q} {TODAY.year}"
    pct_lbl = f"{int(pct*100)}% af kvartalet gennemført"

    svg  = f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:Helvetica Neue,Arial,sans-serif;">'
    svg += f'<text x="0" y="14" fill="#999" font-size="10">{label}</text>'
    svg += f'<text x="{W}" y="14" fill="{color}" font-size="10" font-weight="bold" text-anchor="end">{pct_lbl}</text>'
    svg += f'<rect x="{TRACK_X}" y="{TRACK_Y}" width="{TRACK_W}" height="{TRACK_H}" fill="#f0f0f8" rx="4"/>'
    if fill_w > 0:
        svg += f'<rect x="{TRACK_X}" y="{TRACK_Y}" width="{fill_w}" height="{TRACK_H}" fill="{color}" rx="4" opacity="0.75"/>'
    for wk in range(1, q_total_wks + 1):
        tx = TRACK_X + int((wk / q_total_wks) * TRACK_W)
        tc = "#153EED" if wk == q_week_num else "#ddd"
        svg += f'<rect x="{tx-1}" y="{TRACK_Y-2}" width="2" height="{TRACK_H+4}" fill="{tc}"/>'
    svg += '</svg>'
    return svg


def urgency_badge(urgency: str) -> str:
    u = urgency.lower()
    if "today" in u or "i dag" in u: return '<span class="badge b-red">I dag</span>'
    if "week"  in u or "uge"  in u:  return '<span class="badge b-amber">Denne uge</span>'
    return '<span class="badge b-blue">Denne måned</span>'

def signal_dot_color(urgency: str) -> str:
    u = urgency.lower()
    if "today" in u or "i dag" in u: return "#c0392b"
    if "week"  in u or "uge"  in u:  return "#b87800"
    return "#153EED"

def status_badge(status: str) -> str:
    s = status.lower()
    if s == "active":  return '<span class="badge b-green">Aktiv</span>'
    if s == "stalled": return '<span class="badge b-red">Stalled</span>'
    if s == "ready":   return '<span class="badge b-amber">Klar</span>'
    return f'<span class="badge b-blue">{status}</span>'

def render_html(brief: dict) -> str:
    status   = brief.get("status", "Amber")
    forecast = brief.get("forecast", {})

    # ── SVGs ──────────────────────────────────────────────────────────────────
    funnel_svg   = svg_pipeline_funnel(
        brief.get("pipeline_total", "€0"),
        brief.get("pipeline_weighted", "€0"),
        brief.get("base_case_forecast", "€0"),
    )
    forecast_svg = svg_forecast_range(
        forecast.get("worst_case", "€0"),
        forecast.get("base_case", "€0"),
        forecast.get("best_case",  "€0"),
    )
    quarter_svg  = svg_quarter_progress()

    # ── Priorities ─────────────────────────────────────────────────────────────
    priorities_html = ""
    for p in brief.get("top_priorities", []):
        priorities_html += f"""
        <div class="priority-item">
          <div class="p-num">0{p.get('rank','')}</div>
          <div class="p-bar"></div>
          <div class="p-content">
            <div class="p-account">{p.get('account','')}</div>
            <div class="p-action">{p.get('action','')}</div>
            <div class="p-meta">{p.get('owner','')} &nbsp;·&nbsp; {p.get('why','')}</div>
          </div>
          <div class="p-when">{p.get('by_when','')}</div>
        </div>"""

    # ── Signals ────────────────────────────────────────────────────────────────
    signals_html = ""
    for sig in brief.get("hot_signals", []):
        urgency = sig.get('urgency', 'Denne uge')
        dot_color = signal_dot_color(urgency)
        signals_html += f"""
        <div class="signal-item">
          <div class="signal-dot" style="background:{dot_color};box-shadow:0 0 5px {dot_color}44;"></div>
          <div class="signal-content">
            <div class="sig-top">
              <span class="sig-account">{sig.get('account','')}</span>
              {urgency_badge(urgency)}
            </div>
            <div class="sig-text">{sig.get('signal','')}</div>
            <div class="sig-action">→&nbsp;{sig.get('action','')}</div>
          </div>
        </div>"""

    # ── Scorecard ──────────────────────────────────────────────────────────────
    scorecard_rows = ""
    for row in brief.get("pipeline_scorecard", []):
        pct     = row.get('win_pct', '0%')
        mini    = svg_probability_bar(pct)
        scorecard_rows += f"""
        <tr>
          <td class="sc-account">{row.get('account','')}</td>
          <td>{mini}</td>
          <td class="sc-value">{row.get('weighted','')}</td>
          <td>{status_badge(row.get('status','Active'))}</td>
          <td style="color:#666;font-size:12px;">{row.get('next_action','')}</td>
        </tr>"""

    conf = forecast.get("confidence", "Medium").lower()
    conf_badge = "b-green" if "høj" in conf or "high" in conf else ("b-red" if "lav" in conf or "low" in conf else "b-amber")

    status_dot = {"Green": "green", "Amber": "amber", "Red": "red"}.get(status, "amber")
    html = HTML_TEMPLATE

    replacements = {
        "{status_dot}":         status_dot,
        "{week_num}":           str(WEEK_NUM),
        "{date_str}":           TODAY.strftime("%d. %B %Y"),
        "{week_headline}":      brief.get("week_headline", ""),
        "{status}":             status,
        "{status_reason}":      brief.get("status_reason", ""),
        "{pipeline_total}":     brief.get("pipeline_total", "—"),
        "{pipeline_weighted}":  brief.get("pipeline_weighted", "—"),
        "{base_case_forecast}": brief.get("base_case_forecast", "—"),
        "{situation_60s}":      brief.get("situation_60s", "").replace("\n", "<br>"),
        "{svg_funnel}":         funnel_svg,
        "{svg_forecast}":       forecast_svg,
        "{svg_quarter}":        quarter_svg,
        "{priorities_html}":    priorities_html,
        "{signals_html}":       signals_html,
        "{scorecard_rows}":     scorecard_rows,
        "{biggest_risk}":       brief.get("biggest_risk", ""),
        "{biggest_opportunity}":brief.get("biggest_opportunity", ""),
        "{forecast_best}":      forecast.get("best_case", "—"),
        "{forecast_base}":      forecast.get("base_case", "—"),
        "{forecast_worst}":     forecast.get("worst_case", "—"),
        "{forecast_confidence}":forecast.get("confidence", "Medium"),
        "{confidence_badge}":   conf_badge.replace("b-",""),
        "{confidence_note}":    forecast.get("confidence_note", ""),
        "{verdict}":            brief.get("verdict", ""),
    }
    for k, v in replacements.items():
        html = html.replace(k, str(v))
    return html


# ─── 4. Send email via SendGrid ───────────────────────────────────────────────

def send_email(html: str, subject: str):
    import urllib.request, urllib.error
    api_key  = os.environ.get("SENDGRID_API_KEY", "")
    to_email = os.environ.get("TO_EMAIL", "")
    from_email = os.environ.get("FROM_EMAIL", to_email)

    if not api_key or not to_email:
        print("ERROR: SENDGRID_API_KEY and TO_EMAIL must be set", file=sys.stderr)
        sys.exit(1)

    payload = json.dumps({
        "personalizations": [{"to": [{"email": to_email}]}],
        "from":             {"email": from_email, "name": "JAKALA Commercial OS"},
        "subject":          subject,
        "content":          [{"type": "text/html", "value": html}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Email sent: {resp.status} → {to_email}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"SendGrid error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


# ─── 5. Main ──────────────────────────────────────────────────────────────────

def html_to_pdf(html: str, pdf_path: Path) -> bool:
    """Convert HTML to PDF using Chrome headless (no pip packages needed)."""
    import subprocess, tempfile

    # Write HTML to temp file
    tmp_html = Path(tempfile.mktemp(suffix=".html"))
    tmp_html.write_text(html, encoding="utf-8")

    # Find Chrome / Chromium on macOS or Linux
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "google-chrome", "chromium-browser", "chromium",
    ]
    chrome = next((c for c in candidates if Path(c).exists() or
                   subprocess.run(["which", c], capture_output=True).returncode == 0), None)

    if not chrome:
        print("[morning-brief] Chrome ikke fundet — prøver weasyprint...", file=sys.stderr)
        try:
            from weasyprint import HTML
            HTML(string=html).write_pdf(str(pdf_path))
            return True
        except ImportError:
            print("[morning-brief] Installer weasyprint: pip install weasyprint", file=sys.stderr)
            return False

    result = subprocess.run([
        chrome,
        "--headless", "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={pdf_path}",
        "--print-to-pdf-no-header",
        f"file://{tmp_html}",
    ], capture_output=True, timeout=30)

    tmp_html.unlink(missing_ok=True)
    return pdf_path.exists()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true", help="Print HTML, no send")
    parser.add_argument("--preview",  action="store_true", help="Gem HTML og åbn i browser")
    parser.add_argument("--pdf",      action="store_true", help="Generér PDF og åbn i Finder")
    args = parser.parse_args()

    print(f"[morning-brief] Indlæser data...")
    context = load_context()
    print(f"[morning-brief] {len(context):,} tegn indlæst")

    print(f"[morning-brief] Genererer briefing med Claude...")
    brief = generate_brief(context)
    print(f"[morning-brief] Status: {brief.get('status')}")

    html = render_html(brief)

    status_emoji = {"Green": "🟢", "Amber": "🟡", "Red": "🔴"}.get(brief.get("status","Amber"), "🟡")
    subject = f"{status_emoji} JAKALA Nordic — CCO Briefing · Uge {WEEK_NUM} · {TODAY.strftime('%d. %b %Y')}"

    if args.dry_run:
        print(f"\nSubject: {subject}\n{'='*60}")
        print(html[:3000] + "..." if len(html) > 3000 else html)
        return

    if args.preview:
        preview_path = Path("/tmp/brief-preview.html")
        preview_path.write_text(html)
        print(f"Preview gemt: {preview_path}")
        import subprocess
        subprocess.run(["open", str(preview_path)], check=False)
        return

    if args.pdf:
        import subprocess
        filename = f"JAKALA-CCO-Brief-{TODAY.strftime('%Y-%m-%d')}.pdf"
        pdf_path  = BASE_DIR / filename
        print(f"[morning-brief] Genererer PDF...")
        ok = html_to_pdf(html, pdf_path)
        if ok:
            print(f"\n✅  PDF klar: {pdf_path}")
            subprocess.run(["open", "--reveal", str(pdf_path)], check=False)
        else:
            print(f"❌  PDF-generering fejlede. Åbner HTML i stedet...")
            tmp = Path("/tmp/brief-preview.html")
            tmp.write_text(html)
            subprocess.run(["open", str(tmp)], check=False)
        return

    print(f"[morning-brief] Sender email: {subject}")
    send_email(html, subject)
    print(f"[morning-brief] Sendt.")


if __name__ == "__main__":
    main()
