"""
Debrief Generator for Abuzz Competitor Intelligence
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


def generate_cuid():
    return 'c' + uuid.uuid4().hex[:24]


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


SYSTEM_PROMPT = """You are a strategic intelligence analyst for Abuzz, a 3D wayfinding and kiosk solutions company based in UAE/Australia.

Generate a comprehensive weekly intelligence debrief based on competitor activities.

Key Context:
- Primary Markets: UAE, Saudi Arabia, Qatar (malls, airports, hospitals)
- Main Competitors: Mappedin, 22Miles, Pointr, ViaDirect, MapsPeople
- Threat Levels: 1 (routine) to 5 (major threat in MENA)

Structure your debrief with:
1. **Executive Summary** (2-3 sentences on key trends)
2. **High-Priority Threats** (threat level 4-5 items)
3. **Regional Analysis** (MENA focus, then other regions)
4. **Competitor Movements** (grouped by company)
5. **Strategic Recommendations** (actionable insights)

Use clear markdown formatting with headers, bullet points, and emphasis.
Be concise but actionable."""


def fetch_recent_news(days=7):
    """Fetch news from the last N days"""
    conn = get_db_connection()
    cursor = conn.cursor()

    end = datetime.datetime.now(datetime.timezone.utc)
    start = end - datetime.timedelta(days=days)

    cursor.execute("""
        SELECT cn.*, c.name as competitor_name
        FROM "CompetitorNews" cn
        JOIN "Competitor" c ON cn."competitorId" = c.id
        WHERE cn.date >= %s AND cn.date <= %s
        ORDER BY cn."threatLevel" DESC
        LIMIT 50
    """, (start.isoformat(), end.isoformat()))

    news = cursor.fetchall()
    conn.close()
    return news, start, end


def format_news(news_items):
    """Format news items for Claude"""
    lines = []
    for i, item in enumerate(news_items, 1):
        lines.append(f"""{i}. [{item['competitor_name']}] {item['title']}
   Date: {item['date']}
   Threat Level: {item['threatLevel']}/5
   Type: {item['eventType']}
   Region: {item.get('region') or 'Global'}
   Summary: {item['summary']}
   Source: {item['sourceUrl']}
""")
    return '\n'.join(lines)


def generate_debrief(news_items):
    """Generate debrief using Claude"""
    formatted = format_news(news_items)

    user_prompt = f"""Analyze these {len(news_items)} intelligence items from the past week and generate a strategic debrief:

{formatted}

Generate a comprehensive weekly intelligence debrief following the structure outlined."""

    print("  Calling Claude API...")
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return message.content[0].text


def save_debrief(content, period_start, period_end, item_count):
    """Save debrief to database"""
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


def main():
    print("=" * 60)
    print("📊 WEEKLY INTELLIGENCE DEBRIEF GENERATOR")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not found")
        return

    if not DATABASE_URL:
        print("\n❌ ERROR: DATABASE_URL not found")
        return

    # Fetch news
    print("\n📋 Fetching recent news...")
    news, start, end = fetch_recent_news(days=7)
    print(f"   Found {len(news)} items from {start.strftime('%b %d')} to {end.strftime('%b %d, %Y')}")

    if len(news) == 0:
        print("\n⚠️  No news found in the last 7 days. Nothing to generate.")
        return

    # Generate debrief
    print("\n🤖 Generating debrief with Claude...")
    content = generate_debrief(news)
    print(f"   Generated {len(content)} characters")

    # Save to database
    print("\n💾 Saving to database...")
    debrief_id = save_debrief(content, start, end, len(news))
    print(f"   Saved with ID: {debrief_id}")

    print("\n" + "=" * 60)
    print("✅ DEBRIEF GENERATED AND SAVED")
    print("   View at: localhost:3000/debrief or intel.navpro.io/debrief")
    print("=" * 60)


if __name__ == "__main__":
    main()
