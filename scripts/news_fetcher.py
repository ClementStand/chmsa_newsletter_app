"""
News Fetcher for CIMHSA Competitor Intelligence
Uses Serper.dev (Google Search API) + Claude AI (Anthropic) for analysis
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import json
import os
import time
import uuid
import re
import requests
import anthropic
from dotenv import load_dotenv

# Load .env.local first, then .env as fallback
load_dotenv('.env.local')
load_dotenv()

# Configure APIs
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
# Get database URL - prefer pooler connection, strip Prisma-specific params
_raw_db_url = os.getenv("DATABASE_URL") or os.getenv("DIRECT_URL")
DATABASE_URL = _raw_db_url.split('?')[0] if _raw_db_url else None  # Remove query params like ?pgbouncer=true

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Priority competitors (most likely to have news)
PRIORITY_COMPETITORS = [
    "Indústrias Romi", "Fagor Automation", "Eurostec", "Alletech Máquinas"
]

# Regional search configurations
REGIONS = {
    'global': {'gl': 'us', 'hl': 'en'},
    'brazil_pt': {'gl': 'br', 'hl': 'pt'},  # Brazil in Portuguese
    'brazil_en': {'gl': 'br', 'hl': 'en'},  # Brazil in English
    'europe': {'gl': 'es', 'hl': 'es'},  # Spain (Fagor HQ)
    'latam': {'gl': 'mx', 'hl': 'es'},  # Mexico / Latin America
}

# URLs that indicate non-news content (product pages, sales, profiles)
BLOCKED_URL_PATTERNS = [
    'linkedin.com', 'crunchbase.com', 'facebook.com', 'instagram.com',
    'youtube.com', 'twitter.com', 'x.com',
    '/product', '/products', '/catalog', '/catalogo',
    '/shop', '/store', '/loja', '/tienda',
    '/contact', '/contato', '/about', '/sobre',
    'mercadolivre', 'mercadolibre', 'amazon.com', 'alibaba.com',
    'olx.com', 'ebay.com',
    'glassdoor.com', 'indeed.com', 'ziprecruiter.com',
    'wikipedia.org', 'dnb.com', 'zoominfo.com',
    '/careers', '/vagas', '/empleo',
]


def is_news_url(url):
    """Filter out product pages, sales sites, social media, and company profiles"""
    if not url:
        return False
    url_lower = url.lower()
    for pattern in BLOCKED_URL_PATTERNS:
        if pattern in url_lower:
            return False
    return True


ANALYSIS_PROMPT = """You are a competitive intelligence analyst for CIMHSA, a company that manufactures and sells CNC machine tools, industrial machinery, and automation solutions.

I found these search results about {competitor_name}:

{articles}

IMPORTANT: Articles may be in Portuguese, Spanish, or English. Analyze ALL articles regardless of language. Always output your title and summary in ENGLISH, even if the source article is in another language.

Your job is to find REAL NEWS EVENTS only. Include:
- New contracts, deals, project wins
- Partnerships, acquisitions, mergers, joint ventures
- Product launches, new machine models, technology announcements
- Trade show appearances with NEW products or announcements
- Financial results, earnings reports, revenue milestones
- New factory openings, facility expansions
- Leadership changes, executive appointments
- Awards, certifications, recognitions
- Market expansion into new countries or regions
- Funding rounds, IPO news, investment news

STRICTLY EXCLUDE (these are NOT news):
- Product catalog pages or sales listings
- Generic company profile descriptions ("Company X sells machines...")
- Job postings or career pages
- Social media posts without real news content
- "About us" or company overview pages
- Price lists or quotation pages
- Old press releases just being re-indexed

If NONE of the articles contain real news events, respond with: {{"no_relevant_news": true}}

Otherwise, return JSON:

{{
  "news_items": [
    {{
      "event_type": "New Project/Installation" | "Investment/Funding Round" | "Award/Recognition" | "Product Launch" | "Partnership/Acquisition" | "Leadership Change" | "Market Expansion" | "Technical Innovation" | "Financial Performance",
      "title": "Clear headline in ENGLISH (max 100 chars)",
      "summary": "2-3 sentence summary in ENGLISH (max 500 chars). Must describe a specific event, not a general company description.",
      "threat_level": 1-5,
      "date": "YYYY-MM-DD",
      "source_url": "The actual URL from the article",
      "region": "NORTH_AMERICA" | "EUROPE" | "SOUTH_AMERICA" | "APAC" | "GLOBAL",
      "details": {{
        "location": "City, Country or null",
        "financial_value": "Amount or null",
        "partners": ["Companies"],
        "products": ["Products"]
      }}
    }}
  ]
}}

