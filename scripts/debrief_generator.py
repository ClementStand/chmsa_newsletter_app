"""
Debrief Generator for CIMHSA Competitor Intelligence
Generates weekly intelligence debrief using Claude AI and saves to database.
Run locally: ./.venv/bin/python scripts/debrief_generator.py
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import json
import os
import uuid
import anthropic
from dotenv import load_dotenv

# Load .env.local first, then .env as fallback
load_dotenv('.env.local')
load_dotenv()

# Configure
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
_raw_db_url = os.getenv("DATABASE_URL") or os.getenv("DIRECT_URL")
DATABASE_URL = _raw_db_url.split('?')[0] if _raw_db_url else None

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Region relevance weights for CIMHSA
# Higher = more strategically important to CIMHSA
REGION_WEIGHTS = {
    'SOUTH_AMERICA': 10,   # Primary market — Brazil, Argentina, Colombia, Chile
    'BRAZIL':        10,   # Alias used by some records
    'ARGENTINA':      9,
    'LATAM':          8,   # Mexico, Colombia, other LatAm
    'EUROPE':         6,   # Secondary market — Spain, Germany, Italy
    'NORTH_AMERICA':  4,   # US and Mexico — growing market
    'APAC':           2,
    'GLOBAL':         3,
}


def generate_cuid():
    return 'c' + uuid.uuid4().hex[:24]


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


SYSTEM_PROMPT = """You are a strategic intelligence analyst for CIMHSA, a Brazilian manufacturer of CNC machine tools, industrial machinery, and automation solutions.

Your role is to produce a concise, actionable weekly intelligence debrief for CIMHSA's leadership team.

Key Context:
- CIMHSA's primary markets: Brazil, Argentina, Colombia, Chile (South America)
- Secondary markets: Spain, Germany, Italy, France (Europe)
- Growth markets: USA, Mexico
- Industry: CNC machine tools, industrial machining centres, automation, laser cutting, injection moulding
- Threat drivers: competitors winning large government/industrial tenders in South America, new factory openings in the region, disruptive product launches (fibre laser, 5-axis CNC), price-competitive new entrants

Threat Levels:
- 5: Direct threat — competitor wins a major contract or opens a factory in South America
- 4: Significant — major product launch or market expansion into CIMHSA's core regions
- 3: Moderate — relevant European or North American move worth monitoring
- 2: Low — minor development outside core regions
- 1: Informational only

Structure your debrief EXACTLY as follows (use markdown):

## Executive Summary
2–3 sentences covering the single most important development and overall competitive temperature this week.

## Top 3 Most Relevant Developments
For each of the 3 most strategically important items:
### [Rank]. [Competitor Name] — [Short headline]
- **Why it matters for CIMHSA:** 1–2 sentences on the direct implication
- **Region:** …  |  **Threat Level:** X/5  |  **Date:** YYYY-MM-DD
- **Source:** [URL]

## Regional Breakdown
### South America (Primary)
Bullet list of relevant developments, or "No significant activity this week."

### Europe (Secondary)
Bullet list of relevant developments, or "No significant activity this week."

### North America & Other
Bullet list of relevant developments, or "No significant activity this week."

## Competitor Movements
Group remaining news items by competitor. One bullet per item.

## Strategic Recommendations
3–5 concise, actionable recommendations for CIMHSA based on this week's intelligence.

## Week in Summary
A single paragraph (max 5 sentences) written for a busy executive who will read only this section. Cover the top threat, the key opportunity, and one recommended action.

Be concise, avoid filler phrases, and always tie observations back to CIMHSA's South American market position."""


def fetch_recent_news(days=7):
    """Fetch news from the last N days, ranked by strategic relevance to CIMHSA."""
    conn = get_db_connection()
    cursor = conn.cursor()

    end = datetime.datetime.now(datetime.timezone.utc)
    start = end - datetime.timedelta(days=days)

    cursor.execute("""
        SELECT cn.*, c.name as competitor_name, c.industry
        FROM "CompetitorNews" cn
        JOIN "Competitor" c ON cn."competitorId" = c.id
        WHERE cn.date >= %s AND cn.date <= %s
        ORDER BY cn."threatLevel" DESC, cn.date DESC
        LIMIT 60
    """, (start.isoformat(), end.isoformat()))

    news = cursor.fetchall()
    conn.close()

    # Score each item: threat level (0-50) + region weight (0-10) + recency bonus
    def score(item):
        threat = (item.get('threatLevel') or 1) * 10
        region = (item.get('region') or 'GLOBAL').upper()
        region_score = REGION_WEIGHTS.get(region, 1)
        # Small recency bonus: articles from the last 3 days get +5
        try:
            item_date = item['date']
            if isinstance(item_date, str):
                item_date = datetime.datetime.fromisoformat(item_date.replace('Z', '+00:00'))
            days_old = (end - item_date).days
            recency = max(0, 5 - days_old)
        except Exception:
            recency = 0
        return threat + region_score + recency

    ranked = sorted(news, key=score, reverse=True)
    return ranked, start, end


