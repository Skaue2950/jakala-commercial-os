from datetime import datetime
from pathlib import Path

today = datetime.utcnow().strftime("%Y-%m-%d")

content = f"""# Daily Lead Radar — {today}

## Countries
- Norway
- Sweden
- Denmark
- United Kingdom
- France

## What to review today
Look for:
- AI initiatives
- ecommerce platform changes
- digital transformation programs
- leadership hires
- funding
- new digital strategy announcements

## Leads
- Add findings here

## Notes
- Match each lead to GTM strategy
- Suggest entry offer
- Suggest next action
"""

out_dir = Path("intelligence/daily-leads")
out_dir.mkdir(parents=True, exist_ok=True)

file_path = out_dir / f"{today}.md"
file_path.write_text(content, encoding="utf-8")

print(f"Created {file_path}")