Threat Level Guide:
- 1: Routine news, minimal impact
- 2: Minor development, worth monitoring
- 3: Moderate competitive move
- 4: Significant threat to CIMHSA
- 5: Major threat (big contract in Brazil/Latin America, or game-changing development)

CRITICAL: Assign higher threat levels (4-5) for news in Brazil and Latin America as these are our primary markets.

DATE EXTRACTION INSTRUCTIONS:
- Use the EXACT "Published Date" provided in the article metadata.
- Do NOT use today's date unless the article explicitly says "today".
- If the date is "October 28, 2024", the output date must be "2024-10-28".
- If no date is found, use the current date as fallback.

Return ONLY valid JSON, no markdown formatting or explanation."""


def sanitize_text(text):
    """Remove problematic characters"""
    if not text:
        return ""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', str(text))
    replacements = {
        '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-',
        '\u2026': '...',
        '\u00a0': ' ',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text.strip()


def generate_cuid():
    return 'c' + uuid.uuid4().hex[:24]


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_competitors():
    """Fetch competitors from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, website, industry, region 
        FROM "Competitor" 
        WHERE status = 'active' OR status IS NULL
    """)
    all_competitors = cursor.fetchall()  # Already dicts thanks to RealDictCursor
    conn.close()
    
    def sort_key(c):
        name = c['name']
        if name in PRIORITY_COMPETITORS:
            return (0, PRIORITY_COMPETITORS.index(name))
        elif 'Direct' in (c.get('industry') or ''):
            return (1, name)
        else:
            return (2, name)
    
    return sorted(all_competitors, key=sort_key)


def check_existing_url(cursor, url):
    """Check if URL already exists in database (pass cursor to reuse connection)"""
    cursor.execute('SELECT id FROM "CompetitorNews" WHERE "sourceUrl" = %s', (url,))
    return cursor.fetchone() is not None


def save_news_item(competitor_id, news_item):
    """Save news item to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    source_url = sanitize_text(news_item.get('source_url', ''))
    
    if not source_url or 'example.com' in source_url:
        conn.close()
        return False, "invalid_url"
    
    if check_existing_url(cursor, source_url):
        conn.close()
        return False, "duplicate"
    
    try:
        news_id = generate_cuid()
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Prepare strictly formatted strings for SQLite/Prisma compatibility
        iso_now_str = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        title = sanitize_text(news_item.get('title', 'Untitled'))[:200]
        summary = sanitize_text(news_item.get('summary', ''))[:1000]
        event_type = sanitize_text(news_item.get('event_type', 'Unknown'))[:100]
        region = news_item.get('region', 'GLOBAL')
        
        threat_level = news_item.get('threat_level', 2)
        try:
            threat_level = int(threat_level)
        except:
            threat_level = 2
        threat_level = max(1, min(5, threat_level))
        
        date_str = news_item.get('date', now.strftime('%Y-%m-%d'))
        try:
            news_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
        except:
            news_date = now

        # Cap future dates to today
        if news_date > now:
            news_date = now

        # Skip news before 2024
        cutoff = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        if news_date < cutoff:
            conn.close()
            return False, "pre_2024"

        news_date_str = news_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        details = news_item.get('details', {})
        if isinstance(details, dict):
            clean_details = {
                'location': sanitize_text(details.get('location', '')),
                'financial_value': sanitize_text(details.get('financial_value', '')),
                'partners': [sanitize_text(p) for p in (details.get('partners') or [])],
                'products': [sanitize_text(p) for p in (details.get('products') or [])]
            }
        else:
            clean_details = {}
        details_json = json.dumps(clean_details)
        
        cursor.execute("""
            INSERT INTO "CompetitorNews" (
                id, "competitorId", "eventType", date, title, summary,
                "threatLevel", details, "sourceUrl", "isRead", "isStarred", "extractedAt", region
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            news_id,
            competitor_id,
            event_type,
            news_date_str,
            title,
            summary,
            threat_level,
            details_json,
            source_url,
            False,
            False,
            iso_now_str,
            region
        ))
        
        conn.commit()
        conn.close()
        return True, "saved"
        
    except Exception as e:
        conn.close()
        return False, str(e)


def get_last_fetch_date():
    """Get the date of the most recent news item in the DB to use as search start date"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT MAX("extractedAt") as last_fetch FROM "CompetitorNews"')
        result = cursor.fetchone()
        conn.close()
        if result and result['last_fetch']:
            return result['last_fetch']
    except:
        pass
    return None


def get_all_existing_urls():
    """Fetch all existing source URLs from DB for fast duplicate checking"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT "sourceUrl" FROM "CompetitorNews"')
    urls = {row['sourceUrl'] for row in cursor.fetchall()}
    conn.close()
    return urls


def search_serper(query, search_type='news', region='global', num_results=10, date_restrict=None):
    """
    Search using Serper.dev API
    search_type: 'news' or 'search'
    date_restrict: e.g. 'd3' for last 3 days, 'w1' for last week
    """
    if not SERPER_API_KEY:
        print("      ERROR: SERPER_API_KEY not set in .env")
        return []
    
    url = f"https://google.serper.dev/{search_type}"
    
    region_config = REGIONS.get(region, REGIONS['global'])
    
    payload = {
        "q": query,
        "gl": region_config['gl'],
        "hl": region_config['hl'],
        "num": num_results
    }
    
    # Add date restriction if provided
    if date_restrict:
        payload["tbs"] = f"qdr:{date_restrict}"
    
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Extract results based on search type
        if search_type == 'news':
            return data.get('news', [])
        else:
            return data.get('organic', [])
            
    except requests.exceptions.RequestException as e:
        print(f"      Serper error: {e}")
        return []


def search_news(competitor_name, regions_to_search=['global', 'brazil_pt', 'brazil_en', 'europe'], date_restrict=None):
    """
    Search for news about a competitor across multiple regions and languages.
    Focuses on actual news sources, not product/sales pages.
    date_restrict: e.g. 'd3' for last 3 days, 'w1' for last week
    """
    all_results = []
    seen_urls = set()
    filtered_count = 0
    
    # News-focused search queries in English, Portuguese, and Spanish
    queries = [
        # English — news-focused
        f'"{competitor_name}" announcement OR launch OR partnership OR expansion OR acquisition',
        f'"{competitor_name}" revenue OR earnings OR "new contract" OR award',
        # Portuguese — news-focused
        f'"{competitor_name}" lan\u00e7amento OR parceria OR expans\u00e3o OR aquisi\u00e7\u00e3o OR faturamento',
        f'"{competitor_name}" not\u00edcia OR feira OR FEIMEC OR Expomafe',
        # Spanish — news-focused
        f'"{competitor_name}" lanzamiento OR asociaci\u00f3n OR expansi\u00f3n OR adquisici\u00f3n',
    ]
    
    for region in regions_to_search:
        for query in queries:
            # Use NEWS search type only — this avoids product pages
            results = search_serper(query, search_type='news', region=region, num_results=10, date_restrict=date_restrict)
            
            for r in results:
                url = r.get('link', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    if is_news_url(url):
                        r['_search_region'] = region
                        all_results.append(r)
                    else:
                        filtered_count += 1
            
            if len(all_results) >= 25:
                break
        
        if len(all_results) >= 25:
            break
    
    if filtered_count > 0:
        print(f" ({filtered_count} non-news URLs filtered)", end="")
    
    return all_results[:25]


def analyze_with_claude(competitor_name, articles):
    """Send articles to Claude for analysis, batching if needed"""
    if not articles:
        return None
    
    if not ANTHROPIC_API_KEY:
        print("      ERROR: ANTHROPIC_API_KEY not set in .env")
        return None
    
    # Batch articles to avoid overwhelming Claude (max 12 per batch)
    BATCH_SIZE = 12
    all_news_items = []
    
    for batch_start in range(0, len(articles), BATCH_SIZE):
        batch = articles[batch_start:batch_start + BATCH_SIZE]
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (len(articles) + BATCH_SIZE - 1) // BATCH_SIZE
        
        if total_batches > 1:
            print(f"      [batch {batch_num}/{total_batches}]", end="")
        
        articles_text = ""
        for i, article in enumerate(batch, 1):
            title = sanitize_text(article.get('title', 'No title'))
            snippet = sanitize_text(article.get('snippet', article.get('description', '')))
            url = article.get('link', article.get('url', ''))
            date = article.get('date', 'Unknown')
            region = article.get('_search_region', 'global').upper()
            
            articles_text += f"""
---
Article {i}:
Title: {title}
Published Date: {date}
URL: {url}
Region Found: {region}
Content: {snippet[:500]}
---
"""
        
        prompt = ANALYSIS_PROMPT.format(
            competitor_name=competitor_name,
            articles=articles_text
        )
        
        try:
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text.strip()
            
            # Clean JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            response_text = response_text.strip()
            
            # Try to fix truncated JSON
            result = None
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Attempt recovery: try adding closing brackets
                for fix in ['}]}', ']}', '}']:
                    try:
                        result = json.loads(response_text + fix)
                        print(" (recovered truncated JSON)", end="")
                        break
                    except json.JSONDecodeError:
                        continue
            
            if result is None:
                print(f" JSON parse failed, skipping batch")
                continue
            
            if not result.get('no_relevant_news'):
                batch_items = result.get('news_items', [])
                all_news_items.extend(batch_items)
                if total_batches > 1:
                    print(f" → {len(batch_items)} items")
            else:
                if total_batches > 1:
                    print(f" → no relevant news")
                
        except anthropic.APIError as e:
            print(f"\n      Claude API error: {e}")
            continue
        except Exception as e:
            print(f"\n      Error: {e}")
            continue
        
        # Small delay between batches
        if batch_start + BATCH_SIZE < len(articles):
            time.sleep(0.5)
    
    if not all_news_items:
        return {'no_relevant_news': True}
    
    return {'news_items': all_news_items}


def fetch_news_for_competitor(competitor, regions=['global', 'brazil_pt', 'brazil_en', 'europe'], existing_urls=None, date_restrict=None):
    """Fetch and analyze news for one competitor"""
    comp_id = competitor['id']
    name = competitor['name']
    
    print(f"\n  🔍 {name}", end="")
    
    articles = search_news(name, regions, date_restrict=date_restrict)
    
    if not articles:
        print(f" — no articles found")
        return 0
    
    # Pre-filter: remove articles whose URLs are already in the DB
    if existing_urls:
        new_articles = [a for a in articles if a.get('link', '') not in existing_urls]
        skipped = len(articles) - len(new_articles)
        if skipped > 0:
            print(f" — {len(articles)} found, {skipped} already known", end="")
        if not new_articles:
            print(f" — all duplicates, skipping Claude")
            return 0
        articles = new_articles
    
    print(f" — analyzing {len(articles)} new articles...")
    
    analysis = analyze_with_claude(name, articles)
    
    if not analysis:
        print(f"      Analysis failed")
        return 0
    
    if analysis.get('no_relevant_news'):
        print(f"      No relevant news found")
        return 0
    
    news_items = analysis.get('news_items', [])
    saved = 0
    
    for item in news_items:
        success, status = save_news_item(comp_id, item)
        if success:
            saved += 1
            region = item.get('region', 'GLOBAL')
            print(f"      ✅ [{region}] {item.get('title', '')[:50]}...")
        elif status == "duplicate":
            print(f"      ⏭️  Duplicate: {item.get('title', '')[:40]}...")
        elif status == "pre_2024":
            print(f"      📅 Too old ({item.get('date', '?')}): {item.get('title', '')[:40]}...")
    
    return saved


def write_status(status, current_competitor=None, processed=0, total=0, error=None):
    """Write progress status to JSON file for Next.js API to read"""
    import time
    from datetime import datetime

    # Calculate progress
    percent_complete = 0
    if total > 0:
        percent_complete = int((processed / total) * 100)

    # Estimate remaining time (assuming ~15 seconds per competitor)
    estimated_seconds_remaining = (total - processed) * 15

    status_data = {
        'status': status,
        'current_competitor': current_competitor,
        'processed': processed,
        'total': total,
        'percent_complete': percent_complete,
        'estimated_seconds_remaining': estimated_seconds_remaining,
        'started_at': datetime.utcnow().isoformat() + 'Z' if status == 'running' and processed == 0 else None,
        'completed_at': datetime.utcnow().isoformat() + 'Z' if status == 'completed' else None,
        'error': error
    }

    # Write to public directory
    status_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'public', 'refresh_status.json')
    os.makedirs(os.path.dirname(status_path), exist_ok=True)

    with open(status_path, 'w') as f:
        json.dump(status_data, f, indent=2)
        f.flush()  # Ensure immediate write

    return status_data


def clear_all_news():
    """Clear all news"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM "CompetitorNews"')
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def fetch_all_news(limit=None, clean_start=False, regions=['global', 'brazil_pt', 'brazil_en', 'europe'], days=None):
    """Main function
    days: Only search for articles from the last N days. If None, auto-detects from last fetch.
    """
    print("=" * 60)
    print("🎯 CIMHSA COMPETITOR INTELLIGENCE FETCHER")
    print("   Powered by Serper.dev + Claude AI")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not found in .env")
        print("   Get your API key at https://console.anthropic.com")
        write_status('error', error='ANTHROPIC_API_KEY not found in .env')
        return 0

    if clean_start:
        deleted = clear_all_news()
        print(f"\n🧹 Cleared {deleted} news entries")

    # Determine date restriction for Serper searches
    date_restrict = None
    if days:
        date_restrict = f"d{days}"
        print(f"\n📅 Searching last {days} day(s) only")
    elif not clean_start:
        # Auto-detect: calculate days since last fetch
        last_fetch = get_last_fetch_date()
        if last_fetch:
            if isinstance(last_fetch, str):
                last_fetch = datetime.datetime.fromisoformat(last_fetch.replace('Z', '+00:00'))
            days_since = (datetime.datetime.now(datetime.timezone.utc) - last_fetch).days
            search_days = max(days_since + 1, 1)  # At least 1 day, +1 for overlap
            search_days = min(search_days, 14)  # Cap at 2 weeks
            date_restrict = f"d{search_days}"
            print(f"\n📅 Last fetch: {last_fetch.strftime('%b %d, %Y')} — searching last {search_days} day(s)")
        else:
            print(f"\n📅 First run — searching all available articles")

    # Pre-load all existing URLs for fast duplicate checking
    print("📦 Loading existing URLs from database...")
    existing_urls = get_all_existing_urls()
    print(f"   {len(existing_urls)} existing articles in DB")

    competitors = get_competitors()
    print(f"📋 Found {len(competitors)} competitors")
    print(f"🌍 Searching regions: {', '.join(regions)}")

    if limit:
        competitors = competitors[:limit]
        print(f"🎯 Processing {limit} competitors")

    total_competitors = len(competitors)
    total_news = 0

    # Write initial status
    write_status('running', current_competitor=None, processed=0, total=total_competitors)

    try:
        for i, comp in enumerate(competitors, 1):
            # Update status before processing each competitor
            write_status('running', current_competitor=comp['name'], processed=i-1, total=total_competitors)

            print(f"[{i}/{len(competitors)}]", end="")
            saved = fetch_news_for_competitor(comp, regions, existing_urls=existing_urls, date_restrict=date_restrict)
            total_news += saved

            # Update status after processing
            write_status('running', current_competitor=comp['name'], processed=i, total=total_competitors)

            # Rate limiting - Serper is fast but let's be nice
            if i < len(competitors):
                time.sleep(1)

        # Write completion status
        write_status('completed', processed=total_competitors, total=total_competitors)

        print("\n" + "=" * 60)
        print(f"✅ COMPLETE: Added {total_news} news items")
        print("=" * 60)

        return total_news

    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        write_status('error', error=str(e), processed=i-1, total=total_competitors)
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fetch competitor news using Serper.dev')
    parser.add_argument('--limit', type=int, help='Limit number of competitors')
    parser.add_argument('--skip', type=int, default=0, help='Skip first N competitors')
    parser.add_argument('--test', action='store_true', help='Test with 5 competitors')
    parser.add_argument('--clean', action='store_true', help='Clear all news first')
    parser.add_argument('--region', type=str, help='Specific region: global, brazil, europe, latam')
    parser.add_argument('--mena', action='store_true', help='Focus on Brazil region')
    parser.add_argument('--days', type=int, help='Only search last N days (e.g. --days 3)')
    args = parser.parse_args()
    
    # Determine regions to search
    regions = ['global', 'brazil_pt', 'brazil_en', 'europe']
    if args.region:
        regions = [args.region]
    elif args.mena:
        regions = ['brazil', 'global']
    
    if args.test:
        fetch_all_news(limit=5, clean_start=True, regions=regions, days=args.days)
    elif args.limit:
        fetch_all_news(limit=args.limit, clean_start=args.clean, regions=regions, days=args.days)
    else:
        fetch_all_news(clean_start=args.clean, regions=regions, days=args.days)