import os
import re
import json
import datetime
import io
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, Response, stream_with_context, send_file
import anthropic
from dotenv import load_dotenv

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    PPTX_OK = True
except ImportError:
    PPTX_OK = False

load_dotenv()

app = Flask(__name__)
BASE_DIR = Path(__file__).parent.parent  # jakala-commercial-os root
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

# ── File helpers ─────────────────────────────────────────────────────────────

def read_file(rel_path):
    p = BASE_DIR / rel_path
    return p.read_text(encoding="utf-8") if p.exists() else None

def write_file(rel_path, content):
    p = BASE_DIR / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

def get_accounts():
    d = BASE_DIR / "Accounts"
    if not d.exists():
        return []
    return sorted(
        f.name for f in d.iterdir()
        if f.is_dir() and not f.name.startswith(".")
    )

def load_account_files(account_slug):
    files = ["overview.md", "strategy.md", "stakeholders.md", "next-actions.md", "meetings.md"]
    parts = []
    for f in files:
        content = read_file(f"Accounts/{account_slug}/{f}")
        if content:
            parts.append(f"--- {f} ---\n{content}")
    return "\n\n".join(parts) if parts else None

def build_system_prompt():
    today = datetime.date.today().isoformat()
    knowledge = []
    for f in [
        "knowledge/gtm-strategy.md",
        "knowledge/strategy-mapping.md",
        "knowledge/icp-scoring.md",
        "knowledge/deal-scoring.md",
        "knowledge/offerings.md",
        "knowledge/outreach-playbook.md",
        "intelligence/top-opportunities.md",
        "intelligence/pipeline-dashboard.md",
    ]:
        c = read_file(f)
        if c:
            knowledge.append(f"=== {f} ===\n{c}")

    return f"""You are the JAKALA GTM OS — a senior commercial strategy assistant for JAKALA Nordic.

TODAY: {today}
GEOGRAPHIC SCOPE: Denmark, Norway, Sweden ONLY. UK and France accounts are inactive/excluded.
ACTIVE DELIVERY: Maxbo (Norway) — Speedtrain onboarding in progress.

YOUR ROLE:
- Help JAKALA sellers structure commercial thinking, analyze accounts, and plan next actions
- Generate outreach messages (LinkedIn/email), meeting briefs, revenue simulations, pitch summaries
- Score and prioritize pipeline opportunities
- Process meeting notes and suggest file updates
- Answer questions about accounts, signals, strategies and the pipeline

KNOWLEDGE BASE:
{"=" * 60}
{chr(10).join(knowledge)}
{"=" * 60}

SKILLS YOU CAN PERFORM:
- Outreach generation (LinkedIn/email, languages: en/no/da/sv) — max 300 words, soft CTA, peer-to-peer
- Pre-meeting brief (90-second battle card)
- Revenue simulation (3-lever model: data completeness, search quality, AI model input)
- Competitor intelligence mapping
- Account setup and research
- Pipeline forecast (probability-weighted, 7-factor model)
- Signal-to-action conversion
- Morning CCO briefing
- Commercial war room (full situation assessment)
- Meeting note processing — summarize, update next-actions and meetings files

GTM STRATEGIES (always map accounts to one):
1. Data Revenue Unlock — loyalty data, retail media, first-party data monetisation
2. AI Readiness Accelerator — AI ambition outpacing data architecture
3. Commerce Optimization — live ecommerce underperforming (search, discovery, catalog)
4. Experience Transformation — multi-brand, composable architecture, DXP

TONE & OUTPUT:
- Concise, structured, senior consultant style
- Use markdown tables and headers for clarity
- For outreach: no jargon, no bullets in message body, one soft question at end
- Score conservatively — never inflate ICP or deal scores without evidence
- When account context is provided in the conversation, use it directly
- When asked about a specific account not in context, say so and ask if the user wants to load it

RULES:
- Never fabricate company data or signals — only use what is confirmed or clearly labelled as estimated
- If a deal has no named buyer, cap win probability at 25%
- Always identify the GTM strategy and entry offer when reviewing an account
- Prefer updating files over long responses when processing meeting notes"""


SYSTEM_PROMPT = build_system_prompt()


def detect_accounts_in_message(message):
    """Detect account names mentioned in a message and return their slugs."""
    accounts = get_accounts()
    found = []
    msg_lower = message.lower()
    for slug in accounts:
        display = slug.replace("-", " ")
        if display in msg_lower or slug in msg_lower:
            found.append(slug)
    return found


# ── API routes ───────────────────────────────────────────────────────────────

@app.route("/api/accounts")
def api_accounts():
    accounts = get_accounts()
    result = []
    for slug in accounts:
        overview = read_file(f"Accounts/{slug}/overview.md") or ""
        icp = "—"
        m = re.search(r"ICP Score[:\s]+(\d+)/10", overview)
        if m:
            icp = m.group(1)
        deal = "—"
        m = re.search(r"Deal Score[:\s]+(\d+)/10", overview)
        if m:
            deal = m.group(1)
        country = "—"
        for line in overview.splitlines():
            if "Norway" in line or "Norge" in line or "NO)" in line:
                country = "NO"
                break
            if "Denmark" in line or "Danmark" in line or "DK)" in line:
                country = "DK"
                break
            if "Sweden" in line or "Sverige" in line or "SE)" in line:
                country = "SE"
                break
        result.append({"slug": slug, "name": slug.replace("-", " ").title(), "icp": icp, "deal": deal, "country": country})
    return jsonify(result)


@app.route("/api/account/<slug>")
def api_account(slug):
    content = load_account_files(slug)
    if not content:
        return jsonify({"error": "Account not found"}), 404
    return jsonify({"slug": slug, "content": content})


@app.route("/api/account/<slug>/file/<filename>", methods=["GET"])
def api_get_file(slug, filename):
    allowed = ["overview.md", "strategy.md", "stakeholders.md", "next-actions.md", "meetings.md"]
    if filename not in allowed:
        return jsonify({"error": "File not allowed"}), 403
    content = read_file(f"Accounts/{slug}/{filename}")
    if content is None:
        return jsonify({"error": "File not found"}), 404
    return jsonify({"content": content})


@app.route("/api/account/<slug>/file/<filename>", methods=["POST"])
def api_save_file(slug, filename):
    allowed = ["overview.md", "strategy.md", "stakeholders.md", "next-actions.md", "meetings.md"]
    if filename not in allowed:
        return jsonify({"error": "File not allowed"}), 403
    data = request.get_json()
    content = data.get("content", "")
    write_file(f"Accounts/{slug}/{filename}", content)
    return jsonify({"ok": True})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    messages = data.get("messages", [])
    account_slug = data.get("account")

    injected_context = ""

    if account_slug:
        account_content = load_account_files(account_slug)
        if account_content:
            injected_context += f"\n\nACCOUNT CONTEXT LOADED — {account_slug.replace('-', ' ').title()}:\n{account_content}"

    if messages:
        last_msg = messages[-1].get("content", "")
        detected = detect_accounts_in_message(last_msg)
        for slug in detected:
            if slug != account_slug:
                content = load_account_files(slug)
                if content:
                    injected_context += f"\n\nACCOUNT CONTEXT — {slug.replace('-', ' ').title()}:\n{content}"

    api_messages = []
    for i, msg in enumerate(messages):
        role = msg.get("role")
        content = msg.get("content", "")
        if i == len(messages) - 1 and role == "user" and injected_context:
            content = f"{injected_context}\n\n---\n\nUser question: {content}"
        api_messages.append({"role": role, "content": content})

    def generate():
        with client.messages.stream(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=api_messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/process-notes", methods=["POST"])
def api_process_notes():
    data = request.get_json()
    account_slug = data.get("account")
    notes = data.get("notes", "")

    if not account_slug or not notes:
        return jsonify({"error": "account and notes required"}), 400

    account_content = load_account_files(account_slug)
    today = datetime.date.today().isoformat()

    prompt = f"""You are processing meeting notes for JAKALA account: {account_slug.replace('-', ' ').title()}

EXISTING ACCOUNT FILES:
{account_content or '(no existing files)'}

MEETING NOTES TO PROCESS:
{notes}

TODAY: {today}

Your task — return a JSON object with EXACTLY these keys:
{{
  "summary": "2-3 sentence summary of the meeting",
  "meeting_entry": "Full markdown entry to append to meetings.md (include date, attendees if mentioned, key points, agreed actions)",
  "next_actions_updated": "Complete updated content for next-actions.md — incorporate new actions from this meeting, mark completed items if applicable",
  "key_insight": "One sentence: the most important commercial insight from this meeting"
}}

Rules:
- next_actions_updated should be the FULL new content of the file (not just the additions)
- Include today's date ({today}) in the meeting entry header
- Keep the same markdown format as existing files
- Prioritise actions by commercial impact
- Return ONLY valid JSON — no markdown fences, no explanation"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse AI response", "raw": raw}), 500

    return jsonify(result)


@app.route("/api/save-notes", methods=["POST"])
def api_save_notes():
    data = request.get_json()
    slug = data.get("account")
    meeting_entry = data.get("meeting_entry", "")
    next_actions = data.get("next_actions_updated", "")

    if not slug:
        return jsonify({"error": "account required"}), 400

    today = datetime.date.today().isoformat()

    existing_meetings = read_file(f"Accounts/{slug}/meetings.md") or f"# {slug.replace('-', ' ').title()} — Meetings\n\nLast updated: {today}\n\n---\n"
    existing_meetings = re.sub(r"Last updated: \d{4}-\d{2}-\d{2}", f"Last updated: {today}", existing_meetings)
    existing_meetings = existing_meetings + f"\n\n---\n\n{meeting_entry}"
    write_file(f"Accounts/{slug}/meetings.md", existing_meetings)

    if next_actions:
        next_actions = re.sub(r"Last updated: \d{4}-\d{2}-\d{2}", f"Last updated: {today}", next_actions)
        write_file(f"Accounts/{slug}/next-actions.md", next_actions)

    return jsonify({"ok": True})


# ── PPTX generation ──────────────────────────────────────────────────────────

BLUE  = RGBColor(0x15,0x3E,0xED) if PPTX_OK else None
NAVY  = RGBColor(0x02,0x02,0x66) if PPTX_OK else None
RED   = RGBColor(0xF6,0x57,0x4A) if PPTX_OK else None
GREEN = RGBColor(0x00,0xD4,0xA0) if PPTX_OK else None
WHITE = RGBColor(0xFF,0xFF,0xFF) if PPTX_OK else None
GREY  = RGBColor(0xBB,0xBB,0xDD) if PPTX_OK else None
MUTED = RGBColor(0x88,0x88,0xAA) if PPTX_OK else None
BG    = RGBColor(0x04,0x04,0x0F) if PPTX_OK else None
CARD  = RGBColor(0x0A,0x0A,0x22) if PPTX_OK else None
W = Inches(9.84) if PPTX_OK else None
H = Inches(7.48) if PPTX_OK else None
FONT  = "Calibri"


def _prs():
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H
    return prs

def _slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

def _bg(slide):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = BG

def _rect(slide, x, y, w, h, color):
    s = slide.shapes.add_shape(1, x, y, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = color
    s.line.fill.background()
    return s

def _txt(slide, text, x, y, w, h, size=14, bold=False, color=None, align=None):
    if color is None: color = WHITE
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    if align: p.alignment = align
    r = p.add_run(); r.text = str(text)
    r.font.name = FONT; r.font.size = Pt(size)
    r.font.bold = bold; r.font.color.rgb = color
    return tb

def _add_para(tf, text, size=13, bold=False, color=None, space=6):
    if color is None: color = WHITE
    p = tf.add_paragraph(); p.space_before = Pt(space)
    r = p.add_run(); r.text = str(text)
    r.font.name = FONT; r.font.size = Pt(size)
    r.font.bold = bold; r.font.color.rgb = color

def _header(slide, tag, title):
    _rect(slide, Inches(0), Inches(0), W, Inches(0.08), BLUE)
    _txt(slide, tag,   Inches(0.5), Inches(0.14), Inches(8), Inches(0.35),
         size=9, bold=True, color=BLUE)
    _txt(slide, title, Inches(0.5), Inches(0.54), Inches(8.5), Inches(0.75),
         size=24, bold=True)

def _footer(slide, text):
    _rect(slide, Inches(0), H - Inches(0.32), W, Inches(0.32), BLUE)
    _txt(slide, text, Inches(0.3), H - Inches(0.30), Inches(9), Inches(0.28),
         size=9, color=WHITE)

def _bullet_col(slide, x, y, w, h, sections):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    first = True
    for header, bullets in sections:
        _add_para(tf, header, 12, True, BLUE, 0 if first else 10)
        first = False
        for b in bullets:
            _add_para(tf, f"• {b}", 11, False, WHITE, 3)

def build_account_deck(account_name, data):
    """Build a 5-slide discovery deck from Claude-generated JSON data."""
    prs = _prs()

    # Slide 1 — Cover
    s = _slide(prs); _bg(s)
    _rect(s, Inches(0), H - Inches(0.5), W, Inches(0.5), BLUE)
    _rect(s, Inches(0), Inches(0), Inches(0.08), H, BLUE)
    _txt(s, "JAKALA COMMERCIAL", Inches(0.3), Inches(1.2), Inches(8), Inches(0.4),
         size=10, bold=True, color=MUTED)
    _txt(s, account_name, Inches(0.3), Inches(1.75), Inches(8.5), Inches(2.2),
         size=48, bold=True)
    _txt(s, data.get("subtitle","Commercial Discovery"), Inches(0.3), Inches(3.9),
         Inches(7), Inches(0.65), size=22, bold=True, color=BLUE)
    _txt(s, data.get("date", datetime.date.today().isoformat()),
         Inches(0.3), Inches(5.6), Inches(4), Inches(0.35), size=11, color=MUTED)

    # Slide 2 — Why now
    s = _slide(prs); _bg(s)
    _header(s, "COMMERCIAL CONTEXT", data.get("context_title","Why Now"))
    _bullet_col(s, Inches(0.5), Inches(1.5), Inches(4.0), Inches(5.2),
                [("Signals & Timing", data.get("context_points",[]))])
    _bullet_col(s, Inches(5.0), Inches(1.5), Inches(4.34), Inches(5.2),
                [("Business Pressure", data.get("pressure_points",[]))])
    _footer(s, f"JAKALA — {account_name} — Confidential")

    # Slide 3 — GTM Strategy
    s = _slide(prs); _bg(s)
    _header(s, "GTM STRATEGY", data.get("gtm_title","Our Entry Approach"))
    _rect(s, Inches(0.5), Inches(1.5), Inches(3.8), Inches(0.55), NAVY)
    _txt(s, data.get("gtm_strategy","—"), Inches(0.6), Inches(1.52), Inches(3.6),
         Inches(0.5), size=14, bold=True, color=BLUE)
    _bullet_col(s, Inches(0.5), Inches(2.2), Inches(4.0), Inches(4.5),
                [("Entry Offer", data.get("entry_points",[])),
                 ("Expansion Path", data.get("expansion_points",[]))])
    _bullet_col(s, Inches(5.0), Inches(1.5), Inches(4.34), Inches(5.2),
                [("Likely Buyer", data.get("buyer_points",[])),
                 ("Why JAKALA Wins", data.get("why_jakala",[]))])
    _footer(s, f"JAKALA — {account_name} — Confidential")

    # Slide 4 — Business case
    s = _slide(prs); _bg(s)
    _header(s, "THE BUSINESS CASE", data.get("value_title","Value & Impact"))
    # Stat cards
    stats = data.get("stats", [])
    for i, st in enumerate(stats[:3]):
        x = Inches(0.5) + i * Inches(3.1)
        _rect(s, x, Inches(1.5), Inches(2.8), Inches(1.2), NAVY)
        _txt(s, st.get("value","—"), x + Inches(0.15), Inches(1.55),
             Inches(2.5), Inches(0.65), size=30, bold=True, color=BLUE)
        _txt(s, st.get("label",""), x + Inches(0.15), Inches(2.1),
             Inches(2.5), Inches(0.45), size=11, color=WHITE)
    _bullet_col(s, Inches(0.5), Inches(2.85), Inches(4.0), Inches(4.0),
                [("Impact Framing", data.get("value_points",[]))])
    _bullet_col(s, Inches(5.0), Inches(2.85), Inches(4.34), Inches(4.0),
                [("Risk of Inaction", data.get("risk_points",[]))])
    _footer(s, f"JAKALA — {account_name} — Confidential")

    # Slide 5 — Next steps
    s = _slide(prs); _bg(s)
    _header(s, "NEXT STEPS", data.get("next_title","Proposed Actions"))
    next_steps = data.get("next_steps",[])
    colors = [BLUE, GREEN, RED]
    for i, step in enumerate(next_steps[:4]):
        y = Inches(1.55) + i * Inches(1.2)
        col = colors[i % len(colors)]
        _rect(s, Inches(0.5), y, Inches(0.52), Inches(0.52), col)
        _txt(s, str(i+1), Inches(0.5), y, Inches(0.52), Inches(0.52),
             size=20, bold=True, align=PP_ALIGN.CENTER)
        _txt(s, step.get("title",""), Inches(1.15), y, Inches(8.1), Inches(0.42),
             size=14, bold=True)
        _txt(s, step.get("desc",""), Inches(1.15), y + Inches(0.4), Inches(8.1),
             Inches(0.55), size=11, color=GREY)
    _footer(s, f"JAKALA — {account_name} — Confidential")

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


@app.route("/api/generate-deck/<slug>", methods=["POST"])
def api_generate_deck(slug):
    import traceback
    if not PPTX_OK:
        return jsonify({"error": "python-pptx not installed"}), 500
    try:
        return _do_generate_deck(slug)
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

def _do_generate_deck(slug):
    account_content = load_account_files(slug)
    account_name = slug.replace("-", " ").title()
    today = datetime.date.today().isoformat()

    prompt = f"""You are building a 5-slide commercial discovery deck for JAKALA about: {account_name}

ACCOUNT DATA:
{account_content or '(no files)'}

TODAY: {today}

Return ONLY valid JSON (no markdown fences) with this exact structure:
{{
  "subtitle": "Commercial Discovery — [GTM Strategy Name]",
  "date": "{today}",
  "context_title": "Why {account_name}, Why Now",
  "context_points": ["signal 1", "signal 2", "signal 3"],
  "pressure_points": ["business pressure 1", "pressure 2", "pressure 3"],
  "gtm_title": "Our Entry Approach",
  "gtm_strategy": "[one of: Data Revenue Unlock / AI Readiness Accelerator / Commerce Optimization / Experience Transformation]",
  "entry_points": ["entry offer detail 1", "detail 2"],
  "expansion_points": ["expansion 1", "expansion 2"],
  "buyer_points": ["Name — Title", "why they care"],
  "why_jakala": ["differentiator 1", "differentiator 2"],
  "value_title": "The Business Case",
  "stats": [
    {{"value": "€Xm", "label": "Estimated revenue impact"}},
    {{"value": "X/10", "label": "Deal score"}},
    {{"value": "Xwks", "label": "Time to first value"}}
  ],
  "value_points": ["value framing 1", "value 2", "value 3"],
  "risk_points": ["risk of inaction 1", "risk 2"],
  "next_title": "Proposed Next Steps",
  "next_steps": [
    {{"title": "action 1", "desc": "description"}},
    {{"title": "action 2", "desc": "description"}},
    {{"title": "action 3", "desc": "description"}}
  ]
}}

Rules:
- Be specific — use real names, real signals from account data
- Keep each bullet under 10 words
- GTM strategy must match the account's best fit
- Return ONLY the JSON object"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse AI response", "raw": raw}), 500

    buf = build_account_deck(account_name, data)
    filename = f"JAKALA-{slug}-discovery-{today}.pptx"
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name=filename
    )


