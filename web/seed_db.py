"""Run once to seed the Control Center database. python seed_db.py"""
import bcrypt
from datetime import datetime
from models import init_db, SessionLocal, User, Industry, Account, Service, Activation, Signal, Prediction

def hash_pw(pw): return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def seed(force=False):
    from models import Base, engine
    if force:
        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables — reseeding fresh.")
    init_db()
    db = SessionLocal()

    if not force and db.query(User).count() > 0:
        print("Already seeded — skipping.")
        db.close(); return

    # ── USERS ──────────────────────────────────────────────────────────────
    pw = hash_pw("Jakala2026!")
    users = [
        User(name="Jacob Skaue",     email="jacob@jakala.com",   password_hash=pw, role="country_head", country="no", initials="JS"),
        User(name="Anna Jensen",     email="anna@jakala.com",    password_hash=pw, role="country_head", country="dk", initials="AJ"),
        User(name="Erik Lindqvist",  email="erik@jakala.com",    password_hash=pw, role="country_head", country="se", initials="EL"),
        User(name="James Wright",    email="james@jakala.com",   password_hash=pw, role="country_head", country="uk", initials="JW"),
        User(name="Sophie Martin",   email="sophie@jakala.com",  password_hash=pw, role="country_head", country="fr", initials="SM"),
        User(name="Global Head",     email="global@jakala.com",  password_hash=pw, role="global",       country=None,  initials="GH"),
    ]
    db.add_all(users); db.flush()

    # ── INDUSTRIES ─────────────────────────────────────────────────────────
    inds = [
        Industry(name="Retail & E-commerce",  slug="retail",    icon="🛒"),
        Industry(name="Fashion & Apparel",     slug="fashion",   icon="👗"),
        Industry(name="Home & DIY",            slug="home-diy",  icon="🏠"),
        Industry(name="Food & Grocery",        slug="food",      icon="🛍️"),
        Industry(name="Finance & Banking",     slug="finance",   icon="🏦"),
        Industry(name="Sports & Outdoor",      slug="sports",    icon="⛷️"),
        Industry(name="Technology & SaaS",     slug="tech-saas", icon="💻"),
        Industry(name="Education",             slug="education", icon="🎓"),
        Industry(name="Energy & Utilities",    slug="energy",    icon="⚡"),
        Industry(name="Healthcare & Pharma",   slug="health",    icon="🏥"),
    ]
    db.add_all(inds); db.flush()
    ind = {i.slug: i for i in inds}

    # ── SERVICES ───────────────────────────────────────────────────────────
    svcs = [
        Service(name="Data Revenue Diagnostic + Speedtrain", slug="data-revenue",    short_name="Data Revenue",     practice="Data & AI",  color="#153EED", entry_price_min=50000,  entry_price_max=100000,  expansion_price_min=200000, expansion_price_max=700000),
        Service(name="AI Readiness Diagnostic",              slug="ai-readiness",    short_name="AI Readiness",     practice="Data & AI",  color="#8B5CF6", entry_price_min=50000,  entry_price_max=100000,  expansion_price_min=200000, expansion_price_max=500000),
        Service(name="Commerce Optimization Pilot",          slug="commerce-opt",    short_name="Commerce Optim.",  practice="Commerce",   color="#00D4A0", entry_price_min=40000,  entry_price_max=80000,   expansion_price_min=100000, expansion_price_max=400000),
        Service(name="Shopify Commerce Build",               slug="shopify-build",   short_name="Shopify Build",    practice="Commerce",   color="#06B6D4", entry_price_min=15000,  entry_price_max=30000,   expansion_price_min=80000,  expansion_price_max=500000),
        Service(name="Hello Growth",                         slug="hello-growth",    short_name="Hello Growth",     practice="Growth",     color="#F59E0B", entry_price_min=20000,  entry_price_max=34000,   expansion_price_min=20000,  expansion_price_max=34000),
        Service(name="DXP Transformation Program",           slug="dxp",             short_name="DXP Transform.",   practice="Commerce",   color="#F6574A", entry_price_min=500000, entry_price_max=3000000, expansion_price_min=500000, expansion_price_max=3000000),
        Service(name="Communication & Media Activation",     slug="media-activation",short_name="Media Activation", practice="Growth",     color="#EC4899", entry_price_min=50000,  entry_price_max=500000,  expansion_price_min=50000,  expansion_price_max=500000),
        Service(name="J-IGNITE Innovation Platform",         slug="j-ignite",        short_name="J-IGNITE",         practice="Data & AI",  color="#F97316", entry_price_min=30000,  entry_price_max=80000,   expansion_price_min=150000, expansion_price_max=500000),
    ]
    db.add_all(svcs); db.flush()
    svc = {s.slug: s for s in svcs}

    # ── NORWAY ACCOUNTS ────────────────────────────────────────────────────
    no_accounts = [
        Account(name="Maxbo",          slug="maxbo",         country="no", industry_id=ind["home-diy"].id,  account_type="existing", icp_score=9, deal_score=8, pipeline_value=500000,  win_probability=0.85, named_buyer="TBD",                  buyer_role="CIO / Head of Ecommerce",           revenue="€539M",    tech_stack="Magento · Pimcore · Perfion · Azure"),
        Account(name="Elkjøp Nordic",  slug="elkjop",        country="no", industry_id=ind["retail"].id,    account_type="prospect",  icp_score=8, deal_score=9, pipeline_value=700000,  win_probability=0.65, named_buyer="Morten Syversen",      buyer_role="Chief Brand & Digital Officer",      revenue="€3.5B",    tech_stack="SAP Commerce · SASE · B2B expansion"),
        Account(name="Trumf",          slug="trumf",         country="no", industry_id=ind["food"].id,      account_type="prospect",  icp_score=9, deal_score=9, pipeline_value=450000,  win_probability=0.40, named_buyer="Rikke Etholm-Idsøe",   buyer_role="Commercial Director (new role)",     revenue="2.9M members", tech_stack="Loyalty platform · retail media gap"),
        Account(name="Varner Group",   slug="varner",        country="no", industry_id=ind["fashion"].id,   account_type="prospect",  icp_score=9, deal_score=9, pipeline_value=500000,  win_probability=0.25, named_buyer="TBD",                  buyer_role="CDO / CTO",                          revenue="€1.2B",    tech_stack="Sitoo Unified Commerce · AutoStore · no shared PIM"),
        Account(name="Vinmonopolet",   slug="vinmonopolet",  country="no", industry_id=ind["retail"].id,    account_type="prospect",  icp_score=8, deal_score=8, pipeline_value=200000,  win_probability=0.35, named_buyer="Espen Terland",        buyer_role="Chief Digital Officer (new)",        revenue="€2.1B",    tech_stack="17K+ SKUs · new CDO honeymoon window"),
        Account(name="Skeidar",        slug="skeidar",       country="no", industry_id=ind["home-diy"].id,  account_type="prospect",  icp_score=8, deal_score=8, pipeline_value=200000,  win_probability=0.40, named_buyer="Sujit Nath",           buyer_role="CIO",                                revenue="€180M",    tech_stack="MS Dynamics 365 Commerce · SpectrumOne CDP"),
        Account(name="Helly Hansen",   slug="helly-hansen",  country="no", industry_id=ind["fashion"].id,   account_type="prospect",  icp_score=8, deal_score=8, pipeline_value=300000,  win_probability=0.25, named_buyer="Joumana Lovstad",      buyer_role="CMO",                                revenue="€650M",    tech_stack="55 Adobe Commerce sites · 65K SKUs per site"),
        Account(name="Bulder Bank",    slug="bulder-bank",   country="no", industry_id=ind["finance"].id,   account_type="prospect",  icp_score=8, deal_score=8, pipeline_value=200000,  win_probability=0.30, named_buyer="Simen Eilertsen",      buyer_role="Head of Digital",                    revenue="€80M",     tech_stack="Google Cloud · post-merger integration"),
        Account(name="Sport Outlet",   slug="sport-outlet",  country="no", industry_id=ind["sports"].id,    account_type="prospect",  icp_score=8, deal_score=8, pipeline_value=150000,  win_probability=0.30, named_buyer="Tor-André Skeie",      buyer_role="CEO (CTO/CDO both vacant)",          revenue="€120M",    tech_stack="18 parallel webshops · no CDO"),
        Account(name="Cognite",        slug="cognite",       country="no", industry_id=ind["tech-saas"].id, account_type="prospect",  icp_score=9, deal_score=8, pipeline_value=34000,   win_probability=0.40, named_buyer="Sandy Joung",          buyer_role="CMO",                                revenue="$117M ARR", tech_stack="Azure Marketplace ISV · Microsoft partner"),
        Account(name="Simployer",      slug="simployer",     country="no", industry_id=ind["tech-saas"].id, account_type="prospect",  icp_score=7, deal_score=7, pipeline_value=27000,   win_probability=0.35, named_buyer="Vigleik Takle",        buyer_role="CEO",                                revenue="€40M ARR", tech_stack="HRM SaaS · Nordic market"),
        Account(name="Jernia",         slug="jernia",        country="no", industry_id=ind["retail"].id,    account_type="prospect",  icp_score=7, deal_score=8, pipeline_value=200000,  win_probability=0.35, named_buyer="Espen Karlsen",        buyer_role="CEO",                                revenue="€280M",    tech_stack="SAP Commerce Cloud · Bluestone PIM (recently live)"),
        Account(name="Nille",          slug="nille",         country="no", industry_id=ind["retail"].id,    account_type="prospect",  icp_score=7, deal_score=7, pipeline_value=150000,  win_probability=0.30, named_buyer="Kjersti Hobøl",        buyer_role="CEO",                                revenue="€470M",    tech_stack="Optimizely · Dynamics NAV"),
    ]
    db.add_all(no_accounts); db.flush()

    # ── DENMARK ACCOUNTS ───────────────────────────────────────────────────
    dk_accounts = [
        Account(name="Boozt",          slug="boozt",         country="dk", industry_id=ind["retail"].id,    account_type="prospect",  icp_score=9, deal_score=8, pipeline_value=300000,  win_probability=0.70, named_buyer="Jesper Brøndum",       buyer_role="CTO / Co-founder",                   revenue="€600M",    tech_stack="Pure ecommerce · high data maturity · AI investment"),
        Account(name="Matas Group",    slug="matas",         country="dk", industry_id=ind["retail"].id,    account_type="prospect",  icp_score=9, deal_score=9, pipeline_value=700000,  win_probability=0.25, named_buyer="TBD",                  buyer_role="CTO / CDO",                          revenue="€600M",    tech_stack="SymphonyAI (category AI live Jan 2026)"),
        Account(name="Siteimprove",    slug="siteimprove",   country="dk", industry_id=ind["tech-saas"].id, account_type="prospect",  icp_score=9, deal_score=9, pipeline_value=34000,   win_probability=0.60, named_buyer="Jen Jones",            buyer_role="CMO (started March 2026)",           revenue="€80M ARR", tech_stack="SaaS · Azure Marketplace"),
        Account(name="Imerco",         slug="imerco",        country="dk", industry_id=ind["retail"].id,    account_type="prospect",  icp_score=8, deal_score=7, pipeline_value=200000,  win_probability=0.35, named_buyer="Mads Bøgh Larsen",     buyer_role="Head of E-commerce",                 revenue="€350M",    tech_stack="DI Frontrunner member"),
        Account(name="Bestseller",     slug="bestseller",    country="dk", industry_id=ind["fashion"].id,   account_type="prospect",  icp_score=8, deal_score=8, pipeline_value=400000,  win_probability=0.25, named_buyer="TBD",                  buyer_role="Group CTO / CDO",                    revenue="€5.1B",    tech_stack="13 brands · 70 markets · transformation mandate"),
        Account(name="Heimdal Security",slug="heimdal",      country="dk", industry_id=ind["tech-saas"].id, account_type="prospect",  icp_score=7, deal_score=7, pipeline_value=20000,   win_probability=0.35, named_buyer="Jesper Frederiksen",   buyer_role="CEO",                                revenue="€30M ARR", tech_stack="Cybersecurity SaaS"),
    ]
    db.add_all(dk_accounts); db.flush()

    # ── SWEDEN ACCOUNTS ────────────────────────────────────────────────────
    se_accounts = [
        Account(name="H&M Group",      slug="hm",            country="se", industry_id=ind["fashion"].id,   account_type="prospect",  icp_score=9, deal_score=9, pipeline_value=900000,  win_probability=0.65, named_buyer="Adam Ull",             buyer_role="Global Product Information Lead",    revenue="€20B",     tech_stack="Google Cloud AI partnership · AI strategy public"),
        Account(name="Clas Ohlson",    slug="clas-ohlson",   country="se", industry_id=ind["retail"].id,    account_type="prospect",  icp_score=7, deal_score=8, pipeline_value=350000,  win_probability=0.55, named_buyer="Helena Holmström",     buyer_role="CMO",                                revenue="€1.1B",    tech_stack="Adobe Commerce · MSEK 400 DC automation (March 2026)"),
        Account(name="Lyko",           slug="lyko",          country="se", industry_id=ind["retail"].id,    account_type="prospect",  icp_score=8, deal_score=7, pipeline_value=200000,  win_probability=0.30, named_buyer="Peter Gunnarsson",     buyer_role="CTO",                                revenue="€200M",    tech_stack="Beauty e-commerce · high loyalty data"),
        Account(name="Quinyx",         slug="quinyx",        country="se", industry_id=ind["tech-saas"].id, account_type="prospect",  icp_score=8, deal_score=8, pipeline_value=27000,   win_probability=0.50, named_buyer="Ani Obermeier",        buyer_role="CMO (new in role)",                  revenue="€50M ARR", tech_stack="WFM SaaS · IDC Leader 2025"),
        Account(name="Oneflow",        slug="oneflow",       country="se", industry_id=ind["tech-saas"].id, account_type="prospect",  icp_score=7, deal_score=7, pipeline_value=20000,   win_probability=0.30, named_buyer="Anders Hamnes",        buyer_role="CEO",                                revenue="€15M ARR", tech_stack="Contract automation SaaS"),
        Account(name="KappAhl",        slug="kappahl",       country="se", industry_id=ind["fashion"].id,   account_type="prospect",  icp_score=7, deal_score=7, pipeline_value=250000,  win_probability=0.25, named_buyer="TBD",                  buyer_role="CDO / Head of Digital",              revenue="€450M",    tech_stack="Omnichannel retail · Nordic markets"),
    ]
    db.add_all(se_accounts); db.flush()

    # ── ACTIVATIONS ────────────────────────────────────────────────────────
    # helper: find account by slug
    all_acc = {a.slug: a for a in no_accounts + dk_accounts + se_accounts}

    activations = [
        # Maxbo - active delivery
        Activation(account_id=all_acc["maxbo"].id,        service_id=svc["data-revenue"].id,  manager="Jacob Skaue",  stage="active",      cost_estimate=80000,  timeline_weeks=12, roi_estimate=250000, notes="Speedtrain onboarding — product data foundation for 1M+ SKUs"),
        # Norway prospects — identified
        Activation(account_id=all_acc["elkjop"].id,       service_id=svc["commerce-opt"].id,  manager="Jacob Skaue",  stage="identified",  cost_estimate=60000,  timeline_weeks=10, roi_estimate=350000, notes="B2B commerce live. New buyer segment needs better product discovery."),
        Activation(account_id=all_acc["trumf"].id,        service_id=svc["data-revenue"].id,  manager="Jacob Skaue",  stage="identified",  cost_estimate=75000,  timeline_weeks=8,  roi_estimate=300000, notes="Retail media gap acknowledged. Rikke E. new Commercial Director — 90-day window."),
        Activation(account_id=all_acc["varner"].id,       service_id=svc["data-revenue"].id,  manager="Jacob Skaue",  stage="identified",  cost_estimate=75000,  timeline_weeks=10, roi_estimate=400000, notes="7 brands, 1200+ stores, no shared PIM. Sitoo Unified Commerce rollout = entry wedge."),
        Activation(account_id=all_acc["vinmonopolet"].id, service_id=svc["data-revenue"].id,  manager="Jacob Skaue",  stage="identified",  cost_estimate=60000,  timeline_weeks=8,  roi_estimate=150000, notes="Espen Terland new CDO (ex-XXL). Honeymoon phase — agenda not set."),
        Activation(account_id=all_acc["skeidar"].id,      service_id=svc["commerce-opt"].id,  manager="Jacob Skaue",  stage="identified",  cost_estimate=60000,  timeline_weeks=10, roi_estimate=200000, notes="'Best furniture portal' ambition stated publicly. Sujit Nath CIO confirmed."),
        Activation(account_id=all_acc["helly-hansen"].id, service_id=svc["shopify-build"].id, manager="Jacob Skaue",  stage="identified",  cost_estimate=25000,  timeline_weeks=6,  roi_estimate=300000, notes="55 Adobe Commerce sites across markets. Acquired by Kontoor Brands June 2025."),
        Activation(account_id=all_acc["bulder-bank"].id,  service_id=svc["ai-readiness"].id,  manager="Jacob Skaue",  stage="identified",  cost_estimate=75000,  timeline_weeks=8,  roi_estimate=200000, notes="Post-merger data consolidation + Google Cloud partnership."),
        Activation(account_id=all_acc["cognite"].id,      service_id=svc["hello-growth"].id,  manager="Jacob Skaue",  stage="identified",  cost_estimate=27000,  timeline_weeks=12, roi_estimate=80000,  notes="$117M ARR. Sandy Joung CMO. Azure Marketplace ISV."),
        # Denmark
        Activation(account_id=all_acc["boozt"].id,        service_id=svc["data-revenue"].id,  manager="Anna Jensen",  stage="identified",  cost_estimate=75000,  timeline_weeks=8,  roi_estimate=250000, notes="Pure ecommerce, high data maturity. CTO Jesper Brøndum = known buyer."),
        Activation(account_id=all_acc["matas"].id,        service_id=svc["ai-readiness"].id,  manager="Anna Jensen",  stage="identified",  cost_estimate=75000,  timeline_weeks=8,  roi_estimate=300000, notes="SymphonyAI live Jan 2026. Adjacent AI layers wide open."),
        Activation(account_id=all_acc["siteimprove"].id,  service_id=svc["hello-growth"].id,  manager="Anna Jensen",  stage="proposed",    cost_estimate=27000,  timeline_weeks=12, roi_estimate=80000,  notes="Jen Jones CMO — started March 2026. Window closing."),
        # Sweden
        Activation(account_id=all_acc["hm"].id,           service_id=svc["data-revenue"].id,  manager="Erik Lindqvist", stage="identified", cost_estimate=100000, timeline_weeks=10, roi_estimate=600000, notes="Google Cloud AI partnership live. Adam Ull identified as Product Information Lead."),
        Activation(account_id=all_acc["clas-ohlson"].id,  service_id=svc["commerce-opt"].id,  manager="Erik Lindqvist", stage="identified", cost_estimate=60000,  timeline_weeks=10, roi_estimate=200000, notes="20% ecommerce growth YoY. MSEK 400 DC automation starting March 2026."),
        Activation(account_id=all_acc["quinyx"].id,       service_id=svc["hello-growth"].id,  manager="Erik Lindqvist", stage="identified", cost_estimate=27000,  timeline_weeks=12, roi_estimate=70000,  notes="Ani Obermeier new CMO. IDC Leader 2025."),
    ]
    db.add_all(activations); db.flush()

    # ── SIGNALS ────────────────────────────────────────────────────────────
    signals = [
        Signal(country=None, vertical="Retail", signal_type="regulation", severity="critical",
               title="EU AI Act — Phase 2 enforcement begins Q3 2026",
               description="High-risk AI systems in retail (recommendation engines, pricing algorithms) must comply with transparency and audit requirements by August 2026.",
               action_recommended="Audit all clients using AI recommendation/pricing tools. Position AI Readiness Diagnostic as compliance accelerator. Entry frame: 'Are your AI systems audit-ready for August?'",
               source="European Commission", date=datetime(2026, 3, 1)),
        Signal(country=None, vertical="Retail", signal_type="regulation", severity="warning",
               title="GDPR enforcement on loyalty data intensifying — NL and SE DPAs active",
               description="Dutch and Swedish data protection authorities have issued fines to retailers using loyalty data for personalization without explicit AI consent.",
               action_recommended="Position Data Revenue Diagnostic as GDPR-compliant data foundation audit. Target loyalty-heavy accounts: Trumf (2.9M members), Kitch'n (1.35M members), Lyko.",
               source="IAPP / DPA press releases", date=datetime(2026, 2, 15)),
        Signal(country="no", vertical="Finance", signal_type="market", severity="info",
               title="Norges Bank expected to cut rates Q2 2026 — retail spending upswing",
               description="Rate cut forecast increases consumer spending confidence in Norway. Retail and home improvement sectors expected to see 3-5% volume uplift H2 2026.",
               action_recommended="Accelerate outreach to Maxbo, Jernia, Skeidar and Nille ahead of the spending wave. Frame Commerce Optimization as revenue capture readiness.",
               source="Norges Bank forward guidance", date=datetime(2026, 3, 10)),
        Signal(country="no", vertical="Sports", signal_type="market", severity="warning",
               title="Frasers Group (UK) accelerating Nordic retail acquisition strategy",
               description="Frasers Group (owner of Sport Direct, XXL post-acquisition) is evaluating further Nordic retail assets. Creates uncertainty and leadership instability.",
               action_recommended="Move fast on Sport Outlet (CTO/CDO both vacant). Acquisition targets often freeze vendor decisions 6 months post-announcement. Window = now.",
               source="Financial Times / Nordic retail press", date=datetime(2026, 3, 5)),
        Signal(country=None, vertical="Fashion", signal_type="technology", severity="warning",
               title="Adobe Commerce end-of-life roadmap accelerating — mass migration signal",
               description="Adobe has confirmed Commerce Cloud on-premise versions will lose full support by 2027. Multiple Nordic fashion brands still on Adobe Commerce (Helly Hansen, Varner sub-brands).",
               action_recommended="Use Shopify Commerce Build pitch with Adobe EOL as the urgency driver. Pipeline: Helly Hansen (55 sites), Varner Group sub-brands. Entry: Shopify Check-up €15-30K.",
               source="Adobe Commerce roadmap", date=datetime(2026, 2, 20)),
    ]
    db.add_all(signals); db.flush()

    # ── PREDICTIONS ────────────────────────────────────────────────────────
    predictions = [
        Prediction(account_id=all_acc["maxbo"].id,  country="no", vertical="Home & DIY",
                   risk_score=2.0, opportunity_score=8.5,
                   trigger_summary="Speedtrain foundation live → data quality improving → Commerce Optimization is the natural next layer. Rate cut = consumer spending upswing. Act Q2 2026.",
                   recommended_service_id=svc["commerce-opt"].id, confidence=0.85, timeframe_weeks=8),
        Prediction(account_id=all_acc["trumf"].id,  country="no", vertical="Food & Grocery",
                   risk_score=5.0, opportunity_score=9.0,
                   trigger_summary="Rikke Etholm-Idsøe first 90 days window closing. GDPR enforcement on loyalty data creates urgency for compliant data architecture. Retail media revenue mandate from board.",
                   recommended_service_id=svc["data-revenue"].id, confidence=0.78, timeframe_weeks=4),
        Prediction(account_id=all_acc["helly-hansen"].id, country="no", vertical="Fashion",
                   risk_score=7.5, opportunity_score=7.0,
                   trigger_summary="Adobe Commerce EOL 2027 — 55 sites need migration path. Kontoor Brands acquisition creates platform consolidation mandate. Risk of budget freeze if global IT intervenes first.",
                   recommended_service_id=svc["shopify-build"].id, confidence=0.72, timeframe_weeks=12),
        Prediction(account_id=all_acc["hm"].id,     country="se", vertical="Fashion",
                   risk_score=3.0, opportunity_score=9.5,
                   trigger_summary="EU AI Act Q3 2026 compliance deadline + Google Cloud AI partnership = dual urgency for data governance audit. H&M's AI ambition outpaces their data infrastructure maturity.",
                   recommended_service_id=svc["data-revenue"].id, confidence=0.80, timeframe_weeks=6),
        Prediction(account_id=all_acc["bulder-bank"].id, country="no", vertical="Finance",
                   risk_score=4.0, opportunity_score=7.5,
                   trigger_summary="Post-merger with Sparebanken Vest creates data consolidation urgency. Google Cloud partnership signals AI ambition. AI Readiness Diagnostic = natural entry before budget is locked.",
                   recommended_service_id=svc["ai-readiness"].id, confidence=0.74, timeframe_weeks=8),
    ]
    db.add_all(predictions)
    db.commit()
    print(f"Seeded: {len(users)} users · {len(inds)} industries · {len(svcs)} services · {len(no_accounts + dk_accounts + se_accounts)} accounts · {len(activations)} activations · {len(signals)} signals · {len(predictions)} predictions")
    db.close()

if __name__ == "__main__":
    seed()
