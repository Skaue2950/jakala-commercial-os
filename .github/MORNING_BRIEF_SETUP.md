# CEO Morning Brief — Setup Guide

Klar på 10 minutter.

---

## Hvad du skal bruge

1. **SendGrid konto** — gratis tier (100 emails/dag). sendgrid.com
2. **4 GitHub Secrets** sat på dette repo

---

## Trin 1 — SendGrid

1. Opret konto på sendgrid.com
2. Gå til **Settings → API Keys → Create API Key**
3. Vælg "Restricted Access" → aktivér kun "Mail Send"
4. Kopiér API key

---

## Trin 2 — GitHub Secrets

Gå til: **github.com/[dit-repo] → Settings → Secrets and variables → Actions**

Tilføj disse 4 secrets:

| Secret name | Værdi |
|-------------|-------|
| `ANTHROPIC_API_KEY` | Din Anthropic API key |
| `SENDGRID_API_KEY` | SendGrid API key fra trin 1 |
| `TO_EMAIL` | Din email (modtager) — fx `jacob.skaue@jakala.com` |
| `FROM_EMAIL` | Afsender email — skal være verified i SendGrid |

---

## Trin 3 — Verify sender i SendGrid

1. I SendGrid: **Settings → Sender Authentication → Single Sender Verification**
2. Verificér din `FROM_EMAIL` adresse

---

## Trin 4 — Test

Kør manuelt fra GitHub:
1. Gå til **Actions → CEO Morning Brief**
2. Klik **Run workflow**
3. Tjek din inbox inden for 2 minutter

---

## Hvornår kører det?

**Automatisk:** Hver mandag kl. 07:00 CET

**Manuelt:** Actions → CEO Morning Brief → Run workflow

---

## Email format

Subject: `🟡 JAKALA Nordic — CCO Brief · Uke 12 · 16. mar 2026`

Indhold:
- Status (Grøn/Amber/Rød) med begrundelse
- Pipeline KPIs (total · weighted · base case)
- Situasjon på 60 sekunder
- Topp 3 prioriteter denne uken
- Varme signaler
- Pipeline scorecard (top 6)
- Største risiko + mulighed
- Forecast (best/base/worst)
- War Room Verdict