# ── Partnership API ──────────────────────────────────────────────────────────

@app.route("/api/validate-partner", methods=["POST"])
def api_validate_partner():
    data      = request.get_json()
    partner   = data.get("partner", "").strip()
    market    = data.get("market", "Nordic")
    context   = data.get("context", "")
    if not partner:
        return jsonify({"error": "Partner name required"}), 400

    gtm      = read_file("knowledge/gtm-strategy.md") or ""
    services = read_file("knowledge/jakala-services.md") or ""
    offerings= read_file("knowledge/offerings.md") or ""
    today    = datetime.date.today().isoformat()

    prompt = f"""You are a senior JAKALA partnership strategist evaluating a potential partner.

TODAY: {today}
JAKALA CONTEXT:
- Nordic GTM focus: Denmark, Norway, Sweden
- Core services: Commerce Experience, Product Experience / Speedtrain PIM, DXP, Generative AI, CDP/CRM, BI, Data Architecture, Pricing, Hello Growth (SaaS)
- GTM strategies: Data Revenue Unlock · AI Readiness Accelerator · Commerce Optimization · Experience Transformation
- Buyer personas: CTO, CDO, CMO, Head of Ecommerce, Head of Data
- Active delivery: Maxbo (Norway) — Speedtrain onboarding

GTM STRATEGY SUMMARY:
{gtm[:1000]}

SERVICES:
{services[:1200]}

PARTNER TO EVALUATE: {partner}
MARKET FOCUS: {market}
ADDITIONAL CONTEXT: {context or "None provided"}

Evaluate this partnership across 5 dimensions and return a structured assessment.

Return ONLY valid JSON (no markdown fences):
{{
  "partner": "{partner}",
  "market": "{market}",
  "verdict": "STRONG FIT" | "POTENTIAL FIT" | "WEAK FIT" | "NOT RECOMMENDED",
  "verdict_reason": "One sentence summary of the verdict",
  "overall_score": 7,
  "dimensions": [
    {{
      "name": "GTM Fit",
      "score": 8,
      "max": 10,
      "rationale": "Does this partner serve the same buyer personas and complement JAKALA's GTM strategies?",
      "finding": "2-3 sentence specific assessment"
    }},
    {{
      "name": "Revenue Potential",
      "score": 7,
      "max": 10,
      "rationale": "Joint pipeline, referrals, co-delivery, or new market access potential",
      "finding": "2-3 sentence specific assessment"
    }},
    {{
      "name": "Market Positioning",
      "score": 8,
      "max": 10,
      "rationale": "Does the partnership enhance JAKALA credibility and reach in {market}?",
      "finding": "2-3 sentence specific assessment"
    }},
    {{
      "name": "Channel Conflict Risk",
      "score": 6,
      "max": 10,
      "rationale": "Risk of competing with JAKALA for the same deals or services (higher score = lower risk)",
      "finding": "2-3 sentence specific assessment"
    }},
    {{
      "name": "Activation Speed",
      "score": 7,
      "max": 10,
      "rationale": "How quickly can this partnership generate tangible pipeline or revenue?",
      "finding": "2-3 sentence specific assessment"
    }}
  ],
  "gtm_match": ["Data Revenue Unlock", "Commerce Optimization"],
  "buyer_overlap": ["CTO", "Head of Ecommerce"],
  "joint_offer": "One specific joint offer or entry point that combines both companies",
  "target_accounts": ["Account 1", "Account 2", "Account 3"],
  "risks": ["Risk 1", "Risk 2"],
  "first_step": "Concrete first action to activate this partnership",
  "partner_type": "Technology Vendor" | "System Integrator" | "Consulting Firm" | "Platform Vendor" | "Agency" | "Data Provider" | "Other"
}}

Rules:
- Be specific — if you know what this company does, use that knowledge
- Score honestly — a weak fit should score 3-4, not 6-7
- Target accounts should be from the Nordic pipeline (NO/SE/DK) if possible
- Return ONLY the JSON"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = re.sub(r"^```json\s*", "", response.content[0].text.strip())
    raw = re.sub(r"\s*```$", "", raw)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return jsonify({"error": "AI parse failed", "raw": raw}), 500

    # Save to intelligence/partnerships/
    save_partner_result(partner, market, result, today)
    return jsonify(result)


def save_partner_result(partner, market, data, today):
    p = BASE_DIR / "intelligence" / "partnerships"
    p.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", partner.lower()).strip("-")
    fname = p / f"{slug}-{today}.md"
    lines = [
        f"# Partnership Assessment — {partner}",
        f"Date: {today} | Market: {market} | Verdict: {data.get('verdict','—')}",
        "",
        f"**Overall Score:** {data.get('overall_score','—')}/10",
        f"**Type:** {data.get('partner_type','—')}",
        f"**Verdict:** {data.get('verdict_reason','—')}",
        "",
        "## Dimension Scores",
    ]
    for d in data.get("dimensions", []):
        lines.append(f"- **{d['name']}:** {d['score']}/{d['max']} — {d['finding']}")
    lines += [
        "",
        f"## Joint Offer\n{data.get('joint_offer','—')}",
        "",
        f"## GTM Match\n{', '.join(data.get('gtm_match',[]))}",
        "",
        f"## Target Accounts\n{', '.join(data.get('target_accounts',[]))}",
        "",
        f"## First Step\n{data.get('first_step','—')}",
        "",
        f"## Risks\n" + "\n".join(f"- {r}" for r in data.get("risks", [])),
    ]
    fname.write_text("\n".join(lines), encoding="utf-8")


@app.route("/api/partner-history")
def api_partner_history():
    p = BASE_DIR / "intelligence" / "partnerships"
    if not p.exists():
        return jsonify([])
    results = []
    for f in sorted(p.glob("*.md"), reverse=True)[:20]:
        content = f.read_text(encoding="utf-8")
        verdict_m = re.search(r"Verdict: (.+)", content)
        score_m   = re.search(r"Overall Score:\*\* (\d+)/10", content)
        market_m  = re.search(r"Market: (\w+)", content)
        name_m    = re.search(r"# Partnership Assessment — (.+)", content)
        results.append({
            "file":    f.stem,
            "name":    name_m.group(1).strip()  if name_m    else f.stem,
            "verdict": verdict_m.group(1).strip() if verdict_m else "—",
            "score":   score_m.group(1)          if score_m   else "—",
            "market":  market_m.group(1)         if market_m  else "—",
        })
    return jsonify(results)


@app.route("/api/monthly-partnerships")
def api_monthly_partnerships():
    p = BASE_DIR / "intelligence" / "partnerships"
    if not p.exists():
        return jsonify({"content": None})
    files = sorted(p.glob("monthly-*.md"), reverse=True)
    if not files:
        return jsonify({"content": None})
    return jsonify({"content": files[0].read_text(encoding="utf-8")})


# ── Signals API ──────────────────────────────────────────────────────────────

@app.route("/api/signals")
def api_signals():
    hot = [
        {"company":"Sport Outlet","text":"CTO + CDO both vacant March 2026. Entry via CEO Tor-André Skeie. Vacancy = budget already approved.","tag":"URGENT","tagColor":"red","icon":"🔴","slug":"sport-outlet"},
        {"company":"Trumf (NorgesGruppen)","text":"Rikke Etholm-Idsøe — new Commercial Director in newly created role. 90-day honeymoon window open now.","tag":"90-DAY WINDOW","tagColor":"red","icon":"⚡","slug":"trumf"},
        {"company":"Vinmonopolet","text":"Espen Terland new CDO (ex-XXL 15 years). Agenda not set — honeymoon phase. Ideal discovery entry.","tag":"NEW EXEC","tagColor":"amber","icon":"🆕","slug":"vinmonopolet"},
        {"company":"Skeidar","text":"\"Best furniture portal in the Nordics\" declared publicly by CEO. CIO Sujit Nath confirmed buyer.","tag":"NAMED BUYER","tagColor":"amber","icon":"🏗️","slug":"skeidar"},
        {"company":"BI Handelshøyskolen","text":"Rector Karen Spens leaving August 2026. Institution in transition — new leadership will reset priorities.","tag":"TRANSITION","tagColor":"amber","icon":"🎓","slug":"bi-handelshoyskolen"},
        {"company":"GANT Norway","text":"New CEO Fredrik Malm + IMPACT Commerce new ecom partner (Feb 2026). Integration phase = JAKALA entry.","tag":"NEW CEO","tagColor":"amber","icon":"👔","slug":"gant-norway"},
        {"company":"H&M Sweden","text":"ICP 9/10 · Deal 9/10 · €900K unweighted. No named buyer confirmed yet. Largest untouched opportunity.","tag":"TOP PRIORITY","tagColor":"blue","icon":"💎","slug":"hm"},
        {"company":"Matas","text":"ICP 9/10 · Deal 9/10 · €700K. AI Readiness entry. Loyalty data + personalisation play — Matas More programme.","tag":"HIGH VALUE","tagColor":"blue","icon":"💡","slug":"matas"},
    ]
    # Append signals from intelligence folder
    extra = []
    intel = BASE_DIR / "intelligence" / "daily-leads"
    if intel.exists():
        for f in sorted(intel.iterdir(), reverse=True)[:1]:
            if f.suffix == ".md":
                for line in f.read_text(encoding="utf-8").splitlines():
                    if line.startswith("## ") and len(line) > 4:
                        extra.append({"company": line[3:].strip(), "text": f"From daily radar {f.stem}", "tag":"RADAR","tagColor":"blue","icon":"📡","slug":""})
    return jsonify({"signals": hot + extra[:4]})


# ── Pitch Simulator API ───────────────────────────────────────────────────────

@app.route("/api/pitch", methods=["POST"])
def api_pitch():
    data = request.get_json()
    messages = data.get("messages", [])
    account_slug = data.get("account", "")
    scoring = data.get("scoring", False)

    account_content = load_account_files(account_slug) or ""
    account_name = account_slug.replace("-", " ").title()

    # Extract buyer from stakeholders
    stakeholders = read_file(f"Accounts/{account_slug}/stakeholders.md") or ""
    buyer_match = re.search(r"###\s+(.+)", stakeholders)
    title_match = re.search(r"\*\*Title:\*\*\s*(.+)", stakeholders)
    buyer_name  = buyer_match.group(1).strip() if buyer_match else "The Decision Maker"
    buyer_title = title_match.group(1).strip() if title_match else "CDO / CMO"

    if scoring:
        system = f"""You are a senior sales coach. The user just completed a pitch practice session trying to sell JAKALA's services to {account_name}.

Review the conversation and provide a concise scorecard:

**Pitch Scorecard — {account_name}**
Score each dimension 1–10:
- Opening hook: X/10
- Value proposition clarity: X/10
- Objection handling: X/10
- Buyer fit: X/10
- Call to action: X/10
- **Overall: X/10**

Then give 1 key strength and 1 specific improvement to make the pitch 20% more effective."""
    else:
        system = f"""You are {buyer_name}, {buyer_title} at {account_name}.

ACCOUNT CONTEXT:
{account_content[:2000]}

YOUR PERSONA:
- You are a senior executive who is busy, slightly sceptical, and protective of budget
- You care deeply about business outcomes, not technology for its own sake
- You ask tough but fair questions
- You are open to the right partner if they demonstrate clear ROI and understand your specific challenges
- You do NOT know about JAKALA or their services — treat them as a cold approach
- Stay in character throughout. Respond as this buyer would in a real meeting.
- Keep responses concise (2-5 sentences) — you're in a meeting, not writing an essay
- Push back if the pitch is vague or generic
- If the pitch is compelling, show genuine interest

Start the conversation by briefly introducing yourself and asking what brings the salesperson to this meeting."""

    def generate():
        with client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# ── Board Report API ──────────────────────────────────────────────────────────

@app.route("/api/board-report", methods=["POST"])
def api_board_report():
    import traceback
    if not PPTX_OK:
        return jsonify({"error": "python-pptx not installed"}), 500
    try:
        return _do_board_report()
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


def _do_board_report():
    today = datetime.date.today().isoformat()
    accounts = get_accounts()
    pipeline_lines = []
    for slug in accounts[:60]:
        ov = read_file(f"Accounts/{slug}/overview.md") or ""
        st = read_file(f"Accounts/{slug}/strategy.md") or ""
        icp_m  = re.search(r"ICP Score[:\s]+(\d+)/10", ov)
        deal_m = re.search(r"Deal Score[:\s]+(\d+)/10", ov)
        icp  = int(icp_m.group(1))  if icp_m  else 0
        deal = int(deal_m.group(1)) if deal_m else 0
        if icp >= 7 or deal >= 7:
            pipeline_lines.append(f"- {slug.replace('-',' ').title()}: ICP {icp}, Deal {deal}")

    top_ctx = read_file("intelligence/top-opportunities.md") or ""

    prompt = f"""You are building a board-level commercial review for JAKALA Nordic.

TODAY: {today}
PIPELINE (top accounts):
{chr(10).join(pipeline_lines[:20])}

TOP OPPORTUNITIES:
{top_ctx[:1500]}

Return ONLY valid JSON (no markdown fences):
{{
  "exec_summary": "2-sentence pipeline status for the board",
  "pipeline_value": "€6.8M",
  "pipeline_status": "AMBER",
  "top_deals": [
    {{"name":"H&M","value":"€900K","stage":"Prospecting","gtm":"Data Revenue Unlock","next":"Identify buyer — no named contact yet"}},
    {{"name":"Matas","value":"€700K","stage":"Prospecting","gtm":"AI Readiness","next":"Outreach to loyalty/data team"}},
    {{"name":"Elkjøp","value":"€700K","stage":"Prospecting","gtm":"Commerce Optimization","next":"Contact Morten Syversen"}},
    {{"name":"Varner Group","value":"€450K","stage":"Prospecting","gtm":"Data Revenue Unlock","next":"Confirm buyer — Elise Laupstad"}},
    {{"name":"Trumf","value":"€450K","stage":"Prospecting","gtm":"Data Revenue Unlock","next":"Reach Rikke Etholm-Idsøe (new role)"}}
  ],
  "q2_forecast": "€420K",
  "q2_confidence": "Base case",
  "q3_forecast": "€850K",
  "q3_confidence": "Upside",
  "risks": ["Zero first meetings booked","No named buyer on top 3 accounts","Pipeline age increasing"],
  "opportunities": ["5 hot timing signals active this week","45 ICP-scored accounts ready to contact","Trumf + Vinmonopolet honeymoon windows open"],
  "this_week": [
    {{"action":"Contact Sport Outlet CEO Tor-André Skeie","why":"CTO + CDO both vacant — entry window closing fast"}},
    {{"action":"Reach Trumf Commercial Director Rikke Etholm-Idsøe","why":"New role, 90-day honeymoon window"}},
    {{"action":"Vinmonopolet CDO Espen Terland outreach","why":"New CDO, agenda not set — perfect timing"}},
    {{"action":"H&M buyer identification","why":"€900K — largest opportunity, buyer TBD"}},
    {{"action":"Matas loyalty team outreach","why":"€700K, AI Readiness — data infrastructure opportunity"}}
  ],
  "gtm_split": {{"dru":12,"ai":11,"co":13,"xt":9}}
}}