def pick_top3(news_items):
    """Return the top 3 items by score (already pre-sorted by fetch_recent_news)."""
    return news_items[:3]


def format_news(news_items):
    """Format all news items for Claude."""
    lines = []
    for i, item in enumerate(news_items, 1):
        region = (item.get('region') or 'Global').upper()
        lines.append(
            f"{i}. [{item['competitor_name']}] {item['title']}\n"
            f"   Date: {item['date']} | Threat: {item.get('threatLevel', '?')}/5 | "
            f"Type: {item.get('eventType', '?')} | Region: {region}\n"
            f"   Summary: {item.get('summary', '')}\n"
            f"   Source: {item.get('sourceUrl', '')}\n"
        )
    return '\n'.join(lines)


def generate_debrief(news_items, top3):
    """Generate debrief using Claude, with top-3 pre-highlighted."""
    formatted_all = format_news(news_items)

    top3_hint = "\n".join(
        f"- [{t['competitor_name']}] {t['title']} (Threat {t.get('threatLevel','?')}/5, {(t.get('region') or 'Global').upper()})"
        for t in top3
    )

    user_prompt = (
        f"Analyze these {len(news_items)} intelligence items and generate a strategic weekly debrief for CIMHSA.\n\n"
        f"SUGGESTED TOP 3 (by relevance score — you may adjust if you judge differently):\n"
        f"{top3_hint}\n\n"
        f"ALL ITEMS:\n{formatted_all}\n\n"
        f"Generate the full debrief following the required structure."
    )

    print("  Calling Claude API...")
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return message.content[0].text


def save_debrief(content, period_start, period_end, item_count):
    """Save debrief to database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    debrief_id = generate_cuid()
    now = datetime.datetime.now(datetime.timezone.utc)

    cursor.execute("""
        INSERT INTO "Debrief" (id, content, "periodStart", "periodEnd", "itemCount", "generatedAt")
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        debrief_id,
        content,
        period_start.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        period_end.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        item_count,
        now.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    ))

    conn.commit()
    conn.close()
    return debrief_id


def main(days=7):
    print("=" * 60)
    print("📊 CIMHSA WEEKLY INTELLIGENCE DEBRIEF GENERATOR")
    print("   Powered by Claude AI")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not found")
        return

    if not DATABASE_URL:
        print("\n❌ ERROR: DATABASE_URL not found")
        return

    # Fetch and rank news
    print(f"\n📋 Fetching news from the last {days} days...")
    news, start, end = fetch_recent_news(days=days)
    print(f"   Found {len(news)} items from {start.strftime('%b %d')} to {end.strftime('%b %d, %Y')}")

    if len(news) == 0:
        print(f"\n⚠️  No news found in the last {days} days. Try --days 14 or run the fetcher first.")
        return

    # Identify top 3
    top3 = pick_top3(news)
    print(f"\n🏆 Top 3 by relevance score:")
    for i, t in enumerate(top3, 1):
        region = (t.get('region') or 'Global').upper()
        print(f"   {i}. [{t['competitor_name']}] {t['title'][:60]} (T{t.get('threatLevel','?')}, {region})")

    # Generate debrief
    print("\n🤖 Generating debrief with Claude...")
    content = generate_debrief(news, top3)
    print(f"   Generated {len(content)} characters")

    # Save to database
    print("\n💾 Saving to database...")
    debrief_id = save_debrief(content, start, end, len(news))
    print(f"   Saved with ID: {debrief_id}")

    print("\n" + "=" * 60)
    print("✅ DEBRIEF GENERATED AND SAVED")
    print("   View at: localhost:3000/debrief")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate CIMHSA weekly intelligence debrief')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back (default: 7)')
    args = parser.parse_args()
    main(days=args.days)