Return ONLY the JSON — no explanation."""

    response = client.messages.create(
        model=MODEL, max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = re.sub(r"^```json\s*", "", response.content[0].text.strip())
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return jsonify({"error": "AI parse failed", "raw": raw}), 500

    buf = _build_board_report(data, today)
    return send_file(buf,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name=f"JAKALA-Board-Report-{today}.pptx")


def _build_board_report(data, today):
    prs = _prs()

    # Slide 1 — Cover
    s = _slide(prs); _bg(s)
    _rect(s, Inches(0), Inches(0), Inches(0.08), H, BLUE)
    _rect(s, Inches(0), H - Inches(0.5), W, Inches(0.5), BLUE)
    _txt(s, "JAKALA NORDIC", Inches(0.3), Inches(1.2), Inches(8), Inches(0.4), size=10, bold=True, color=MUTED)
    _txt(s, "Commercial\nBoard Review", Inches(0.3), Inches(1.75), Inches(8.5), Inches(2.5), size=44, bold=True)
    _txt(s, today, Inches(0.3), Inches(4.2), Inches(4), Inches(0.35), size=12, color=MUTED)
    status = data.get("pipeline_status", "AMBER")
    scol = GREEN if status == "GREEN" else (RED if status == "RED" else RGBColor(0xF5,0xA6,0x23))
    _rect(s, Inches(0.3), Inches(4.75), Inches(2.2), Inches(0.45), scol)
    _txt(s, f"STATUS: {status}", Inches(0.35), Inches(4.77), Inches(2.1), Inches(0.4), size=11, bold=True, color=WHITE)

    # Slide 2 — KPIs + Exec Summary
    s = _slide(prs); _bg(s)
    _header(s, "PIPELINE OVERVIEW", "Nordic Commercial Pipeline — Q1–Q2 2026")
    kpis = [
        (data.get("pipeline_value","€6.8M"), "Total Pipeline", BLUE),
        ("45", "Active Accounts", NAVY),
        (data.get("q2_forecast","€420K"), "Q2 Base Case", GREEN),
        ("18", "Named Buyers", RGBColor(0xF5,0xA6,0x23)),
    ]
    for i, (val, lbl, col) in enumerate(kpis):
        x = Inches(0.4) + i * Inches(2.35)
        _rect(s, x, Inches(1.5), Inches(2.1), Inches(1.3), col)
        _txt(s, val, x+Inches(0.12), Inches(1.56), Inches(1.86), Inches(0.72), size=26, bold=True)
        _txt(s, lbl, x+Inches(0.12), Inches(2.24), Inches(1.86), Inches(0.45), size=10, color=WHITE)
    _txt(s, data.get("exec_summary",""), Inches(0.5), Inches(3.1), Inches(9.0), Inches(1.0), size=13, color=GREY)
    _bullet_col(s, Inches(0.5), Inches(4.3), Inches(4.3), Inches(2.8), [("Key Risks", data.get("risks",[]))])
    _bullet_col(s, Inches(5.0), Inches(4.3), Inches(4.3), Inches(2.8), [("Key Opportunities", data.get("opportunities",[]))])
    _footer(s, f"JAKALA Nordic Board Review — {today} — Confidential")

    # Slide 3 — Top 5 Deals
    s = _slide(prs); _bg(s)
    _header(s, "TOP OPPORTUNITIES", "Highest-Value Active Deals")
    cols_cycle = [GREEN, BLUE, BLUE, NAVY, NAVY]
    for i, deal in enumerate(data.get("top_deals",[])[:5]):
        y = Inches(1.55) + i * Inches(1.04)
        col = cols_cycle[i]
        _rect(s, Inches(0.4), y, Inches(0.08), Inches(0.84), col)
        _txt(s, deal.get("name",""), Inches(0.6), y+Inches(0.02), Inches(3.0), Inches(0.44), size=14, bold=True)
        _txt(s, deal.get("gtm",""), Inches(0.6), y+Inches(0.44), Inches(3.0), Inches(0.35), size=10, color=MUTED)
        _txt(s, deal.get("value",""), Inches(3.8), y+Inches(0.02), Inches(1.5), Inches(0.44), size=18, bold=True, color=col)
        _txt(s, deal.get("stage",""), Inches(3.8), y+Inches(0.44), Inches(1.5), Inches(0.35), size=10, color=MUTED)
        _txt(s, f"\u2192 {deal.get('next','')}", Inches(5.5), y+Inches(0.2), Inches(3.8), Inches(0.45), size=11, color=GREY)
    _footer(s, f"JAKALA Nordic Board Review — {today} — Confidential")

    # Slide 4 — Forecast
    s = _slide(prs); _bg(s)
    _header(s, "REVENUE FORECAST", "Q2–Q3 2026 Probability-Weighted")
    for i, (period, val, conf) in enumerate([
        ("Q2 2026 Base", data.get("q2_forecast","€420K"), data.get("q2_confidence","Base case")),
        ("Q3 2026 Upside", data.get("q3_forecast","€850K"), data.get("q3_confidence","Upside")),
        ("FY 2026 Target", "€1.8M", "Stretch"),
    ]):
        x = Inches(0.5) + i * Inches(3.1)
        _rect(s, x, Inches(1.55), Inches(2.8), Inches(1.8), NAVY)
        _txt(s, period, x+Inches(0.15), Inches(1.62), Inches(2.5), Inches(0.44), size=11, bold=True, color=MUTED)
        _txt(s, val, x+Inches(0.15), Inches(2.1), Inches(2.5), Inches(0.72), size=32, bold=True, color=BLUE)
        _txt(s, conf, x+Inches(0.15), Inches(2.8), Inches(2.5), Inches(0.4), size=11, color=GREY)
    sp = data.get("gtm_split", {"dru":12,"ai":11,"co":13,"xt":9})
    _bullet_col(s, Inches(0.5), Inches(3.8), Inches(4.0), Inches(3.3), [("GTM Strategy Mix", [
        f"Commerce Optimization: {sp.get('co',0)} accounts",
        f"Data Revenue Unlock: {sp.get('dru',0)} accounts",
        f"AI Readiness: {sp.get('ai',0)} accounts",
        f"Experience Transformation: {sp.get('xt',0)} accounts",
    ])])
    _footer(s, f"JAKALA Nordic Board Review — {today} — Confidential")

    # Slide 5 — Priority Actions
    s = _slide(prs); _bg(s)
    _header(s, "PRIORITY ACTIONS", "This Week's Commercial Focus")
    colors_c = [BLUE, GREEN, RED, RGBColor(0xF5,0xA6,0x23), BLUE]
    for i, item in enumerate(data.get("this_week",[])[:5]):
        y = Inches(1.6) + i * Inches(1.1)
        col = colors_c[i % len(colors_c)]
        _rect(s, Inches(0.5), y, Inches(0.52), Inches(0.52), col)
        _txt(s, str(i+1), Inches(0.5), y, Inches(0.52), Inches(0.52), size=20, bold=True, align=PP_ALIGN.CENTER)
        _txt(s, item.get("action",""), Inches(1.15), y, Inches(8.1), Inches(0.42), size=14, bold=True)
        _txt(s, item.get("why",""), Inches(1.15), y+Inches(0.42), Inches(8.1), Inches(0.5), size=11, color=GREY)
    _footer(s, f"JAKALA Nordic Board Review — {today} — Confidential")

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


# ── Frontend ─────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JAKALA GTM OS</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --blue:       #153EED;
  --blue-mid:   #3558F0;
  --blue-light: #4B6EF7;
  --blue-glow:  rgba(21,62,237,0.35);
  --blue-dim:   rgba(21,62,237,0.10);
  --blue-dim2:  rgba(21,62,237,0.18);
  --red:        #F6574A;
  --red-dim:    rgba(246,87,74,0.12);
  --green:      #00D4A0;
  --green-dim:  rgba(0,212,160,0.12);
  --amber:      #F5A623;
  --amber-dim:  rgba(245,166,35,0.12);
  --purple:     #7B5CF5;
  --bg:         #03030E;
  --bg2:        #06061A;
  --bg3:        #0A0A22;
  --bg4:        #0F0F2E;
  --border:     rgba(255,255,255,0.055);
  --border-hi:  rgba(255,255,255,0.11);
  --text:       #E0E0F0;
  --muted:      #5A5A8A;
  --muted2:     #8080B0;
  --white:      #FFFFFF;
  --sidebar:    272px;
  --font:       'Inter', -apple-system, system-ui, sans-serif;
}

body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  display: flex;
  overflow: hidden;
  font-size: 13px;
  -webkit-font-smoothing: antialiased;
}

/* ── Ambient background ── */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 60% at 15% 10%, rgba(21,62,237,0.07) 0%, transparent 60%),
    radial-gradient(ellipse 60% 50% at 85% 90%, rgba(123,92,245,0.05) 0%, transparent 60%),
    radial-gradient(ellipse 50% 40% at 50% 50%, rgba(246,87,74,0.03) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
  animation: ambientShift 12s ease-in-out infinite alternate;
}
@keyframes ambientShift {
  0%   { opacity: 0.6; transform: scale(1); }
  100% { opacity: 1;   transform: scale(1.04); }
}

/* ── Grid overlay ── */
body::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.012) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.012) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
  z-index: 0;
}

/* ══════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════ */
#sidebar {
  width: var(--sidebar);
  min-width: var(--sidebar);
  background: rgba(6,6,26,0.96);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  position: relative;
  z-index: 10;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
}

/* Logo */
#logo {
  padding: 20px 18px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 11px;
  flex-shrink: 0;
}
.logo-mark {
  width: 32px; height: 32px;
  background: linear-gradient(135deg, var(--blue) 0%, var(--purple) 100%);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 900; color: #fff; letter-spacing: -1px;
  box-shadow: 0 0 18px var(--blue-glow);
  flex-shrink: 0;
}
.logo-text { flex: 1; }
.logo-text .brand { font-size: 14px; font-weight: 800; letter-spacing: 2.5px; color: var(--white); }
.logo-text .sub   { font-size: 9px; color: var(--muted); letter-spacing: 1.5px; text-transform: uppercase; margin-top: 1px; }
.live-pill {
  display: flex; align-items: center; gap: 5px;
  padding: 3px 8px; border-radius: 12px;
  background: var(--green-dim);
  border: 1px solid rgba(0,212,160,0.2);
  font-size: 9px; font-weight: 700; color: var(--green);
  letter-spacing: 1px; text-transform: uppercase;
}
.live-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 6px var(--green);
  animation: livePulse 2s infinite;
}
@keyframes livePulse { 0%,100% { opacity:1; } 50% { opacity:0.25; } }

/* Nav */
.sidebar-label {
  padding: 14px 18px 7px;
  font-size: 9.5px; font-weight: 700;
  letter-spacing: 2px; text-transform: uppercase;
  color: var(--muted);
  flex-shrink: 0;
}
.nav-btn {
  display: flex; align-items: center; gap: 10px;
  width: calc(100% - 14px); margin: 1px 7px;
  padding: 9px 11px; border-radius: 7px;
  background: transparent; border: 1px solid transparent;
  color: var(--muted2); cursor: pointer;
  font-size: 12.5px; font-weight: 500; text-align: left;
  transition: all 0.18s;
  flex-shrink: 0;
}
.nav-btn:hover { background: rgba(255,255,255,0.035); color: var(--text); }
.nav-btn.active {
  background: var(--blue-dim2); color: var(--white);
  border-color: rgba(21,62,237,0.22);
  box-shadow: inset 3px 0 0 var(--blue);
}
.nav-btn .icon { font-size: 14px; width: 20px; text-align: center; }

/* Skill buttons */
.skill-btn {
  display: flex; align-items: center; gap: 8px;
  width: calc(100% - 14px); margin: 1px 7px;
  padding: 7px 11px; border-radius: 6px;
  background: transparent; border: 1px solid transparent;
  color: var(--muted); cursor: pointer;
  font-size: 11.5px; font-weight: 500; text-align: left;
  transition: all 0.15s;
  flex-shrink: 0;
}
.skill-btn:hover {
  border-color: rgba(21,62,237,0.25);
  color: var(--text); background: var(--blue-dim);
}

/* Account list */
#account-list { flex: 1; overflow-y: auto; padding-bottom: 16px; }
#account-list::-webkit-scrollbar { width: 3px; }
#account-list::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 2px; }

#account-search {
  margin: 8px 10px;
  padding: 8px 12px;
  border-radius: 6px;
  background: rgba(255,255,255,0.035);
  border: 1px solid var(--border);
  color: var(--text); font-size: 12px;
  width: calc(100% - 20px); outline: none;
  transition: border-color 0.18s;
  flex-shrink: 0;
}
#account-search::placeholder { color: var(--muted); }
#account-search:focus { border-color: rgba(21,62,237,0.45); }

.account-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 7px 11px; margin: 1px 7px; border-radius: 6px;
  cursor: pointer; transition: all 0.12s;
}
.account-item:hover { background: rgba(255,255,255,0.035); }
.account-item.selected { background: var(--blue-dim2); border: 1px solid rgba(21,62,237,0.2); }
.account-item .aname { flex: 1; font-size: 12px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.acc-badges { display: flex; gap: 4px; margin-left: 6px; align-items: center; }
.spill {
  font-size: 9.5px; font-weight: 700; padding: 1px 5px; border-radius: 3px;
  background: var(--blue-dim); color: var(--blue);
}
.spill.g { background: var(--green-dim); color: var(--green); }
.spill.c { font-size: 9px; color: var(--muted); background: transparent; }

/* ══════════════════════════════════════════
   MAIN
══════════════════════════════════════════ */
#main {
  flex: 1; display: flex; flex-direction: column;
  overflow: hidden; position: relative; z-index: 1;
}

.tab-pane { display: none; flex: 1; flex-direction: column; overflow: hidden; }
.tab-pane.active { display: flex; }

/* ══════════════════════════════════════════
   DASHBOARD
══════════════════════════════════════════ */
#tab-dashboard { overflow-y: auto; }
#dash-wrap { padding: 32px 36px 48px; min-height: 100%; }

.dash-top {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 28px;
}
.dash-headline { font-size: 26px; font-weight: 800; color: var(--white); letter-spacing: -0.6px; line-height: 1.1; }
.dash-tagline { font-size: 13px; color: var(--muted2); margin-top: 5px; }
.dash-meta {
  text-align: right; padding: 12px 18px;
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--border); border-radius: 10px;
  min-width: 180px;
}
.dash-meta .dm-date { font-size: 13px; font-weight: 600; color: var(--text); }
.dash-meta .dm-time { font-size: 22px; font-weight: 800; color: var(--white); letter-spacing: -0.5px; margin-top: 2px; }
.dash-meta .dm-label { font-size: 9.5px; color: var(--muted); text-transform: uppercase; letter-spacing: 1.5px; margin-top: 3px; }

/* KPI row */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }

.kpi {
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--border); border-radius: 12px;
  padding: 20px 20px 16px; position: relative; overflow: hidden;
  transition: border-color 0.2s, transform 0.2s;
}
.kpi:hover { border-color: var(--border-hi); transform: translateY(-2px); }
.kpi::after {
  content: '';
  position: absolute; top: 0; left: 12px; right: 12px; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(21,62,237,0.5), transparent);
}
.kpi-label { font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 1.8px; margin-bottom: 10px; }
.kpi-num {
  font-size: 38px; font-weight: 900; color: var(--white);
  letter-spacing: -2px; line-height: 1;
  font-variant-numeric: tabular-nums;
}
.kpi-unit { font-size: 20px; font-weight: 700; color: var(--muted2); vertical-align: super; font-size: 16px; }
.kpi-suffix { font-size: 22px; font-weight: 800; color: var(--muted2); }
.kpi-sub { font-size: 11px; color: var(--muted2); margin-top: 8px; }
.kpi-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 9px; border-radius: 5px;
  font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.8px;
  margin-top: 10px;
}
.kpi-badge.amber { background: var(--amber-dim); color: var(--amber); border: 1px solid rgba(245,166,35,0.22); }
.kpi-badge.green { background: var(--green-dim); color: var(--green); border: 1px solid rgba(0,212,160,0.22); }
.kpi-badge.red   { background: var(--red-dim);   color: var(--red);   border: 1px solid rgba(246,87,74,0.22); }
.kpi-badge.blue  { background: var(--blue-dim2); color: var(--blue-light); border: 1px solid rgba(21,62,237,0.22); }

/* KPI accent bar */
.kpi-bar { height: 3px; border-radius: 2px; margin-top: 14px; background: rgba(255,255,255,0.06); overflow: hidden; }
.kpi-bar-fill { height: 100%; border-radius: 2px; transition: width 1.4s cubic-bezier(0.4,0,0.2,1); }

/* Dashboard two-col */
.dash-cols { display: grid; grid-template-columns: 1.5fr 1fr; gap: 18px; margin-bottom: 18px; }
.dash-card {
  background: rgba(255,255,255,0.022);
  border: 1px solid var(--border); border-radius: 12px; padding: 22px;
}
.dash-card-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px; padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.dash-card-title { font-size: 10px; font-weight: 800; color: var(--muted2); text-transform: uppercase; letter-spacing: 2px; }
.dash-card-tag { font-size: 10px; color: var(--muted); }

/* Opportunity rows */
.opp {
  display: flex; align-items: center; gap: 12px;
  padding: 9px 8px; border-radius: 8px; cursor: pointer;
  transition: background 0.15s; margin: 0 -8px;
  border-bottom: 1px solid var(--border);
}
.opp:last-child { border-bottom: none; }
.opp:hover { background: rgba(255,255,255,0.03); }
.opp-num { font-size: 10px; font-weight: 800; color: var(--muted); width: 18px; text-align: right; flex-shrink: 0; }
.opp-ring { position: relative; width: 38px; height: 38px; flex-shrink: 0; }
.opp-ring svg { position: absolute; top: 0; left: 0; }
.opp-ring-val {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 900; color: var(--white);
}
.opp-body { flex: 1; min-width: 0; }
.opp-name { font-size: 13.5px; font-weight: 700; color: var(--white); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.opp-meta { font-size: 11px; color: var(--muted2); margin-top: 2px; }
.opp-right { text-align: right; flex-shrink: 0; }
.opp-val { font-size: 14px; font-weight: 800; color: var(--white); }
.opp-val-sub { font-size: 10px; color: var(--muted); margin-top: 1px; }

/* Signal rows */
.signal {
  display: flex; align-items: flex-start; gap: 11px;
  padding: 9px 0; border-bottom: 1px solid var(--border);
}
.signal:last-child { border-bottom: none; }
.signal-icon {
  width: 28px; height: 28px; border-radius: 6px;
  background: var(--red-dim); border: 1px solid rgba(246,87,74,0.2);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; flex-shrink: 0;
}
.signal-co { font-size: 13px; font-weight: 700; color: var(--white); }
.signal-txt { font-size: 11px; color: var(--muted2); margin-top: 2px; line-height: 1.45; }
.signal-tag {
  font-size: 9.5px; font-weight: 800; padding: 2px 7px; border-radius: 4px;
  background: var(--red-dim); color: var(--red); white-space: nowrap;
  align-self: flex-start; flex-shrink: 0; margin-top: 1px;
}
.signal-tag.amber { background: var(--amber-dim); color: var(--amber); }

/* Strategy split */
.strat-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-top: 0; }
.strat-card {
  background: rgba(255,255,255,0.018);
  border: 1px solid var(--border); border-radius: 10px;
  padding: 16px; text-align: center;
}
.strat-icon { font-size: 22px; margin-bottom: 8px; }
.strat-name { font-size: 10px; font-weight: 700; color: var(--muted2); text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 10px; line-height: 1.4; }
.strat-num { font-size: 28px; font-weight: 900; color: var(--white); letter-spacing: -1px; }
.strat-sub { font-size: 10px; color: var(--muted); margin-top: 4px; }
.strat-bar-wrap { height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; margin-top: 12px; overflow: hidden; }
.strat-bar { height: 100%; border-radius: 2px; transition: width 1.6s cubic-bezier(0.4,0,0.2,1); }

/* ══════════════════════════════════════════
   CHAT
══════════════════════════════════════════ */
#chat-header {
  padding: 14px 24px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px;
  background: rgba(6,6,26,0.85);
  backdrop-filter: blur(16px);
  flex-shrink: 0;
}
#chat-header h2 { font-size: 14px; font-weight: 700; color: var(--white); }
#selected-account-tag {
  font-size: 11px; padding: 4px 10px; border-radius: 16px;
  background: var(--blue-dim2); color: var(--blue-light);
  border: 1px solid rgba(21,62,237,0.3);
  display: none; align-items: center; gap: 6px;
}
#clear-account { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 12px; padding: 0; }
#clear-account:hover { color: var(--red); }
#deck-btn {
  padding: 5px 12px; border-radius: 6px; font-size: 11px; font-weight: 700;
  background: transparent; border: 1px solid rgba(0,212,160,0.35);
  color: var(--green); cursor: pointer; transition: all 0.15s; display: none; white-space: nowrap;
}
#deck-btn:hover { background: var(--green-dim); }
#deck-btn.loading { opacity: 0.5; cursor: not-allowed; }

#messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 18px; }
#messages::-webkit-scrollbar { width: 3px; }
#messages::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 2px; }

.msg { max-width: 80%; display: flex; flex-direction: column; gap: 5px; }
.msg.user { align-self: flex-end; align-items: flex-end; }
.msg.assistant { align-self: flex-start; align-items: flex-start; }
.msg-role { font-size: 9.5px; color: var(--muted); text-transform: uppercase; letter-spacing: 1.5px; padding: 0 4px; }
.msg-bubble {
  padding: 13px 17px; border-radius: 14px;
  font-size: 13.5px; line-height: 1.65; word-break: break-word;
}
.msg.user .msg-bubble {
  background: linear-gradient(135deg, var(--blue), var(--blue-light));
  color: #fff; border-bottom-right-radius: 4px;
  box-shadow: 0 4px 20px rgba(21,62,237,0.28);
}
.msg.assistant .msg-bubble {
  background: rgba(255,255,255,0.035); color: var(--text);
  border: 1px solid var(--border); border-bottom-left-radius: 4px;
}
.msg-bubble table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 12.5px; }
.msg-bubble th { background: rgba(21,62,237,0.2); color: var(--white); padding: 7px 11px; text-align: left; font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.8px; }
.msg-bubble td { padding: 6px 11px; border-bottom: 1px solid var(--border); }
.msg-bubble tr:last-child td { border-bottom: none; }
.msg-bubble h1, .msg-bubble h2 { color: #7090FF; margin: 14px 0 7px; font-size: 15px; font-weight: 700; }
.msg-bubble h3 { color: var(--white); margin: 11px 0 5px; font-size: 13.5px; font-weight: 600; }
.msg-bubble ul, .msg-bubble ol { padding-left: 20px; margin: 5px 0; }
.msg-bubble li { margin: 3px 0; }
.msg-bubble code { background: rgba(21,62,237,0.18); padding: 2px 6px; border-radius: 4px; font-size: 12px; font-family: 'SF Mono','Fira Code',monospace; color: #A8C0FF; }
.msg-bubble pre { background: rgba(0,0,0,0.35); padding: 12px; border-radius: 8px; overflow-x: auto; border: 1px solid var(--border); margin: 8px 0; }
.msg-bubble strong { color: var(--white); }
.msg-bubble em { color: var(--muted2); }
.msg-bubble blockquote { border-left: 3px solid var(--blue); padding-left: 13px; color: var(--muted2); margin: 8px 0; font-style: italic; }
.msg-bubble hr { border: none; border-top: 1px solid var(--border); margin: 12px 0; }

#typing-row { padding: 0 24px 10px; flex-shrink: 0; }
#typing-indicator {
  display: none; align-items: center; gap: 5px;
  padding: 11px 16px; background: rgba(255,255,255,0.035);
  border: 1px solid var(--border); border-radius: 14px; border-bottom-left-radius: 4px;
  max-width: 90px;
}
#typing-indicator.visible { display: flex; }
.dot { width: 5px; height: 5px; border-radius: 50%; background: var(--blue); animation: dotBounce 1.2s infinite; }
.dot:nth-child(2) { animation-delay: 0.18s; }
.dot:nth-child(3) { animation-delay: 0.36s; }
@keyframes dotBounce { 0%,60%,100% { transform:translateY(0); opacity:0.35; } 30% { transform:translateY(-6px); opacity:1; } }

#chat-input-area {
  padding: 14px 24px 18px;
  border-top: 1px solid var(--border);
  background: rgba(6,6,26,0.85);
  backdrop-filter: blur(16px);
  flex-shrink: 0;
}
#input-row { display: flex; gap: 10px; align-items: flex-end; }
#chat-input {
  flex: 1; padding: 11px 15px; border-radius: 10px;
  background: rgba(255,255,255,0.04); border: 1px solid var(--border);
  color: var(--text); font-size: 13.5px; font-family: var(--font);
  resize: none; outline: none; min-height: 44px; max-height: 140px; line-height: 1.5;
  transition: border-color 0.18s, box-shadow 0.18s;
}
#chat-input::placeholder { color: var(--muted); }
#chat-input:focus {
  border-color: rgba(21,62,237,0.5);
  box-shadow: 0 0 0 3px rgba(21,62,237,0.08);
}
#send-btn {
  padding: 11px 20px;
  background: linear-gradient(135deg, var(--blue), var(--blue-light));
  color: #fff; border: none; border-radius: 10px;
  cursor: pointer; font-size: 13.5px; font-weight: 700;
  transition: all 0.18s;
  box-shadow: 0 4px 14px rgba(21,62,237,0.3);
}
#send-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(21,62,237,0.45); }
#send-btn:disabled { opacity: 0.38; cursor: not-allowed; transform: none; box-shadow: none; }
#input-hint { font-size: 10.5px; color: var(--muted); margin-top: 8px; }

/* Welcome screen */
#welcome {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; gap: 10px; text-align: center; padding: 40px;
}
.welcome-icon { font-size: 44px; margin-bottom: 6px; opacity: 0.7; }
#welcome .big { font-size: 24px; font-weight: 800; color: var(--white); letter-spacing: -0.4px; }
#welcome .sub { font-size: 14px; color: var(--muted2); max-width: 380px; line-height: 1.65; margin-top: 2px; }
.quick-chips { display: flex; flex-wrap: wrap; gap: 7px; justify-content: center; margin-top: 18px; }
.chip {
  padding: 7px 14px; border-radius: 20px;
  background: rgba(255,255,255,0.04); border: 1px solid var(--border);
  color: var(--muted2); font-size: 12px; cursor: pointer;
  transition: all 0.15s;
}
.chip:hover { border-color: rgba(21,62,237,0.4); color: var(--text); background: var(--blue-dim); }

/* ══════════════════════════════════════════
   NOTES
══════════════════════════════════════════ */
#tab-notes { overflow-y: auto; }
#notes-pane { padding: 32px; max-width: 760px; }
#notes-pane h2 { font-size: 20px; font-weight: 800; color: var(--white); letter-spacing: -0.3px; }
#notes-pane .desc { font-size: 13px; color: var(--muted2); margin: 6px 0 24px; line-height: 1.6; }
.form-group { margin-bottom: 18px; }
.form-group label { display: block; font-size: 10px; font-weight: 800; color: var(--muted2); text-transform: uppercase; letter-spacing: 1.8px; margin-bottom: 8px; }
.form-group select, .form-group textarea {
  width: 100%; padding: 10px 13px; border-radius: 8px;
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  color: var(--text); font-size: 13.5px; font-family: var(--font); outline: none;
  transition: border-color 0.18s;
}
.form-group select:focus, .form-group textarea:focus { border-color: rgba(21,62,237,0.5); }
.form-group textarea { resize: vertical; min-height: 160px; line-height: 1.6; }
.form-group select option { background: var(--bg3); }
.btn-primary {
  padding: 11px 22px;
  background: linear-gradient(135deg, var(--blue), var(--blue-light));
  color: #fff; border: none; border-radius: 8px;
  cursor: pointer; font-size: 13px; font-weight: 700;
  transition: all 0.18s; box-shadow: 0 4px 12px rgba(21,62,237,0.25);
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(21,62,237,0.4); }
.btn-primary:disabled { opacity: 0.38; cursor: not-allowed; transform: none; box-shadow: none; }
.btn-secondary {
  padding: 11px 22px; background: transparent; color: var(--text);
  border: 1px solid var(--border); border-radius: 8px;
  cursor: pointer; font-size: 13px; font-weight: 500;
  transition: border-color 0.15s; margin-left: 10px;
}
.btn-secondary:hover { border-color: var(--border-hi); }
#notes-result {
  margin-top: 26px; padding: 22px;
  background: rgba(255,255,255,0.02); border: 1px solid var(--border);
  border-radius: 12px; display: none;
}
.result-label { font-size: 9.5px; font-weight: 800; color: var(--blue-light); text-transform: uppercase; letter-spacing: 2px; margin-bottom: 9px; }
.insight-box { padding: 13px 16px; background: var(--blue-dim2); border-left: 3px solid var(--blue); border-radius: 0 8px 8px 0; font-size: 13.5px; color: var(--text); line-height: 1.6; }
.summary-text { font-size: 13.5px; color: var(--muted2); line-height: 1.7; }
.file-preview {
  background: rgba(0,0,0,0.25); border: 1px solid var(--border); border-radius: 8px;
  padding: 13px; font-size: 11.5px; font-family: 'SF Mono','Fira Code',monospace;
  color: var(--muted2); max-height: 180px; overflow-y: auto; white-space: pre-wrap; line-height: 1.6;
}
.result-section { margin-bottom: 18px; }
.save-actions { display: flex; gap: 10px; margin-top: 18px; }

/* ══════════════════════════════════════════
   ACCOUNTS
══════════════════════════════════════════ */
#tab-accounts { overflow-y: auto; }
#accounts-pane { padding: 32px; }
#accounts-pane h2 { font-size: 20px; font-weight: 800; color: var(--white); letter-spacing: -0.3px; }
#accounts-pane .desc { font-size: 13px; color: var(--muted2); margin: 6px 0 22px; }
.filter-row { display: flex; gap: 7px; margin-bottom: 20px; flex-wrap: wrap; }
.filter-btn {
  padding: 5px 13px; border-radius: 16px; font-size: 11.5px; font-weight: 600;
  background: transparent; border: 1px solid var(--border); color: var(--muted2); cursor: pointer; transition: all 0.15s;
}
.filter-btn.active, .filter-btn:hover { background: var(--blue-dim); border-color: rgba(21,62,237,0.3); color: var(--blue-light); }
.accounts-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 11px; }
.account-card {
  background: rgba(255,255,255,0.022); border: 1px solid var(--border); border-radius: 10px;
  padding: 15px 17px; cursor: pointer; transition: all 0.18s; position: relative; overflow: hidden;
}
.account-card:hover {
  border-color: rgba(21,62,237,0.3); background: rgba(21,62,237,0.05);
  transform: translateY(-2px); box-shadow: 0 10px 28px rgba(0,0,0,0.35);
}
.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.card-name { font-size: 13.5px; font-weight: 700; color: var(--white); }
.card-badges { display: flex; gap: 5px; }
.badge {
  font-size: 9.5px; font-weight: 800; padding: 2px 7px; border-radius: 4px;
  background: var(--blue-dim); color: var(--blue-light); border: 1px solid rgba(21,62,237,0.2);
}
.badge.c { background: var(--red-dim); color: var(--red); border-color: rgba(246,87,74,0.2); }
.badge.g { background: var(--green-dim); color: var(--green); border-color: rgba(0,212,160,0.2); }
.score-bars { display: flex; gap: 10px; }
.sb-item { flex: 1; }
.sb-label { font-size: 9.5px; color: var(--muted); margin-bottom: 4px; }
.sb-track { height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.sb-fill { height: 100%; border-radius: 2px; }
.sb-fill.icp  { background: linear-gradient(90deg, var(--blue), var(--purple)); }
.sb-fill.deal { background: linear-gradient(90deg, var(--green), #00A880); }

/* ══════════════════════════════════════════
   TOAST
══════════════════════════════════════════ */
#toast {
  position: fixed; bottom: 24px; right: 24px;
  padding: 12px 20px; border-radius: 10px;
  font-size: 13px; font-weight: 700;
  background: linear-gradient(135deg, var(--blue), var(--blue-light));
  color: #fff; transform: translateY(80px); opacity: 0;
  transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1);
  z-index: 1000; box-shadow: 0 8px 24px rgba(21,62,237,0.35);
}
#toast.show { transform: translateY(0); opacity: 1; }
#toast.error {
  background: linear-gradient(135deg, var(--red), #D94035);
  box-shadow: 0 8px 24px rgba(246,87,74,0.35);
}

::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 2px; }

/* ══════════════════════════════════════════
   BOARD REPORT BUTTON
══════════════════════════════════════════ */
.btn-board {
  padding: 8px 16px; border-radius: 8px;
  background: linear-gradient(135deg, var(--purple), #9B6BFF);
  color: #fff; border: none; cursor: pointer;
  font-size: 12px; font-weight: 700;
  transition: all 0.18s; box-shadow: 0 4px 14px rgba(123,92,245,0.3);
  white-space: nowrap; align-self: flex-start;
}
.btn-board:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(123,92,245,0.45); }
.btn-board:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

/* ══════════════════════════════════════════
   PIPELINE RADAR
══════════════════════════════════════════ */
#tab-radar { overflow-y: auto; }
#radar-wrap { padding: 28px 36px; }
.radar-title { font-size: 22px; font-weight: 800; color: var(--white); letter-spacing: -0.4px; }
.radar-sub { font-size: 12px; color: var(--muted2); margin-top: 4px; margin-bottom: 22px; }
.radar-layout { display: flex; gap: 22px; align-items: flex-start; }
.radar-svg-container {
  flex: 1; max-width: 580px;
  background: rgba(255,255,255,0.018); border: 1px solid var(--border);
  border-radius: 16px; overflow: hidden; padding: 10px;
}
#radar-svg { width: 100%; height: auto; display: block; }
@keyframes radarSweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
#radar-sweep { animation: radarSweep 4s linear infinite; transform-origin: 300px 300px; }
.radar-sidebar { width: 230px; flex-shrink: 0; display: flex; flex-direction: column; gap: 14px; }
.radar-panel {
  background: rgba(255,255,255,0.022); border: 1px solid var(--border);
  border-radius: 10px; padding: 16px;
}
.radar-panel-title { font-size: 9.5px; font-weight: 800; color: var(--muted2); text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; }
.legend-item { display: flex; align-items: center; gap: 9px; padding: 3px 0; font-size: 11.5px; color: var(--muted2); }
.legend-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.rhi { display: flex; align-items: center; gap: 9px; padding: 6px 0; border-bottom: 1px solid var(--border); cursor: pointer; transition: opacity 0.15s; }
.rhi:last-child { border-bottom: none; }
.rhi:hover { opacity: 0.75; }
.rhi-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.rhi-name { flex: 1; font-size: 11.5px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rhi-score { font-size: 10px; font-weight: 800; color: var(--muted); }

/* ══════════════════════════════════════════
   PITCH SIMULATOR
══════════════════════════════════════════ */
#tab-simulator { overflow: hidden; display: none; flex-direction: column; }
#tab-simulator.active { display: flex; }
#sim-setup {
  padding: 22px 32px 18px; flex-shrink: 0;
  border-bottom: 1px solid var(--border);
  background: rgba(6,6,26,0.9);
}
.sim-title { font-size: 18px; font-weight: 800; color: var(--white); letter-spacing: -0.3px; }
.sim-sub { font-size: 12px; color: var(--muted2); margin-top: 3px; margin-bottom: 14px; }
.sim-controls { display: flex; gap: 12px; align-items: flex-end; }
.sim-select-wrap { flex: 1; }
.sim-select-wrap label { display: block; font-size: 9.5px; font-weight: 800; color: var(--muted2); text-transform: uppercase; letter-spacing: 1.8px; margin-bottom: 7px; }
.sim-select-wrap select {
  width: 100%; padding: 9px 12px; border-radius: 8px;
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  color: var(--text); font-size: 13px; font-family: var(--font); outline: none;
}
.sim-select-wrap select:focus { border-color: rgba(246,87,74,0.5); }
.btn-sim-start {
  padding: 9px 18px; border-radius: 8px;
  background: linear-gradient(135deg, #A52A2A, var(--red));
  color: #fff; border: none; cursor: pointer;
  font-size: 13px; font-weight: 700;
  transition: all 0.18s; box-shadow: 0 4px 14px rgba(246,87,74,0.3);
  white-space: nowrap;
}
.btn-sim-start:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(246,87,74,0.45); }
#sim-persona-bar {
  padding: 8px 32px; flex-shrink: 0;
  display: none; align-items: center; gap: 14px;
  border-bottom: 1px solid var(--border);
  background: rgba(246,87,74,0.04);
}
#sim-persona-bar.active { display: flex; }
.sim-persona {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 12px; border-radius: 7px;
  background: var(--red-dim); border: 1px solid rgba(246,87,74,0.22);
}
.sim-persona-icon { font-size: 18px; }
.sim-persona-name { font-size: 12px; font-weight: 700; color: var(--red); }
.sim-persona-sub { font-size: 10.5px; color: var(--muted2); }
.btn-score {
  padding: 6px 13px; border-radius: 6px;
  background: transparent; border: 1px solid rgba(0,212,160,0.3);
  color: var(--green); font-size: 11px; font-weight: 700; cursor: pointer;
  transition: all 0.15s; white-space: nowrap; margin-left: auto;
}
.btn-score:hover { background: var(--green-dim); }
#sim-messages {
  flex: 1; overflow-y: auto; padding: 20px 32px;
  display: flex; flex-direction: column; gap: 14px;
}
#sim-messages::-webkit-scrollbar { width: 3px; }
#sim-messages::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 2px; }
.sim-note { text-align: center; font-size: 10.5px; color: var(--muted); padding: 2px 0; }
.sim-opp .msg-bubble { background: rgba(246,87,74,0.07) !important; border: 1px solid rgba(246,87,74,0.18) !important; }
.sim-opp .msg-role { color: var(--red) !important; }
#sim-input-area {
  padding: 12px 32px 16px; border-top: 1px solid var(--border);
  background: rgba(6,6,26,0.85); backdrop-filter: blur(16px); flex-shrink: 0;
}
#sim-input-row { display: flex; gap: 10px; align-items: flex-end; }
#sim-input {
  flex: 1; padding: 10px 14px; border-radius: 10px;
  background: rgba(255,255,255,0.04); border: 1px solid var(--border);
  color: var(--text); font-size: 13px; font-family: var(--font);
  resize: none; outline: none; min-height: 42px; max-height: 120px; line-height: 1.5;
  transition: border-color 0.18s;
}
#sim-input:focus { border-color: rgba(246,87,74,0.4); }
#sim-send-btn {
  padding: 10px 18px; border-radius: 10px;
  background: linear-gradient(135deg, #A52A2A, var(--red));
  color: #fff; border: none; cursor: pointer;
  font-size: 13px; font-weight: 700; transition: all 0.18s;
  box-shadow: 0 4px 12px rgba(246,87,74,0.3);
}
#sim-send-btn:hover { transform: translateY(-1px); }
#sim-send-btn:disabled { opacity: 0.38; cursor: not-allowed; transform: none; }

/* ══════════════════════════════════════════
   SIGNAL FEED
══════════════════════════════════════════ */
#tab-signals { overflow-y: auto; }
#signals-wrap { padding: 28px 36px; max-width: 860px; }
.signals-title { font-size: 22px; font-weight: 800; color: var(--white); letter-spacing: -0.4px; }
.signals-sub { font-size: 12px; color: var(--muted2); margin-top: 4px; margin-bottom: 22px; }
.signal-card {
  background: rgba(255,255,255,0.022); border: 1px solid var(--border);
  border-radius: 10px; padding: 15px 18px; margin-bottom: 10px;
  display: flex; align-items: flex-start; gap: 14px;
  transition: border-color 0.18s, transform 0.15s;
}
.signal-card:hover { transform: translateX(4px); border-color: var(--border-hi); }
.signal-card.urg { border-color: rgba(246,87,74,0.3); background: rgba(246,87,74,0.03); }
.signal-card.amb { border-color: rgba(245,166,35,0.2); }
.sc-ico {
  width: 36px; height: 36px; border-radius: 8px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 16px;
}
.sc-ico.red   { background: var(--red-dim);   border: 1px solid rgba(246,87,74,0.2); }
.sc-ico.amber { background: var(--amber-dim); border: 1px solid rgba(245,166,35,0.2); }
.sc-ico.blue  { background: var(--blue-dim);  border: 1px solid rgba(21,62,237,0.2); }
.sc-body { flex: 1; min-width: 0; }
.sc-co { font-size: 14px; font-weight: 700; color: var(--white); }
.sc-txt { font-size: 12px; color: var(--muted2); margin-top: 3px; line-height: 1.5; }
.sc-right { display: flex; flex-direction: column; align-items: flex-end; gap: 7px; flex-shrink: 0; }
.sc-tag { font-size: 9.5px; font-weight: 800; padding: 3px 8px; border-radius: 4px; white-space: nowrap; }
.sc-tag.red   { background: var(--red-dim);   color: var(--red); }
.sc-tag.amber { background: var(--amber-dim); color: var(--amber); }
.sc-tag.blue  { background: var(--blue-dim2); color: var(--blue-light); }
.sc-act {
  padding: 4px 11px; border-radius: 5px; font-size: 10.5px; font-weight: 700;
  background: transparent; border: 1px solid var(--border);
  color: var(--muted2); cursor: pointer; transition: all 0.15s; white-space: nowrap;
}
.sc-act:hover { border-color: rgba(21,62,237,0.4); color: var(--blue-light); background: var(--blue-dim); }

/* ══════════════════════════════════════════
   PARTNERSHIP INTELLIGENCE
══════════════════════════════════════════ */
#tab-partners { overflow-y: auto; }
#partners-wrap { padding: 28px 36px; max-width: 900px; }
.partners-title { font-size: 22px; font-weight: 800; color: var(--white); letter-spacing: -0.4px; }
.partners-sub { font-size: 12px; color: var(--muted2); margin-top: 4px; margin-bottom: 26px; }

.partner-form-card {
  background: rgba(255,255,255,0.022); border: 1px solid var(--border);
  border-radius: 12px; padding: 22px; margin-bottom: 22px;
}
.partner-form-title { font-size: 11px; font-weight: 800; color: var(--muted2); text-transform: uppercase; letter-spacing: 2px; margin-bottom: 16px; }
.partner-form-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.pf-group { display: flex; flex-direction: column; gap: 6px; }
.pf-group label { font-size: 9.5px; font-weight: 800; color: var(--muted); text-transform: uppercase; letter-spacing: 1.5px; }
.pf-group input, .pf-group select, .pf-group textarea {
  padding: 9px 13px; border-radius: 7px;
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  color: var(--text); font-size: 13px; font-family: var(--font); outline: none;
  transition: border-color 0.18s;
}
.pf-group input:focus, .pf-group select:focus, .pf-group textarea:focus { border-color: rgba(123,92,245,0.5); }
.pf-group.grow { flex: 1; min-width: 200px; }
.pf-group select option { background: var(--bg3); }
.btn-validate {
  padding: 10px 20px; border-radius: 8px;
  background: linear-gradient(135deg, var(--purple), #9B6BFF);
  color: #fff; border: none; cursor: pointer;
  font-size: 13px; font-weight: 700;
  transition: all 0.18s; box-shadow: 0 4px 14px rgba(123,92,245,0.3);
  white-space: nowrap; align-self: flex-end;
}
.btn-validate:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(123,92,245,0.45); }
.btn-validate:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

/* Validation result card */
#partner-result { display: none; }
.verdict-banner {
  padding: 14px 20px; border-radius: 10px; margin-bottom: 20px;
  display: flex; align-items: center; gap: 14px;
}
.verdict-banner.strong  { background: rgba(0,212,160,0.1);  border: 1px solid rgba(0,212,160,0.3); }
.verdict-banner.potential { background: rgba(21,62,237,0.1); border: 1px solid rgba(21,62,237,0.3); }
.verdict-banner.weak    { background: rgba(245,166,35,0.1);  border: 1px solid rgba(245,166,35,0.3); }
.verdict-banner.not-rec { background: rgba(246,87,74,0.1);   border: 1px solid rgba(246,87,74,0.3); }
.verdict-icon { font-size: 28px; }
.verdict-label { font-size: 16px; font-weight: 800; }
.verdict-label.strong  { color: var(--green); }
.verdict-label.potential { color: var(--blue-light); }
.verdict-label.weak    { color: var(--amber); }
.verdict-label.not-rec { color: var(--red); }
.verdict-reason { font-size: 12.5px; color: var(--muted2); margin-top: 3px; }
.verdict-score { margin-left: auto; font-size: 32px; font-weight: 900; color: var(--white); }
.verdict-score span { font-size: 14px; font-weight: 500; color: var(--muted); }

.dim-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-bottom: 18px; }
.dim-card {
  background: rgba(255,255,255,0.02); border: 1px solid var(--border);
  border-radius: 9px; padding: 14px;
}
.dim-name { font-size: 10px; font-weight: 800; color: var(--muted2); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }
.dim-score-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.dim-score-num { font-size: 22px; font-weight: 900; color: var(--white); }
.dim-score-max { font-size: 12px; color: var(--muted); }
.dim-bar-track { flex: 1; height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.dim-bar-fill { height: 100%; border-radius: 2px; transition: width 1s cubic-bezier(0.4,0,0.2,1); }
.dim-finding { font-size: 11.5px; color: var(--muted2); line-height: 1.5; }

.partner-meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 18px; }
.pmeta-card {
  background: rgba(255,255,255,0.02); border: 1px solid var(--border);
  border-radius: 9px; padding: 14px;
}
.pmeta-label { font-size: 9.5px; font-weight: 800; color: var(--muted2); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }
.pmeta-value { font-size: 12.5px; color: var(--text); line-height: 1.5; }
.pmeta-tag {
  display: inline-block; padding: 3px 9px; border-radius: 4px; font-size: 10px; font-weight: 700;
  background: var(--purple); color: #fff; margin: 2px 3px 2px 0;
}

.partner-history-title { font-size: 10px; font-weight: 800; color: var(--muted2); text-transform: uppercase; letter-spacing: 2px; margin: 24px 0 12px; }
.ph-row {
  display: flex; align-items: center; gap: 12px; padding: 9px 12px;
  background: rgba(255,255,255,0.018); border: 1px solid var(--border);
  border-radius: 8px; margin-bottom: 7px; cursor: pointer; transition: border-color 0.15s;
}
.ph-row:hover { border-color: var(--border-hi); }
.ph-name { flex: 1; font-size: 13px; font-weight: 600; color: var(--text); }
.ph-market { font-size: 10px; color: var(--muted); }
.ph-verdict {
  font-size: 9.5px; font-weight: 800; padding: 2px 8px; border-radius: 4px;
}
.ph-verdict.strong   { background: rgba(0,212,160,0.12); color: var(--green); }
.ph-verdict.potential { background: var(--blue-dim2); color: var(--blue-light); }
.ph-verdict.weak     { background: rgba(245,166,35,0.12); color: var(--amber); }
.ph-score { font-size: 13px; font-weight: 800; color: var(--white); }
</style>
</head>
<body>

<!-- ══════════════════ SIDEBAR ══════════════════ -->
<div id="sidebar">
  <div id="logo">
    <div class="logo-mark">J</div>
    <div class="logo-text">
      <div class="brand">JAKALA</div>
      <div class="sub">GTM Operating System</div>
    </div>
    <div class="live-pill"><div class="live-dot"></div>LIVE</div>
  </div>

  <div class="sidebar-label">Navigate</div>
  <button class="nav-btn" onclick="showTab('dashboard')" id="nav-dashboard">
    <span class="icon">⚡</span> Command Center
  </button>
  <button class="nav-btn active" onclick="showTab('chat')" id="nav-chat">
    <span class="icon">💬</span> GTM Assistant
  </button>
  <button class="nav-btn" onclick="showTab('notes')" id="nav-notes">
    <span class="icon">📝</span> Meeting Notes
  </button>
  <button class="nav-btn" onclick="showTab('accounts')" id="nav-accounts">
    <span class="icon">🏢</span> Accounts
  </button>
  <button class="nav-btn" onclick="showTab('radar')" id="nav-radar">
    <span class="icon">📡</span> Pipeline Radar
  </button>
  <button class="nav-btn" onclick="showTab('simulator')" id="nav-simulator">
    <span class="icon">🎭</span> Pitch Simulator
  </button>
  <button class="nav-btn" onclick="showTab('signals')" id="nav-signals">
    <span class="icon">⚡</span> Signal Feed
  </button>
  <button class="nav-btn" onclick="showTab('partners')" id="nav-partners">
    <span class="icon">🤝</span> Partnerships
  </button>

  <div class="sidebar-label" style="margin-top:6px">Quick Skills</div>
  <button class="skill-btn" onclick="insertSkill('morning')">🌅 Morning Briefing</button>
  <button class="skill-btn" onclick="insertSkill('warroom')">⚔️ War Room</button>
  <button class="skill-btn" onclick="insertSkill('forecast')">📊 Q2 Forecast</button>
  <button class="skill-btn" onclick="insertSkill('outreach')">✉️ Outreach</button>
  <button class="skill-btn" onclick="insertSkill('pitch')">🎯 Pitch Partner</button>
  <button class="skill-btn" onclick="insertSkill('brief')">📋 Pre-Meeting Brief</button>
  <button class="skill-btn" onclick="insertSkill('revenue')">💰 Revenue Simulation</button>
  <button class="skill-btn" onclick="insertSkill('signal')">📡 Signal to Action</button>

  <div class="sidebar-label" style="margin-top:6px">Accounts</div>
  <input type="text" id="account-search" placeholder="Search accounts…" oninput="filterAccounts()">
  <div id="account-list"></div>
</div>

<!-- ══════════════════ MAIN ══════════════════ -->
<div id="main">

  <!-- ── DASHBOARD ── -->
  <div class="tab-pane" id="tab-dashboard">
    <div id="dash-wrap">
      <div class="dash-top">
        <div>
          <div class="dash-headline">Nordic Commercial Pipeline</div>
          <div class="dash-tagline">JAKALA · DK / NO / SE · Q1–Q2 2026</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:10px">
          <button class="btn-board" id="board-report-btn" onclick="generateBoardReport()">📊 Board Report</button>
          <div class="dash-meta">
            <div class="dm-label">Current time</div>
            <div class="dm-time" id="dash-time">--:--</div>
            <div class="dm-date" id="dash-date">Loading…</div>
          </div>
        </div>
      </div>

      <!-- KPI row -->
      <div class="kpi-row">
        <div class="kpi">
          <div class="kpi-label">Total Pipeline</div>
          <div class="kpi-num"><span class="kpi-unit">€</span><span id="kpi-pipeline">0.0</span><span class="kpi-suffix">M</span></div>
          <div class="kpi-sub">Nordic only · unweighted</div>
          <div class="kpi-badge amber">● AMBER</div>
          <div class="kpi-bar"><div class="kpi-bar-fill" style="background:linear-gradient(90deg,#153EED,#7B5CF5);width:0" data-w="68%"></div></div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Active Accounts</div>
          <div class="kpi-num"><span id="kpi-accounts">0</span></div>
          <div class="kpi-sub">ICP-scored opportunities</div>
          <div class="kpi-badge blue">NORDIC SCOPE</div>
          <div class="kpi-bar"><div class="kpi-bar-fill" style="background:linear-gradient(90deg,#4B6EF7,#7B5CF5);width:0" data-w="100%"></div></div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Named Buyers</div>
          <div class="kpi-num"><span id="kpi-buyers">0</span></div>
          <div class="kpi-sub">Confirmed stakeholders</div>
          <div class="kpi-badge green">CONFIRMED</div>
          <div class="kpi-bar"><div class="kpi-bar-fill" style="background:linear-gradient(90deg,#00D4A0,#00A880);width:0" data-w="40%"></div></div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Q2 Base Forecast</div>
          <div class="kpi-num"><span class="kpi-unit">€</span><span id="kpi-forecast">0</span><span class="kpi-suffix">K</span></div>
          <div class="kpi-sub">Probability-weighted · 0% closed</div>
          <div class="kpi-badge red">0 MEETINGS</div>
          <div class="kpi-bar"><div class="kpi-bar-fill" style="background:linear-gradient(90deg,#F6574A,#E04030);width:0" data-w="6%"></div></div>
        </div>
      </div>

      <!-- Two columns -->
      <div class="dash-cols">
        <!-- Top opportunities -->
        <div class="dash-card">
          <div class="dash-card-head">
            <div class="dash-card-title">Top Opportunities</div>
            <div class="dash-card-tag">By deal score · click to load</div>
          </div>
          <div id="top-opps"></div>
        </div>

        <!-- Hot signals -->
        <div class="dash-card">
          <div class="dash-card-head">
            <div class="dash-card-title">Hot Signals</div>
            <div class="dash-card-tag">Act this week</div>
          </div>
          <div id="signals-list">
            <div class="signal">
              <div class="signal-icon">🔴</div>
              <div style="flex:1">
                <div class="signal-co">Sport Outlet</div>
                <div class="signal-txt">CTO + CDO both vacant March 2026. Contact CEO Tor-André Skeie directly.</div>
              </div>
              <div class="signal-tag">URGENT</div>
            </div>
            <div class="signal">
              <div class="signal-icon">⚡</div>
              <div style="flex:1">
                <div class="signal-co">Trumf (NorgesGruppen)</div>
                <div class="signal-txt">Rikke Etholm-Idsøe — new Commercial Director role. First 90-day window open.</div>
              </div>
              <div class="signal-tag">90-DAY WINDOW</div>
            </div>
            <div class="signal">
              <div class="signal-icon">🆕</div>
              <div style="flex:1">
                <div class="signal-co">Vinmonopolet</div>
                <div class="signal-txt">Espen Terland new CDO (ex-XXL 15 yrs). Agenda not yet set — honeymoon phase.</div>
              </div>
              <div class="signal-tag amber">NEW EXEC</div>
            </div>
            <div class="signal">
              <div class="signal-icon">🏗️</div>
              <div style="flex:1">
                <div class="signal-co">Skeidar</div>
                <div class="signal-txt">CIO Sujit Nath identified. "Best furniture portal" ambition declared publicly.</div>
              </div>
              <div class="signal-tag amber">NAMED BUYER</div>
            </div>
            <div class="signal">
              <div class="signal-icon">🎓</div>
              <div style="flex:1">
                <div class="signal-co">BI Handelshøyskolen</div>
                <div class="signal-txt">Rector Karen Spens leaving August 2026. Transition window open now.</div>
              </div>
              <div class="signal-tag amber">TRANSITION</div>
            </div>
          </div>
        </div>
      </div>

      <!-- GTM Strategy split -->
      <div class="dash-card" style="margin-top:18px">
        <div class="dash-card-head">
          <div class="dash-card-title">GTM Strategy Distribution</div>
          <div class="dash-card-tag">Accounts by entry strategy</div>
        </div>
        <div class="strat-row">
          <div class="strat-card">
            <div class="strat-icon">💡</div>
            <div class="strat-name">Data Revenue Unlock</div>
            <div class="strat-num" id="strat-dru">—</div>
            <div class="strat-sub">accounts</div>
            <div class="strat-bar-wrap"><div class="strat-bar" style="background:linear-gradient(90deg,#153EED,#7B5CF5);width:0" id="sb-dru"></div></div>
          </div>
          <div class="strat-card">
            <div class="strat-icon">🤖</div>
            <div class="strat-name">AI Readiness Accelerator</div>
            <div class="strat-num" id="strat-ai">—</div>
            <div class="strat-sub">accounts</div>
            <div class="strat-bar-wrap"><div class="strat-bar" style="background:linear-gradient(90deg,#7B5CF5,#A080FF);width:0" id="sb-ai"></div></div>
          </div>
          <div class="strat-card">
            <div class="strat-icon">🛒</div>
            <div class="strat-name">Commerce Optimization</div>
            <div class="strat-num" id="strat-co">—</div>
            <div class="strat-sub">accounts</div>
            <div class="strat-bar-wrap"><div class="strat-bar" style="background:linear-gradient(90deg,#00D4A0,#00A880);width:0" id="sb-co"></div></div>
          </div>
          <div class="strat-card">
            <div class="strat-icon">✨</div>
            <div class="strat-name">Experience Transformation</div>
            <div class="strat-num" id="strat-xt">—</div>
            <div class="strat-sub">accounts</div>
            <div class="strat-bar-wrap"><div class="strat-bar" style="background:linear-gradient(90deg,#F5A623,#E08800);width:0" id="sb-xt"></div></div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- ── CHAT ── -->
  <div class="tab-pane active" id="tab-chat">
    <div id="chat-header">
      <h2>GTM Assistant</h2>
      <span id="selected-account-tag">
        <span id="selected-account-name"></span>
        <button id="clear-account" onclick="clearAccount()">✕</button>
      </span>
      <button id="deck-btn" onclick="generateDeck()">⬇ Generate Deck</button>
    </div>
    <div id="messages">
      <div id="welcome">
        <div class="welcome-icon">⚡</div>
        <div class="big">How can I help you win?</div>
        <div class="sub">Ask anything about the pipeline, accounts, or get outreach, briefs and commercial analysis. Select an account from the sidebar to pre-load context.</div>
        <div class="quick-chips">
          <div class="chip" onclick="insertSkill('morning')">Morning briefing</div>
          <div class="chip" onclick="insertSkill('warroom')">War room assessment</div>
          <div class="chip" onclick="insertSkill('forecast')">Q2 forecast</div>
          <div class="chip" onclick="insertSkill('outreach')">Write outreach</div>
          <div class="chip" onclick="insertSkill('signal')">Analyse signal</div>
        </div>
      </div>
    </div>
    <div id="typing-row" style="display:none">
      <div id="typing-indicator"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
    </div>
    <div id="chat-input-area">
      <div id="input-row">
        <textarea id="chat-input" placeholder="Ask anything — or pick a Quick Skill from the sidebar…" rows="1"
          onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
        <button id="send-btn" onclick="sendMessage()">Send ↑</button>
      </div>
      <div id="input-hint">Enter to send &nbsp;·&nbsp; Shift+Enter for new line</div>
    </div>
  </div>

  <!-- ── NOTES ── -->
  <div class="tab-pane" id="tab-notes">
    <div id="notes-pane">
      <h2>📝 Meeting Notes</h2>
      <p class="desc">Paste raw meeting notes below. GTM OS will summarise the meeting, extract next actions, and update account files automatically.</p>
      <div class="form-group">
        <label>Account</label>
        <select id="notes-account"><option value="">— Select account —</option></select>
      </div>
      <div class="form-group">
        <label>Meeting Notes</label>
        <textarea id="notes-text" placeholder="Paste your raw meeting notes here — attendees, discussion points, decisions, agreed actions, follow-ups…"></textarea>
      </div>
      <button class="btn-primary" onclick="processNotes()" id="process-btn">Process Notes</button>
      <div id="notes-result">
        <div class="result-section">
          <div class="result-label">Key Insight</div>
          <div id="result-insight" class="insight-box"></div>
        </div>
        <div class="result-section">
          <div class="result-label">Meeting Summary</div>
          <div id="result-summary" class="summary-text"></div>
        </div>
        <div class="result-section">
          <div class="result-label">Meeting Entry (appended to meetings.md)</div>
          <div id="result-meeting" class="file-preview"></div>
        </div>
        <div class="result-section">
          <div class="result-label">Updated Next Actions (replaces next-actions.md)</div>
          <div id="result-actions" class="file-preview"></div>
        </div>
        <div class="save-actions">
          <button class="btn-primary" onclick="saveNotes()" id="save-btn">Save to Account Files</button>
          <button class="btn-secondary" onclick="cancelNotes()">Cancel</button>
        </div>
      </div>
    </div>
  </div>

  <!-- ── ACCOUNTS ── -->
  <div class="tab-pane" id="tab-accounts">
    <div id="accounts-pane">
      <h2>🏢 Accounts</h2>
      <p class="desc">All ICP-scored accounts in the Nordic GTM OS. Click any account to load it in the assistant.</p>
      <div class="filter-row">
        <button class="filter-btn active" onclick="filterGrid(this,'all')">All</button>
        <button class="filter-btn" onclick="filterGrid(this,'NO')">Norway</button>
        <button class="filter-btn" onclick="filterGrid(this,'DK')">Denmark</button>
        <button class="filter-btn" onclick="filterGrid(this,'SE')">Sweden</button>
        <button class="filter-btn" onclick="filterGrid(this,'scored')">ICP scored</button>
      </div>
      <div class="accounts-grid" id="accounts-grid"></div>
    </div>
  </div>


  <!-- ── PIPELINE RADAR ── -->
  <div class="tab-pane" id="tab-radar">
    <div id="radar-wrap">
      <div class="radar-title">Pipeline Radar</div>
      <div class="radar-sub">Each blip = one account &nbsp;·&nbsp; Distance from centre = deal score &nbsp;·&nbsp; Quadrant = GTM strategy &nbsp;·&nbsp; Colour = urgency &nbsp;·&nbsp; Click any blip to open account</div>
      <div class="radar-layout">
        <div class="radar-svg-container">
          <svg id="radar-svg" viewBox="0 0 600 600" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <radialGradient id="sweepGrad" cx="0%" cy="0%" r="100%">
                <stop offset="0%" stop-color="#153EED" stop-opacity="0.55"/>
                <stop offset="100%" stop-color="#153EED" stop-opacity="0"/>
              </radialGradient>
            </defs>
            <!-- Rings -->
            <circle cx="300" cy="300" r="240" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <circle cx="300" cy="300" r="155" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            <circle cx="300" cy="300" r="78"  fill="none" stroke="rgba(21,62,237,0.15)"   stroke-width="1"/>
            <!-- Axis lines -->
            <line x1="300" y1="55"  x2="300" y2="545" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <line x1="55"  y1="300" x2="545" y2="300" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <!-- Ring labels -->
            <text x="305" y="225" fill="rgba(0,212,160,0.4)" font-size="8" font-family="Inter,sans-serif">HOT</text>
            <text x="305" y="148" fill="rgba(75,110,247,0.4)" font-size="8" font-family="Inter,sans-serif">WARM</text>
            <text x="305" y="68"  fill="rgba(255,255,255,0.2)" font-size="8" font-family="Inter,sans-serif">COLD</text>
            <!-- Quadrant labels -->
            <text x="330" y="78"  fill="rgba(21,62,237,0.55)"   font-size="10" font-family="Inter,sans-serif" font-weight="600">Data Revenue Unlock</text>
            <text x="98"  y="78"  fill="rgba(0,212,160,0.55)"   font-size="10" font-family="Inter,sans-serif" font-weight="600">AI Readiness</text>
            <text x="330" y="528" fill="rgba(123,92,245,0.55)"  font-size="10" font-family="Inter,sans-serif" font-weight="600">Commerce Optimization</text>
            <text x="70"  y="528" fill="rgba(245,166,35,0.55)"  font-size="10" font-family="Inter,sans-serif" font-weight="600">Experience Transform.</text>
            <!-- Rotating sweep -->
            <g id="radar-sweep">
              <path d="M 300 300 L 300 60 A 240 240 0 0 1 470 130 Z" fill="url(#sweepGrad)"/>
            </g>
            <!-- Blips (populated by JS) -->
            <g id="radar-blips"></g>
            <!-- Tooltip (populated by JS) -->
            <g id="radar-tt" display="none">
              <rect id="tt-bg" rx="5" fill="rgba(4,4,15,0.95)" stroke="rgba(21,62,237,0.5)" stroke-width="1"/>
              <text id="tt-name" fill="white" font-size="11.5" font-family="Inter,sans-serif" font-weight="700"/>
              <text id="tt-deal" fill="#8080B0" font-size="10" font-family="Inter,sans-serif"/>
              <text id="tt-val"  fill="#4B6EF7" font-size="10.5" font-family="Inter,sans-serif" font-weight="700"/>
            </g>
          </svg>
        </div>
        <div class="radar-sidebar">
          <div class="radar-panel">
            <div class="radar-panel-title">Legend</div>
            <div class="legend-item"><span class="legend-dot" style="background:#00D4A0;box-shadow:0 0 5px #00D4A0"></span>Deal 8–10 — HOT</div>
            <div class="legend-item"><span class="legend-dot" style="background:#4B6EF7;box-shadow:0 0 5px #4B6EF7"></span>Deal 6–7 — WARM</div>
            <div class="legend-item"><span class="legend-dot" style="background:#F5A623;box-shadow:0 0 5px #F5A623"></span>Deal 4–5 — COOL</div>
            <div class="legend-item"><span class="legend-dot" style="background:#F6574A;box-shadow:0 0 5px #F6574A"></span>Deal &lt;4 — COLD</div>
          </div>
          <div class="radar-panel">
            <div class="radar-panel-title">Hottest Deals</div>
            <div id="radar-hot-list"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── PITCH SIMULATOR ── -->
  <div class="tab-pane" id="tab-simulator">
    <div id="sim-setup">
      <div class="sim-title">🎭 Pitch Simulator</div>
      <div class="sim-sub">Claude becomes the buyer. Practice your pitch before the real meeting — then get scored.</div>
      <div class="sim-controls">
        <div class="sim-select-wrap">
          <label>Target Account</label>
          <select id="sim-account"><option value="">— Select account to practice pitch on —</option></select>
        </div>
        <button class="btn-sim-start" onclick="startPitchSession()">▶ Start Session</button>
      </div>
    </div>
    <div id="sim-persona-bar">
      <div class="sim-persona">
        <div class="sim-persona-icon">🎯</div>
        <div>
          <div class="sim-persona-name" id="sim-persona-name">Buyer</div>
          <div class="sim-persona-sub" id="sim-persona-sub">Playing the decision maker</div>
        </div>
      </div>
      <button class="btn-score" onclick="scorePitch()">📊 Score My Pitch</button>
    </div>
    <div id="sim-messages">
      <div style="text-align:center;padding:60px 20px;color:var(--muted)">
        <div style="font-size:40px;margin-bottom:12px;opacity:0.4">🎭</div>
        <div style="font-size:15px;font-weight:700;color:var(--white)">No session active</div>
        <div style="font-size:13px;margin-top:6px">Select an account above and hit Start Session</div>
      </div>
    </div>
    <div id="sim-input-area" style="display:none">
      <div id="sim-input-row">
        <textarea id="sim-input" placeholder="Type your pitch…" rows="1"
          onkeydown="handleSimKey(event)" oninput="autoResize(this)"></textarea>
        <button id="sim-send-btn" onclick="sendSimMessage()">Send ↑</button>
      </div>
    </div>
  </div>

  <!-- ── PARTNERSHIPS ── -->
  <div class="tab-pane" id="tab-partners">
    <div id="partners-wrap">
      <div class="partners-title">🤝 Partnership Intelligence</div>
      <div class="partners-sub">Valider en potentiel partner mod JAKALA's GTM-strategi, positionering og revenue-potentiale — eller se månedlige markedsanalyser.</div>

      <!-- Validator form -->
      <div class="partner-form-card">
        <div class="partner-form-title">Valider en partner</div>
        <div class="partner-form-row">
          <div class="pf-group grow">
            <label>Virksomhed / Partner</label>
            <input type="text" id="partner-name" placeholder="fx Akeneo, Contentful, Algolia, Sitoo…" />
          </div>
          <div class="pf-group">
            <label>Marked</label>
            <select id="partner-market">
              <option value="Nordic">Nordic (NO/SE/DK)</option>
              <option value="Norway">Norge</option>
              <option value="Sweden">Sverige</option>
              <option value="Denmark">Danmark</option>
            </select>
          </div>
          <div class="pf-group grow">
            <label>Kontekst (valgfri)</label>
            <input type="text" id="partner-context" placeholder="fx 'PIM-vendor', 'mødes med CEO næste uge', 'de arbejder med Elkjøp'…" />
          </div>
          <button class="btn-validate" id="validate-btn" onclick="validatePartner()">Valider ↗</button>
        </div>
      </div>

      <!-- Result card -->
      <div id="partner-result">
        <div id="verdict-banner" class="verdict-banner">
          <div class="verdict-icon" id="verdict-icon">—</div>
          <div>
            <div class="verdict-label" id="verdict-label">—</div>
            <div class="verdict-reason" id="verdict-reason">—</div>
          </div>
          <div class="verdict-score"><span id="verdict-score">—</span><span>/10</span></div>
        </div>

        <div class="dim-grid" id="dim-grid"></div>

        <div class="partner-meta-grid">
          <div class="pmeta-card">
            <div class="pmeta-label">GTM Match</div>
            <div class="pmeta-value" id="pm-gtm"></div>
          </div>
          <div class="pmeta-card">
            <div class="pmeta-label">Buyer Overlap</div>
            <div class="pmeta-value" id="pm-buyers"></div>
          </div>
          <div class="pmeta-card">
            <div class="pmeta-label">Fælles Entry Offer</div>
            <div class="pmeta-value" id="pm-offer"></div>
          </div>
          <div class="pmeta-card">
            <div class="pmeta-label">Target Accounts</div>
            <div class="pmeta-value" id="pm-accounts"></div>
          </div>
          <div class="pmeta-card">
            <div class="pmeta-label">Første skridt</div>
            <div class="pmeta-value" id="pm-step"></div>
          </div>
          <div class="pmeta-card">
            <div class="pmeta-label">Risici</div>
            <div class="pmeta-value" id="pm-risks"></div>
          </div>
        </div>
      </div>

      <!-- History -->
      <div class="partner-history-title">Tidligere valideringer</div>
      <div id="partner-history"></div>
    </div>
  </div>

  <!-- ── SIGNAL FEED ── -->
  <div class="tab-pane" id="tab-signals">
    <div id="signals-wrap">
      <div class="signals-title">⚡ Signal Feed</div>
      <div class="signals-sub">Live commercial signals from the Nordic market. Click "Write Outreach" to generate a message and load the account.</div>
      <div id="signals-content"></div>
    </div>
  </div>

</div>

<div id="toast"></div>

<script>
// ── State ─────────────────────────────────────────────────────────────────────
let messages = [];
let selectedAccount = null;
let allAccounts = [];
let processingResult = null;
let gridFilter = 'all';

// ── Boot ──────────────────────────────────────────────────────────────────────
async function boot() {
  updateClock();
  setInterval(updateClock, 1000);
  showTab('chat');
  try {
    const res = await fetch('/api/accounts');
    allAccounts = await res.json();
    renderAccountList(allAccounts);
    renderAccountsGrid(allAccounts);
    populateNotesSelect(allAccounts);
    populateSimSelect();
    renderDashboard(allAccounts);
    setTimeout(animateDashboard, 400);
    renderSignalFeed();
  } catch(e) {
    console.error('Boot error:', e);
  }
}
boot();

// ── Clock ─────────────────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const t = document.getElementById('dash-time');
  const d = document.getElementById('dash-date');
  if (t) t.textContent = now.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' });
  if (d) d.textContent = now.toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'long', year:'numeric' });
}

// ── Tab switching ─────────────────────────────────────────────────────────────
function showTab(name) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  const nb = document.getElementById('nav-' + name);
  if (nb) nb.classList.add('active');
  if (name === 'radar')    setTimeout(renderRadar, 50);
  if (name === 'partners') setTimeout(loadPartnerHistory, 50);
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
const VALUE_MAP = {
  'hm':           { val:'€900K', strat:'Data Revenue Unlock', icp:9, deal:9 },
  'matas':        { val:'€700K', strat:'AI Readiness',        icp:9, deal:9 },
  'elkjop':       { val:'€700K', strat:'Commerce Opt.',       icp:8, deal:8 },
  'varner-group': { val:'€450K', strat:'Data Revenue Unlock', icp:9, deal:9 },
  'trumf':        { val:'€450K', strat:'Data Revenue Unlock', icp:9, deal:9 },
  'clas-ohlson':  { val:'€350K', strat:'Commerce Opt.',       icp:7, deal:7 },
  'boozt':        { val:'€300K', strat:'AI Readiness',        icp:8, deal:8 },
  'jysk':         { val:'€280K', strat:'Commerce Opt.',       icp:7, deal:7 },
};

function renderDashboard(accounts) {
  // Top 6 by deal score
  const top = accounts
    .filter(a => a.deal !== '\u2014')
    .sort((a,b) => parseInt(b.deal) - parseInt(a.deal))
    .slice(0, 6);

  const circ = 87.96;
  const container = document.getElementById('top-opps');
  if (container) {
    container.innerHTML = top.map((a, i) => {
      const deal = parseInt(a.deal) || 0;
      const icp  = parseInt(a.icp)  || 0;
      const vm   = VALUE_MAP[a.slug] || { val:'\u2014', strat:'GTM' };
      const dash = ((deal / 10) * circ).toFixed(1);
      const col  = deal >= 8 ? '#00D4A0' : deal >= 6 ? '#4B6EF7' : '#F5A623';
      return '<div class="opp" data-slug="' + a.slug + '" data-name="' + a.name + '" onclick="selectAccount(this.dataset.slug,this.dataset.name)">' +
        '<div class="opp-num">#' + (i+1) + '</div>' +
        '<div class="opp-ring">' +
          '<svg width="38" height="38" viewBox="0 0 38 38">' +
            '<circle cx="19" cy="19" r="15" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="2.5"/>' +
            '<circle cx="19" cy="19" r="15" fill="none" stroke="' + col + '" stroke-width="2.5" ' +
              'stroke-dasharray="' + dash + ' ' + circ + '" stroke-linecap="round" ' +
              'style="transform:rotate(-90deg);transform-origin:50% 50%"/>' +
          '</svg>' +
          '<div class="opp-ring-val">' + deal + '</div>' +
        '</div>' +
        '<div class="opp-body">' +
          '<div class="opp-name">' + a.name + '</div>' +
          '<div class="opp-meta">' + vm.strat + ' &nbsp;·&nbsp; ICP ' + icp + '/10 &nbsp;·&nbsp; ' + (a.country !== '\u2014' ? a.country : '') + '</div>' +
        '</div>' +
        '<div class="opp-right">' +
          '<div class="opp-val">' + vm.val + '</div>' +
          '<div class="opp-val-sub">unweighted</div>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  // Active count
  const active = accounts.filter(a => a.deal !== '\u2014').length;
  const el = document.getElementById('kpi-accounts');
  if (el) el.setAttribute('data-target', active);

  // Strategy split (approximate categorization by known accounts)
  const dru = ['hm','varner-group','trumf','xxl-fraser-group','norgesgruppen','salling-group','coop-norge','naf','trumf','oda','europris','nille','vinmonopolet'];
  const ai  = ['matas','dustin-group','bestseller','komplett','dnb','saxo-bank','lyko','apotea','lindex','imerco','pandora','la-redoute','fnac-darty','gymgrossisten'];
  const co  = ['elkjop','clas-ohlson','jysk','boozt','xxl-sport','bohus','skeidar','halfords','currys','ao-world','ocado','dunelm','webhallen','sport-outlet'];
  const xt  = ['helly-hansen','loccitane','plantasjen','plantagen-sverige','norrona','kapphahl','polarn-o-pyret','gant-norway','follestad'];
  const allSlugs = accounts.map(a => a.slug);
  const druN = allSlugs.filter(s => dru.includes(s)).length;
  const aiN  = allSlugs.filter(s => ai.includes(s)).length;
  const coN  = allSlugs.filter(s => co.includes(s)).length;
  const xtN  = allSlugs.filter(s => xt.includes(s)).length;
  const maxN = Math.max(druN, aiN, coN, xtN, 1);
  ['dru','ai','co','xt'].forEach((k,i) => {
    const n = [druN,aiN,coN,xtN][i];
    const el = document.getElementById('strat-' + k);
    if (el) el.setAttribute('data-target', n);
    const bar = document.getElementById('sb-' + k);
    if (bar) bar.setAttribute('data-w', Math.round((n/maxN)*100) + '%');
  });
}

function animateDashboard() {
  countUp('kpi-pipeline', 6.8,  1.4, 1);
  countUp('kpi-buyers',   18,   1.1, 0);
  countUp('kpi-forecast', 420,  1.3, 0);

  // Named-target count-up for dynamic fields
  ['kpi-accounts','strat-dru','strat-ai','strat-co','strat-xt'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      const t = parseInt(el.getAttribute('data-target') || el.textContent) || 0;
      countUp(id, t, 1.2, 0);
    }
  });

  // Animate bars
  document.querySelectorAll('[data-w]').forEach(el => {
    setTimeout(() => { el.style.width = el.getAttribute('data-w'); }, 100);
  });
}

function countUp(id, target, duration, decimals) {
  const el = document.getElementById(id);
  if (!el) return;
  const start = performance.now();
  const ms = duration * 1000;
  function frame(now) {
    const p = Math.min((now - start) / ms, 1);
    const e = 1 - Math.pow(1 - p, 3);
    el.textContent = decimals > 0 ? (e * target).toFixed(decimals) : Math.round(e * target);
    if (p < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

// ── Account sidebar ───────────────────────────────────────────────────────────
function renderAccountList(accounts) {
  const list = document.getElementById('account-list');
  list.innerHTML = accounts.map(a => {
    const icp  = a.icp  !== '\u2014' ? a.icp  : null;
    const high = icp && parseInt(icp) >= 8;
    const sel  = selectedAccount === a.slug;
    return '<div class="account-item' + (sel ? ' selected' : '') + '" data-slug="' + a.slug + '" data-name="' + a.name + '" onclick="selectAccount(this.dataset.slug,this.dataset.name)">' +
      '<span class="aname">' + a.name + '</span>' +
      '<span class="acc-badges">' +
        (icp ? '<span class="spill' + (high ? ' g' : '') + '">ICP ' + icp + '</span>' : '') +
        (a.country !== '\u2014' ? '<span class="spill c">' + a.country + '</span>' : '') +
      '</span>' +
    '</div>';
  }).join('');
}

function filterAccounts() {
  const q = document.getElementById('account-search').value.toLowerCase();
  const filtered = q ? allAccounts.filter(a => a.name.toLowerCase().includes(q) || a.slug.includes(q)) : allAccounts;
  renderAccountList(filtered);
}

function selectAccount(slug, name) {
  selectedAccount = slug;
  renderAccountList(allAccounts);
  document.getElementById('selected-account-tag').style.display = 'flex';
  document.getElementById('selected-account-name').textContent = name;
  document.getElementById('deck-btn').style.display = 'block';
  showTab('chat');
  document.getElementById('welcome').style.display = 'none';
  addSystemNote('Account loaded: ' + name);
}

function clearAccount() {
  selectedAccount = null;
  renderAccountList(allAccounts);
  document.getElementById('selected-account-tag').style.display = 'none';
  document.getElementById('deck-btn').style.display = 'none';
}

async function generateDeck() {
  if (!selectedAccount) return;
  const btn = document.getElementById('deck-btn');
  btn.classList.add('loading');
  btn.textContent = 'Building deck…';
  try {
    const res = await fetch('/api/generate-deck/' + selectedAccount, { method: 'POST' });
    if (!res.ok) { showToast('Deck generation failed', true); return; }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = 'JAKALA-' + selectedAccount + '-discovery.pptx';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Deck downloaded \u2713');
  } catch(e) {
    showToast('Download failed', true);
  } finally {
    btn.classList.remove('loading');
    btn.textContent = '\u2b07 Generate Deck';
  }
}

// ── Accounts grid ─────────────────────────────────────────────────────────────
function renderAccountsGrid(accounts) {
  const grid = document.getElementById('accounts-grid');
  const list = gridFilter === 'all'    ? accounts :
               gridFilter === 'scored' ? accounts.filter(a => a.deal !== '\u2014') :
               accounts.filter(a => a.country === gridFilter);
  grid.innerHTML = list.map(a => {
    const icp  = a.icp  !== '\u2014' ? parseInt(a.icp)  : 0;
    const deal = a.deal !== '\u2014' ? parseInt(a.deal) : 0;
    const high = icp >= 8 || deal >= 8;
    return '<div class="account-card" data-slug="' + a.slug + '" data-name="' + a.name + '" onclick="selectAccount(this.dataset.slug,this.dataset.name)">' +
      '<div class="card-top">' +
        '<div class="card-name">' + a.name + '</div>' +
        '<div class="card-badges">' +
          (a.country !== '\u2014' ? '<span class="badge c">' + a.country + '</span>' : '') +
          (icp  ? '<span class="badge' + (high ? ' g' : '') + '">ICP ' + icp + '</span>' : '') +
          (deal ? '<span class="badge' + (high ? ' g' : '') + '">Deal ' + deal + '</span>' : '') +
        '</div>' +
      '</div>' +
      (icp || deal ? '<div class="score-bars">' +
        (icp  ? '<div class="sb-item"><div class="sb-label">ICP</div><div class="sb-track"><div class="sb-fill icp" style="width:' + (icp*10) + '%"></div></div></div>' : '') +
        (deal ? '<div class="sb-item"><div class="sb-label">Deal</div><div class="sb-track"><div class="sb-fill deal" style="width:' + (deal*10) + '%"></div></div></div>' : '') +
      '</div>' : '') +
    '</div>';
  }).join('');
}

function filterGrid(btn, filter) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  gridFilter = filter;
  renderAccountsGrid(allAccounts);
}

function populateNotesSelect(accounts) {
  const sel = document.getElementById('notes-account');
  accounts.forEach(a => {
    const opt = document.createElement('option');
    opt.value = a.slug;
    opt.textContent = a.name;
    sel.appendChild(opt);
  });
}

// ── Chat ──────────────────────────────────────────────────────────────────────
function addSystemNote(text) {
  const msgs = document.getElementById('messages');
  const el = document.createElement('div');
  el.style.cssText = 'text-align:center;font-size:10.5px;color:var(--muted);padding:2px 0;';
  el.textContent = '\u00b7 ' + text + ' \u00b7';
  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;
}

function appendMessage(role, content) {
  const msgs = document.getElementById('messages');
  const el = document.createElement('div');
  el.className = 'msg ' + role;
  el.innerHTML = '<div class="msg-role">' + (role === 'user' ? 'You' : 'GTM OS') + '</div>' +
                 '<div class="msg-bubble">' + renderMarkdown(content) + '</div>';
  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;
  return el.querySelector('.msg-bubble');
}

function renderMarkdown(text) {
  return text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/```[\s\S]*?```/g, m => '<pre><code>' + m.slice(3,-3).replace(/^[a-z]+\\n/,'') + '</code></pre>')
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/^### (.+)$/gm,'<h3>$1</h3>')
    .replace(/^## (.+)$/gm,'<h2>$1</h2>')
    .replace(/^# (.+)$/gm,'<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,'<em>$1</em>')
    .replace(/^> (.+)$/gm,'<blockquote>$1</blockquote>')
    .replace(/^---$/gm,'<hr>')
    .replace(/^\| (.+) \|$/gm, m => {
      const cells = m.slice(2,-2).split(' | ');
      return '<tr>' + cells.map(c => '<td>' + c.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>') + '</td>').join('') + '</tr>';
    })
    .replace(/(<tr>.*<\/tr>\\n?)+/gs, m => '<table>' + m + '</table>')
    .replace(/<table>(<tr><td>[-:| ]+<\/td><\/tr>)<\/table>/g,'')
    .replace(/^- (.+)$/gm,'<li>$1</li>')
    .replace(/(<li>.*<\/li>\\n?)+/gs, m => '<ul>' + m + '</ul>')
    .replace(/^\d+\. (.+)$/gm,'<li>$1</li>')
    .replace(/\\n/g,'<br>');
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  document.getElementById('welcome').style.display = 'none';
  input.value = '';
  input.style.height = 'auto';
  document.getElementById('send-btn').disabled = true;

  messages.push({ role: 'user', content: text });
  appendMessage('user', text);

  document.getElementById('typing-row').style.display = 'block';
  document.getElementById('typing-indicator').classList.add('visible');

  const bubble = appendMessage('assistant', '');
  let full = '';

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, account: selectedAccount })
    });

    document.getElementById('typing-row').style.display = 'none';
    document.getElementById('typing-indicator').classList.remove('visible');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      for (const line of chunk.split('\\n')) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          try {
            const { text: t } = JSON.parse(line.slice(6));
            full += t;
            bubble.innerHTML = renderMarkdown(full);
            document.getElementById('messages').scrollTop = 99999;
          } catch(e) {}
        }
      }
    }
    messages.push({ role: 'assistant', content: full });
  } catch(err) {
    document.getElementById('typing-row').style.display = 'none';
    bubble.innerHTML = '<em style="color:var(--red)">Connection error — check server and API key.</em>';
  }

  document.getElementById('send-btn').disabled = false;
  input.focus();
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

// ── Quick skills ──────────────────────────────────────────────────────────────
function insertSkill(key) {
  showTab('chat');
  const acc = selectedAccount ? selectedAccount.replace(/-/g,' ') : null;
  const prompts = {
    morning:  'Give me the morning CCO briefing \u2014 top signals, pipeline health, and my 3 priorities for today.',
    warroom:  'Run the commercial war room \u2014 full situation assessment. Nordic pipeline only (DK/NO/SE).',
    forecast: 'Run the Q2 2026 commercial forecast \u2014 probability-weighted, all active Nordic accounts.',
    outreach: acc ? 'Write a LinkedIn outreach message for ' + acc + '. Language: English.' : 'Write a LinkedIn outreach message. Select an account from the sidebar first, or tell me the company name.',
    pitch:    acc ? 'Run the pitch partner brief for ' + acc + '. Who is the buyer and what is the best service match?' : 'Run the pitch partner brief. Select an account from the sidebar first.',
    brief:    acc ? 'Give me the pre-meeting brief for ' + acc + '. Meeting type: discovery.' : 'Give me the pre-meeting brief. Select an account from the sidebar first.',
    revenue:  acc ? 'Run the revenue simulation for ' + acc + '. Show all three levers and three scenarios.' : 'Run the revenue simulation. Select an account from the sidebar first.',
    signal:   'I have a new market signal to analyse. Here it is:',
  };
  const input = document.getElementById('chat-input');
  input.value = prompts[key] || '';
  autoResize(input);
  input.focus();
  document.getElementById('welcome').style.display = 'none';
}

// ── Meeting notes ─────────────────────────────────────────────────────────────
async function processNotes() {
  const account = document.getElementById('notes-account').value;
  const notes   = document.getElementById('notes-text').value.trim();
  if (!account) { showToast('Select an account first', true); return; }
  if (!notes)   { showToast('Paste meeting notes first', true); return; }

  const btn = document.getElementById('process-btn');
  btn.disabled = true; btn.textContent = 'Processing\u2026';

  try {
    const res  = await fetch('/api/process-notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account, notes })
    });
    const data = await res.json();
    if (data.error) { showToast('Error: ' + data.error, true); return; }

    processingResult = { account, ...data };
    document.getElementById('result-insight').textContent  = data.key_insight    || '\u2014';
    document.getElementById('result-summary').textContent  = data.summary        || '\u2014';
    document.getElementById('result-meeting').textContent  = data.meeting_entry  || '\u2014';
    document.getElementById('result-actions').textContent  = data.next_actions_updated || '\u2014';
    document.getElementById('notes-result').style.display = 'block';
    document.getElementById('notes-result').scrollIntoView({ behavior: 'smooth' });
  } catch(err) {
    showToast('Request failed \u2014 check connection', true);
  } finally {
    btn.disabled = false; btn.textContent = 'Process Notes';
  }
}

async function saveNotes() {
  if (!processingResult) return;
  const btn = document.getElementById('save-btn');
  btn.disabled = true; btn.textContent = 'Saving\u2026';

  try {
    const res  = await fetch('/api/save-notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account: processingResult.account,
        meeting_entry: processingResult.meeting_entry,
        next_actions_updated: processingResult.next_actions_updated
      })
    });
    const data = await res.json();
    if (data.ok) {
      showToast('Saved to account files \u2713');
      document.getElementById('notes-result').style.display = 'none';
      document.getElementById('notes-text').value = '';
    }
  } catch { showToast('Save failed', true); }
  finally { btn.disabled = false; btn.textContent = 'Save to Account Files'; }
}

function cancelNotes() {
  document.getElementById('notes-result').style.display = 'none';
  processingResult = null;
}

// ── Toast ──────────────────────────────────────────────────────────────────────
function showToast(msg, error = false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'show' + (error ? ' error' : '');
  setTimeout(() => t.className = '', 3000);
}

// ══════════════════════════════════════════════════════════════════════════════
// PARTNERSHIP VALIDATOR
// ══════════════════════════════════════════════════════════════════════════════
async function validatePartner() {
  const name    = document.getElementById('partner-name').value.trim();
  const market  = document.getElementById('partner-market').value;
  const context = document.getElementById('partner-context').value.trim();
  if (!name) { showToast('Angiv partnerens navn', true); return; }

  const btn = document.getElementById('validate-btn');
  btn.disabled = true; btn.textContent = 'Analyserer\u2026';
  document.getElementById('partner-result').style.display = 'none';

  try {
    const res  = await fetch('/api/validate-partner', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ partner: name, market, context })
    });
    const data = await res.json();
    if (data.error) { showToast('Fejl: ' + data.error, true); return; }
    renderPartnerResult(data);
    loadPartnerHistory();
  } catch(e) {
    showToast('Request fejlede', true);
  } finally {
    btn.disabled = false; btn.textContent = 'Valider \u2197';
  }
}

function renderPartnerResult(d) {
  const verdict = (d.verdict || '').toLowerCase().replace(/\s+/g, '-').replace('not-recommended','not-rec');
  const icons   = { 'strong-fit': '\u2705', 'potential-fit': '\uD83D\uDCA1', 'weak-fit': '\u26A0\uFE0F', 'not-rec': '\u274C' };
  const colors  = { 'strong-fit': 'strong', 'potential-fit': 'potential', 'weak-fit': 'weak', 'not-rec': 'not-rec' };
  const cls     = colors[verdict] || 'potential';

  // Banner
  const banner = document.getElementById('verdict-banner');
  banner.className = 'verdict-banner ' + cls;
  document.getElementById('verdict-icon').textContent   = icons[verdict] || '\uD83D\uDCA1';
  document.getElementById('verdict-label').textContent  = d.verdict || '\u2014';
  document.getElementById('verdict-label').className    = 'verdict-label ' + cls;
  document.getElementById('verdict-reason').textContent = d.verdict_reason || '\u2014';
  document.getElementById('verdict-score').textContent  = d.overall_score || '\u2014';

  // Dimension grid
  const dimColors = { 10:'#00D4A0', 9:'#00D4A0', 8:'#4B6EF7', 7:'#4B6EF7', 6:'#F5A623', 5:'#F5A623', 4:'#F6574A', 3:'#F6574A', 2:'#F6574A', 1:'#F6574A' };
  const dimGrid = document.getElementById('dim-grid');
  dimGrid.innerHTML = (d.dimensions || []).map(dim => {
    const pct = Math.round((dim.score / dim.max) * 100);
    const col = dimColors[dim.score] || '#8080B0';
    return '<div class="dim-card">' +
      '<div class="dim-name">' + dim.name + '</div>' +
      '<div class="dim-score-row">' +
        '<div class="dim-score-num">' + dim.score + '</div>' +
        '<div class="dim-score-max">/' + dim.max + '</div>' +
        '<div class="dim-bar-track"><div class="dim-bar-fill" style="width:0;background:' + col + '" data-w="' + pct + '%"></div></div>' +
      '</div>' +
      '<div class="dim-finding">' + (dim.finding || '') + '</div>' +
    '</div>';
  }).join('');

  // Animate bars
  setTimeout(() => {
    dimGrid.querySelectorAll('.dim-bar-fill').forEach(el => {
      el.style.width = el.getAttribute('data-w');
    });
  }, 80);

  // Meta fields
  document.getElementById('pm-gtm').innerHTML      = (d.gtm_match    || []).map(t => '<span class="pmeta-tag">' + t + '</span>').join('');
  document.getElementById('pm-buyers').innerHTML   = (d.buyer_overlap || []).map(t => '<span class="pmeta-tag">' + t + '</span>').join('');
  document.getElementById('pm-offer').textContent  = d.joint_offer   || '\u2014';
  document.getElementById('pm-accounts').innerHTML = (d.target_accounts || []).map(t => '<span class="pmeta-tag">' + t + '</span>').join('');
  document.getElementById('pm-step').textContent   = d.first_step    || '\u2014';
  document.getElementById('pm-risks').innerHTML    = (d.risks || []).map(r => '\u2022 ' + r).join('<br>');

  document.getElementById('partner-result').style.display = 'block';
  document.getElementById('partner-result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function loadPartnerHistory() {
  const container = document.getElementById('partner-history');
  if (!container) return;
  try {
    const res  = await fetch('/api/partner-history');
    const data = await res.json();
    if (!data.length) {
      container.innerHTML = '<div style="color:var(--muted);font-size:12px">Ingen tidligere valideringer endnu.</div>';
      return;
    }
    const vmap = { 'STRONG FIT':'strong', 'POTENTIAL FIT':'potential', 'WEAK FIT':'weak', 'NOT RECOMMENDED':'not-rec' };
    container.innerHTML = data.map(p => {
      const cls = vmap[p.verdict] || 'potential';
      return '<div class="ph-row">' +
        '<div class="ph-name">' + p.name + '</div>' +
        '<div class="ph-market">' + p.market + '</div>' +
        '<div class="ph-verdict ' + cls + '">' + p.verdict + '</div>' +
        '<div class="ph-score">' + p.score + '/10</div>' +
      '</div>';
    }).join('');
  } catch(e) {}
}

// ══════════════════════════════════════════════════════════════════════════════
// BOARD REPORT
// ══════════════════════════════════════════════════════════════════════════════
async function generateBoardReport() {
  const btn = document.getElementById('board-report-btn');
  btn.disabled = true; btn.textContent = 'Building report\u2026';
  try {
    const res = await fetch('/api/board-report', { method: 'POST' });
    if (!res.ok) { showToast('Board report failed', true); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'JAKALA-Board-Report-' + new Date().toISOString().slice(0,10) + '.pptx';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Board Report downloaded \u2713');
  } catch(e) {
    showToast('Download failed', true);
  } finally {
    btn.disabled = false; btn.textContent = '\uD83D\uDCCA Board Report';
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// PIPELINE RADAR
// ══════════════════════════════════════════════════════════════════════════════
const STRAT_MAP = {
  'hm':'dru','varner-group':'dru','trumf':'dru','norgesgruppen':'dru','oda':'dru',
  'europris':'dru','nille':'dru','vinmonopolet':'dru','coop-norge':'dru','naf':'dru',
  'matas':'ai','dustin-group':'ai','bestseller':'ai','dnb':'ai','saxo-bank':'ai',
  'lyko':'ai','apotea':'ai','lindex':'ai','komplett':'ai','imerco':'ai','pandora':'ai',
  'elkjop':'co','clas-ohlson':'co','jysk':'co','boozt':'co','xxl-sport':'co',
  'bohus':'co','skeidar':'co','halfords':'co','sport-outlet':'co','jernia':'co',
  'webhallen':'co','xxl-fraser-group':'co','salling-group':'co',
  'helly-hansen':'xt','loccitane':'xt','plantasjen':'xt','norrona':'xt',
  'kapphahl':'xt','gant-norway':'xt','follestad':'xt','polarn-o-pyret':'xt',
};
const RADAR_VALS = {
  'hm':'€900K','matas':'€700K','elkjop':'€700K','varner-group':'€450K',
  'trumf':'€450K','clas-ohlson':'€350K','boozt':'€300K','jysk':'€280K',
  'helly-hansen':'€250K','skeidar':'€220K','dnb':'€200K','komplett':'€200K',
  'vinmonopolet':'€180K','norgesgruppen':'€400K',
};

function slugToQuadrant(slug) {
  if (STRAT_MAP[slug]) return STRAT_MAP[slug];
  const dru = ['trumf','norges','oda','europris','nille','vino','coop','naf','xxl-fraser'];
  const ai  = ['matas','dustin','best','dnb','saxo','lyko','apotea','lindex','komplett'];
  const co  = ['elkjop','clas','jysk','boozt','sport','bohus','skeidar','halfords','jernia'];
  const xt  = ['helly','locc','plantasjen','norrona','kapphahl','gant','follestad'];
  if (dru.some(k => slug.includes(k))) return 'dru';
  if (ai.some(k  => slug.includes(k))) return 'ai';
  if (co.some(k  => slug.includes(k))) return 'co';
  if (xt.some(k  => slug.includes(k))) return 'xt';
  let h = 0; for (const c of slug) h = ((h * 31) + c.charCodeAt(0)) >>> 0;
  return ['dru','ai','co','xt'][h % 4];
}

function radarPos(slug, deal) {
  const baseAngles = { dru:45, ai:315, co:135, xt:225 };
  let hash = 0; for (const c of slug) hash = ((hash * 31) + c.charCodeAt(0)) >>> 0;
  const q = slugToQuadrant(slug);
  const spread = ((hash % 50000) / 50000 - 0.5) * 46;
  const deg = (baseAngles[q] || 45) + spread;
  const rad = (deg - 90) * Math.PI / 180;
  const ds = parseInt(deal) || 0;
  const r = ds >= 9 ? 32 + (hash % 40) :
            ds >= 7 ? 82 + (hash % 58) :
            ds >= 5 ? 148 + (hash % 56) :
                      198 + (hash % 36);
  return { x: 300 + r * Math.cos(rad), y: 300 + r * Math.sin(rad) };
}

function renderRadar() {
  const blipsG = document.getElementById('radar-blips');
  const hotList = document.getElementById('radar-hot-list');
  if (!blipsG || !allAccounts.length) return;

  const scored = allAccounts
    .filter(a => a.deal !== '\u2014' && parseInt(a.deal) >= 5)
    .sort((a,b) => parseInt(b.deal) - parseInt(a.deal));

  if (hotList) {
    hotList.innerHTML = scored.slice(0, 9).map(a => {
      const ds = parseInt(a.deal);
      const col = ds >= 8 ? '#00D4A0' : ds >= 6 ? '#4B6EF7' : '#F5A623';
      return '<div class="rhi" data-slug="' + a.slug + '" data-name="' + a.name + '" onclick="selectAccount(this.dataset.slug,this.dataset.name)">' +
        '<div class="rhi-dot" style="background:' + col + ';box-shadow:0 0 6px ' + col + '"></div>' +
        '<div class="rhi-name">' + a.name + '</div>' +
        '<div class="rhi-score">' + ds + '/10</div>' +
      '</div>';
    }).join('');
  }

  let html = '';
  for (const a of scored) {
    const ds = parseInt(a.deal) || 0;
    const pos = radarPos(a.slug, ds);
    const col = ds >= 8 ? '#00D4A0' : ds >= 6 ? '#4B6EF7' : ds >= 5 ? '#F5A623' : '#F6574A';
    const r   = Math.max(5, Math.min(13, 4 + ds * 1.0));
    const val = RADAR_VALS[a.slug] || '';
    const safeSlug = a.slug.replace(/'/g, "\\'");
    const safeName = a.name.replace(/'/g, "\\'");
    html += '<g class="r-blip" style="cursor:pointer" data-slug="' + a.slug + '" data-name="' + a.name + '" data-ds="' + ds + '" data-val="' + val + '"' +
      ' onclick="selectAccount(\'' + safeSlug + '\',\'' + safeName + '\')">' +
      '<circle cx="' + pos.x.toFixed(1) + '" cy="' + pos.y.toFixed(1) + '" r="' + (r+4) + '" fill="' + col + '" opacity="0.1"/>' +
      '<circle cx="' + pos.x.toFixed(1) + '" cy="' + pos.y.toFixed(1) + '" r="' + r + '" fill="' + col + '" opacity="0.88">' +
        '<animate attributeName="r" values="' + r + ';' + (r+1.5) + ';' + r + '" dur="2.2s" repeatCount="indefinite"/>' +
      '</circle>' +
    '</g>';
  }
  blipsG.innerHTML = html;

  blipsG.querySelectorAll('.r-blip').forEach(g => {
    g.addEventListener('mouseenter', function() {
      const tt = document.getElementById('radar-tt');
      const ttBg = document.getElementById('tt-bg');
      const ttName = document.getElementById('tt-name');
      const ttDeal = document.getElementById('tt-deal');
      const ttVal  = document.getElementById('tt-val');
      if (!tt) return;
      const cx = parseFloat(g.querySelector('circle').getAttribute('cx'));
      const cy = parseFloat(g.querySelector('circle').getAttribute('cy'));
      ttName.textContent = this.dataset.name;
      ttDeal.textContent = 'Deal ' + this.dataset.ds + '/10';
      ttVal.textContent  = this.dataset.val || '';
      const w = Math.max(ttName.textContent.length, 12) * 7.5 + 20;
      const tx = cx + 14, ty = cy - 50;
      ttBg.setAttribute('x', tx - 6); ttBg.setAttribute('y', ty - 14);
      ttBg.setAttribute('width', w); ttBg.setAttribute('height', 56);
      ttName.setAttribute('x', tx); ttName.setAttribute('y', ty);
      ttDeal.setAttribute('x', tx); ttDeal.setAttribute('y', ty + 17);
      ttVal.setAttribute('x',  tx); ttVal.setAttribute('y',  ty + 33);
      tt.setAttribute('display', 'block');
    });
    g.addEventListener('mouseleave', () => {
      const tt = document.getElementById('radar-tt');
      if (tt) tt.setAttribute('display', 'none');
    });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// PITCH SIMULATOR
// ══════════════════════════════════════════════════════════════════════════════
let simMessages = [];
let simAccount  = null;

function populateSimSelect() {
  const sel = document.getElementById('sim-account');
  if (!sel || sel.options.length > 1) return;
  allAccounts.forEach(a => {
    const opt = document.createElement('option');
    opt.value = a.slug; opt.textContent = a.name;
    sel.appendChild(opt);
  });
}

async function startPitchSession() {
  const slug = document.getElementById('sim-account').value;
  if (!slug) { showToast('Select an account first', true); return; }

  simAccount  = slug;
  simMessages = [];

  const name = allAccounts.find(a => a.slug === slug)?.name || slug.replace(/-/g,' ').replace(/\\b\\w/g, c => c.toUpperCase());
  const msgs = document.getElementById('sim-messages');
  msgs.innerHTML = '';
  addSimNote('Session started \u2014 ' + name + ' \u00b7 Start with your opening pitch');
  document.getElementById('sim-persona-name').textContent = name + ' Buyer';
  document.getElementById('sim-persona-sub').textContent  = 'Claude is playing the decision maker';
  document.getElementById('sim-persona-bar').classList.add('active');
  document.getElementById('sim-input-area').style.display = 'block';
  document.getElementById('sim-input').focus();

  // Trigger first buyer message
  simMessages.push({ role: 'user', content: 'Hello, I appreciate you taking the time to meet.' });
  const bubble = appendSimMsg('opponent', '');
  let full = '';
  try {
    const res = await fetch('/api/pitch', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: simMessages, account: simAccount })
    });
    const reader = res.body.getReader(); const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      for (const line of decoder.decode(value).split('\\n')) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          try { const { text: t } = JSON.parse(line.slice(6)); full += t; bubble.innerHTML = renderMarkdown(full); msgs.scrollTop = 99999; } catch(e) {}
        }
      }
    }
    simMessages.push({ role: 'assistant', content: full });
    // Remove the fake opener from history, keep only the buyer reply
    simMessages = [{ role: 'assistant', content: full }];
  } catch(e) { bubble.innerHTML = '<em style="color:var(--red)">Connection error.</em>'; }
}

function addSimNote(text) {
  const msgs = document.getElementById('sim-messages');
  const el = document.createElement('div');
  el.className = 'sim-note';
  el.textContent = '\u00b7 ' + text + ' \u00b7';
  msgs.appendChild(el); msgs.scrollTop = msgs.scrollHeight;
}

function appendSimMsg(role, content) {
  const msgs = document.getElementById('sim-messages');
  const el = document.createElement('div');
  el.className = 'msg ' + (role === 'opponent' ? 'assistant sim-opp' : 'user');
  const label = role === 'opponent'
    ? (simAccount || '').replace(/-/g,' ').replace(/\\b\\w/g, c => c.toUpperCase()) + ' Buyer'
    : 'You';
  const roleStyle = role === 'opponent' ? ' style="color:var(--red)"' : '';
  el.innerHTML = '<div class="msg-role"' + roleStyle + '>' + label + '</div>' +
                 '<div class="msg-bubble">' + renderMarkdown(content) + '</div>';
  msgs.appendChild(el); msgs.scrollTop = msgs.scrollHeight;
  return el.querySelector('.msg-bubble');
}

async function sendSimMessage() {
  const input = document.getElementById('sim-input');
  const text = input.value.trim();
  if (!text || !simAccount) return;

  input.value = ''; input.style.height = 'auto';
  document.getElementById('sim-send-btn').disabled = true;

  simMessages.push({ role: 'user', content: text });
  appendSimMsg('user', text);
  const bubble = appendSimMsg('opponent', '');
  let full = '';

  try {
    const res = await fetch('/api/pitch', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: simMessages, account: simAccount })
    });
    const reader = res.body.getReader(); const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      const msgs = document.getElementById('sim-messages');
      for (const line of decoder.decode(value).split('\\n')) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          try { const { text: t } = JSON.parse(line.slice(6)); full += t; bubble.innerHTML = renderMarkdown(full); msgs.scrollTop = 99999; } catch(e) {}
        }
      }
    }
    simMessages.push({ role: 'assistant', content: full });
  } catch(e) { bubble.innerHTML = '<em style="color:var(--red)">Error.</em>'; }
  document.getElementById('sim-send-btn').disabled = false;
  document.getElementById('sim-input').focus();
}

async function scorePitch() {
  if (!simMessages.length || !simAccount) { showToast('Start a pitch session first', true); return; }
  addSimNote('Scoring your pitch\u2026');
  const scorePrompt = [
    ...simMessages,
    { role: 'user', content: 'STOP the roleplay. You are now a senior B2B sales coach. Score this pitch conversation 1\u201310 across: Opening hook, Value proposition clarity, Objection handling, Buyer fit, Call to action. Give an Overall score. Then 1 key strength and 1 specific improvement to make it 20% more effective.' }
  ];
  const bubble = appendSimMsg('opponent', '');
  let full = '';
  try {
    const res = await fetch('/api/pitch', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: scorePrompt, account: simAccount, scoring: true })
    });
    const reader = res.body.getReader(); const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      const msgs = document.getElementById('sim-messages');
      for (const line of decoder.decode(value).split('\\n')) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          try { const { text: t } = JSON.parse(line.slice(6)); full += t; bubble.innerHTML = renderMarkdown(full); msgs.scrollTop = 99999; } catch(e) {}
        }
      }
    }
  } catch(e) { bubble.innerHTML = '<em style="color:var(--red)">Scoring failed.</em>'; }
}

function handleSimKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendSimMessage(); }
}

// ══════════════════════════════════════════════════════════════════════════════
// SIGNAL FEED
// ══════════════════════════════════════════════════════════════════════════════
async function renderSignalFeed() {
  const content = document.getElementById('signals-content');
  if (!content) return;
  content.innerHTML = '<div style="color:var(--muted);font-size:12px;padding:20px 0">Loading signals\u2026</div>';
  try {
    const res = await fetch('/api/signals');
    const data = await res.json();
    const sigs = data.signals || [];
    content.innerHTML = sigs.map(s => {
      const cardCls = s.tagColor === 'red' ? 'urg' : s.tagColor === 'amber' ? 'amb' : '';
      const icoCls  = s.tagColor === 'red' ? 'red' : s.tagColor === 'amber' ? 'amber' : 'blue';
      const hasAcc  = s.slug && allAccounts.some(a => a.slug === s.slug);
      return '<div class="signal-card ' + cardCls + '">' +
        '<div class="sc-ico ' + icoCls + '">' + (s.icon || '\u26a1') + '</div>' +
        '<div class="sc-body">' +
          '<div class="sc-co">' + s.company + '</div>' +
          '<div class="sc-txt">' + s.text + '</div>' +
        '</div>' +
        '<div class="sc-right">' +
          '<span class="sc-tag ' + s.tagColor + '">' + s.tag + '</span>' +
          (hasAcc ? '<button class="sc-act" data-slug="' + s.slug + '" data-name="' + s.company + '" onclick="signalOutreach(this.dataset.slug,this.dataset.name)">Write Outreach</button>' : '') +
        '</div>' +
      '</div>';
    }).join('');
  } catch(e) {
    content.innerHTML = '<div style="color:var(--red);font-size:12px">Failed to load signals</div>';
  }
}

function signalOutreach(slug, name) {
  selectAccount(slug, name);
  document.getElementById('chat-input').value = 'Write a LinkedIn outreach message for ' + name + ' based on the active signal. Language: English. Match tone to the urgency.';
  autoResize(document.getElementById('chat-input'));
  showToast('Account loaded \u2014 outreach ready \u2191');
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5050))
    print(f"\n  JAKALA GTM OS running at http://localhost:{port}\n")
    app.run(debug=False, port=port, threaded=True)
