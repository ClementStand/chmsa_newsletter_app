"""
News Fetcher for CIMHSA Competitor Intelligence (Machine Manufacturing)
Uses Serper.dev (Google Search API) + Gemini + Claude AI for analysis
Target Markets: South America (Brazil, Argentina, Colombia, Chile) — primary
               Europe (Spain, Germany, France, Italy, UK) — secondary
               North America (USA, Mexico) + other markets
"""

import asyncio
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import hashlib
import httpx
import json
import os
import time
import uuid
import re
import requests
import anthropic
from google import genai as google_genai
from google.genai import types as genai_types
from dotenv import load_dotenv

# Load .env.local first, then .env as fallback
load_dotenv('.env.local')
load_dotenv()

# Configure APIs
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_gemini_client = google_genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Get database URL - prefer pooler connection, strip Prisma-specific params
_raw_db_url = os.getenv("DATABASE_URL") or os.getenv("DIRECT_URL")
DATABASE_URL = _raw_db_url.split('?')[0] if _raw_db_url else None  # Remove query params like ?pgbouncer=true

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Priority competitors (processed first — most likely to have news)
PRIORITY_COMPETITORS = [
    "Indústrias Romi", "Fagor Automation", "DMG Mori", "Mazak",
    "Haas Automation", "Trumpf", "Okuma", "Sandvik", "Makino", "Hermle",
]

# --- Serper API cache (file-based, 7-day TTL) ---
SERPER_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache', 'serper')
SERPER_CACHE_TTL = 7 * 24 * 3600  # 7 days in seconds

# Global semaphore for Serper rate limiting (initialized in async main)
SERPER_SEMAPHORE = None


def _serper_cache_key(query, region, search_type):
    raw = f"{query}|{region}|{search_type}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(query, region, search_type):
    key = _serper_cache_key(query, region, search_type)
    cache_file = os.path.join(SERPER_CACHE_DIR, f"{key}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                data = json.load(f)
            age = time.time() - data.get('cached_at', 0)
            if age < SERPER_CACHE_TTL:
                return data.get('results', [])
        except Exception:
            pass
    return None


def _cache_set(query, region, search_type, results):
    os.makedirs(SERPER_CACHE_DIR, exist_ok=True)
    key = _serper_cache_key(query, region, search_type)
    cache_file = os.path.join(SERPER_CACHE_DIR, f"{key}.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump({'cached_at': time.time(), 'results': results}, f)
    except Exception:
        pass

# --- Gemini search cache (file-based, 1-day TTL) ---
GEMINI_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache', 'gemini')
GEMINI_CACHE_TTL = 24 * 3600  # 1 day in seconds


def _gemini_cache_get(name):
    key = hashlib.md5(name.lower().encode()).hexdigest()
    path = os.path.join(GEMINI_CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            if time.time() - data.get('cached_at', 0) < GEMINI_CACHE_TTL:
                return data.get('results', [])
        except Exception:
            pass
    return None


def _gemini_cache_set(name, results):
    os.makedirs(GEMINI_CACHE_DIR, exist_ok=True)
    key = hashlib.md5(name.lower().encode()).hexdigest()
    path = os.path.join(GEMINI_CACHE_DIR, f"{key}.json")
    try:
        with open(path, 'w') as f:
            json.dump({'cached_at': time.time(), 'results': results}, f)
    except Exception:
        pass


def _parse_gemini_grounding(response):
    """Extract verified article URLs and summaries from Gemini text + grounding metadata.
    Uses grounding_supports to map text segments to the best source URL.
    """
    articles = []
    candidate = response.candidates[0] if response.candidates else None
    if not candidate:
        return articles
    
    # Get text and grounding
    text = ""
    if candidate.content and candidate.content.parts:
        text = candidate.content.parts[0].text or ""
    
    grounding = getattr(candidate, 'grounding_metadata', None)
    if not grounding:
        return articles

    chunks = getattr(grounding, 'grounding_chunks', []) or []
    supports = getattr(grounding, 'grounding_supports', []) or []
    
    # Map text lines to chunks via overlap with supports
    current_idx = 0
    lines = text.split('\n')
    
    processed_urls = set()

    for line in lines:
        line_len = len(line)
        start = current_idx
        end = current_idx + line_len
        current_idx = end + 1 # count the newline
        
        line_clean = line.strip()
        # Only process list items
        if not (line_clean.startswith('*') or line_clean.startswith('-')):
            continue
            
        # Find overlapping supports
        best_chunk_idx = -1
        max_score = 0.0
        
        for support in supports:
            seg = support.segment
            # Guard: segment or its indices can be None on some Gemini responses
            if seg is None or seg.start_index is None or seg.end_index is None:
                continue
            # Check overlap: start < seg.end and end > seg.start
            if max(start, seg.start_index) < min(end, seg.end_index):
                indices = support.grounding_chunk_indices
                scores = support.confidence_scores
                
                for idx, score in zip(indices, scores):
                    if score > max_score:
                         if 0 <= idx < len(chunks):
                             chunk = chunks[idx]
                             if hasattr(chunk, 'web') and chunk.web:
                                 uri = getattr(chunk.web, 'uri', None)
                                 # Skip if not news url
                                 if uri and is_news_url(uri):
                                     max_score = score
                                     best_chunk_idx = idx

        if best_chunk_idx != -1:
             chunk = chunks[best_chunk_idx]
             uri = getattr(chunk.web, 'uri', None)
             
             # Avoid adding same URL multiple times from same response
             if uri in processed_urls:
                 continue
             processed_urls.add(uri)

             title_source = getattr(chunk.web, 'title', None)
             
             # Clean snippet: remove markers
             snippet = re.sub(r'^[\*\-]\s*', '', line_clean)
             snippet = snippet.replace('**', '')
             
             # Use snippet as title if extracted title is missing or generic
             title = title_source if title_source else snippet[:100]

             articles.append({
                'title': title,
                'link': uri,
                'snippet': snippet,
                'date': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d'), 
                '_search_region': 'gemini_search'
            })

    return articles


def search_gemini(competitor_name, days_back=7):
    """Search for news using Gemini 2.0 Flash with Google Search grounding.
    """
    if not GEMINI_API_KEY or not _gemini_client:
        return []

    search_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()

    cached = _gemini_cache_get(search_name)
    if cached is not None:
        print(f"      [GEMINI-CACHED] {search_name}: {len(cached)} articles")
        return cached

    try:
        # CIMHSA SPECIFIC PROMPT: Machine Manufacturing
        prompt = (
            f"Search for recent news (last {days_back} days) about '{search_name}', a machine tool or industrial machinery manufacturer. "
            f"Focus on: new factory openings, major contract wins, government tenders, "
            f"partnerships, acquisitions, new CNC or automation product launches. "
            f"Prioritize news from South America (Brazil, Argentina, Colombia, Chile), "
            f"Europe (Spain, Germany, Italy, France), and North America (USA, Mexico). "
            f"Please provide a bulleted list of the articles you find, including their dates."
        )
        response = _gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
                temperature=1.0
            )
        )

        articles = _parse_gemini_grounding(response)
        print(f"      [GEMINI]  {search_name}: {len(articles)} articles found")
        _gemini_cache_set(search_name, articles)
        return articles

    except Exception as e:
        print(f"      Gemini search error: {e}")
        return []


# ---------------------------------------------------------------------------
# ASYNC SEARCH LAYER
# ---------------------------------------------------------------------------

async def search_serper_async(query, search_type='news', region='global', num_results=10, tbs_val=None):
    """Async version of search_serper()"""
    if isinstance(region, dict):
        region_config = region
        region_label = region.get('_label', f"{region.get('gl', '?')}_{region.get('hl', '?')}")
    else:
        region_config = REGIONS.get(region, REGIONS['global'])
        region_label = region

    cached = _cache_get(query, region_label, search_type)
    if cached is not None:
        print(f"      [CACHED] {region_label}: {query[:60]}")
        return cached

    if not SERPER_API_KEY:
        return []

    payload = {"q": query, "gl": region_config['gl'], "hl": region_config['hl'], "num": num_results}
    if tbs_val:
        payload["tbs"] = tbs_val

    try:
        global SERPER_SEMAPHORE
        if SERPER_SEMAPHORE is None:
             SERPER_SEMAPHORE = asyncio.Semaphore(3)
        
        async with SERPER_SEMAPHORE:
            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await http.post(
                    f"https://google.serper.dev/{search_type}",
                    json=payload,
                    headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
                )
        if response.status_code in (400, 403) and "credits" in response.text.lower():
            print("      ❌ Serper credits exhausted!")
            return []
        response.raise_for_status()
        data = response.json()
        results = data.get('news' if search_type == 'news' else 'organic', [])
        print(f"      [API]    {region_label}: {query[:60]}")
        _cache_set(query, region_label, search_type, results)
        return results
    except Exception as e:
        print(f"      Serper async error: {e}")
        return []


async def search_news_async(competitor_name, regions_to_search, days_back=None, native_region=None):
    """Async version — fires ALL (query × region) Serper combinations concurrently."""
    search_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()
    
    # CIMHSA SPECIFIC QUERIES: Machine Tool / Industrial Machinery (EN, ES, PT)
    # Positive: industry-specific terms that anchor results to manufacturing news.
    # Negative (-term): exclude sports/entertainment noise common in AR/ES regions.
    _neg = '-UEFA -"Euro Cup" -"Copa America" -Messi -"Champions League" -futebol -futbol'
    queries = [
        # English — global / US / Europe
        f'"{search_name}" ("machine tool" OR "CNC" OR "machining center" OR "laser fiber" OR "ISO 9001" OR "industrial machinery") {_neg}',
        f'"{search_name}" (contract OR acquisition OR "factory expansion" OR "fleet expansion" OR investment) {_neg}',
        # Spanish — Argentina, Colombia, Mexico, Spain
        f'"{search_name}" ("máquina herramienta" OR "mecanizado" OR "maquinaria" OR "automatización" OR "fibra láser") {_neg}',
        f'"{search_name}" (contrato OR licitación OR adquisición OR fábrica OR inversión) {_neg}',
        # Portuguese — Brazil
        f'"{search_name}" ("máquina ferramenta" OR "usinagem" OR "mecanizado" OR "automação" OR "fibra laser" OR "frota") {_neg}',
        f'"{search_name}" (contrato OR licitação OR aquisição OR investimento OR expansão OR frota) {_neg}',
        # Technical niche — catches equipment-specific updates (CNC, laser, injection moulding)
        f'"{search_name}" (CNC OR "laser de fibra" OR "3D laser" OR injetoras OR "ISO 9001" OR "certificação") {_neg}',
        f'"{search_name}" (frota OR usinagem OR mecanizado OR "laser de fibra" OR "corte a laser") {_neg}',
    ]

    # Build all (query, region) task pairs
    task_pairs = []
    for region in regions_to_search:
        for query in queries:
            task_pairs.append((region, query))
    if native_region:
        for query in queries:
            task_pairs.append((native_region, query))

    tasks = [search_serper_async(q, 'news', r, 10) for r, q in task_pairs]
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls = set()
    all_results = []
    filtered = 0
    for (region_key, _), result in zip(task_pairs, results_lists):
        if isinstance(result, Exception):
            continue
        for r in result:
            url = r.get('link', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                if is_news_url(url):
                    label = region_key if isinstance(region_key, str) else region_key.get('_label', 'native')
                    r['_search_region'] = label
                    all_results.append(r)
                else:
                    filtered += 1
    if filtered > 0:
        print(f" ({filtered} filtered)", end="")
    return all_results


async def search_gemini_async(competitor_name, days_back=7):
    """Async Gemini search with per-call jitter."""
    if not GEMINI_API_KEY or not _gemini_client:
        return []

    search_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()

    cached = _gemini_cache_get(search_name)
    if cached is not None:
        print(f"      [GEMINI-CACHED] {search_name}: {len(cached)} articles")
        return cached

    await asyncio.sleep(random.uniform(1.0, 3.0))

    try:
        # CIMHSA SPECIFIC PROMPT
        prompt = (
            f"Search for recent news (last {days_back} days) about '{search_name}', a machine tool or industrial machinery manufacturer. "
            f"Focus on: new factory openings, major contract wins, government tenders, "
            f"partnerships, acquisitions, new CNC or automation product launches. "
            f"Prioritize news from South America (Brazil, Argentina, Colombia, Chile), "
            f"Europe (Spain, Germany, Italy, France), and North America (USA, Mexico). "
            f"Please provide a bulleted list of the articles you find, including their dates."
        )
        response = await _gemini_client.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
            )
        )
        articles = _parse_gemini_grounding(response)
        print(f"      [GEMINI]  {search_name}: {len(articles)} articles found")
        _gemini_cache_set(search_name, articles)
        return articles

    except Exception as e:
        if '429' in str(e):
            print(f"      [GEMINI] Rate limited ({search_name}) — skipping")
        else:
            print(f"      Gemini async error: {e}")
        return []


async def search_gemini_deep_async(competitor_name, website, days_back=7):
    """Deep site-specific Gemini search."""
    if not GEMINI_API_KEY or not _gemini_client or not website:
        return []

    search_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()
    domain = re.sub(r'^https?://', '', website).rstrip('/')

    await asyncio.sleep(random.uniform(1.5, 3.0))

    try:
        prompt = (
            f"Find any press releases, news announcements, or blog posts from or about "
            f"'{search_name}' (website: {domain}) published in the last {days_back} days. "
            f"Also search trade publications (Metal Working News, Modern Machine Shop, "
            f"Metalurgia e Mecânica, Maquinas e Metais, Interempresas Metalmecanica) "
            f"and industry blogs for any coverage of {search_name} in the machine tool / "
            f"industrial machinery sector. "
            f"Please provide a bulleted list of the articles you find, including their dates."
        )
        response = await _gemini_client.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
            )
        )
        articles = _parse_gemini_grounding(response)
        if articles:
            print(f"      [GEMINI-DEEP] {search_name}: {len(articles)} articles found")
        return articles

    except Exception as e:
        if '429' not in str(e):
            print(f"      Gemini deep search error: {e}")
        return []


# CIMHSA TARGET REGIONS
# Primary: South America | Secondary: Europe | Other: North America + global
REGIONS = {
    'global':    {'gl': 'us', 'hl': 'en', '_label': 'global'},
    'brazil':    {'gl': 'br', 'hl': 'pt', '_label': 'brazil_pt'},
    'argentina': {'gl': 'ar', 'hl': 'es', '_label': 'argentina_es'},
    'europe':    {'gl': 'gb', 'hl': 'en', '_label': 'europe_en'},   # UK as English-language Europe proxy
    'spain':     {'gl': 'es', 'hl': 'es', '_label': 'spain_es'},
    'us':        {'gl': 'us', 'hl': 'en', '_label': 'us_en'},
    'mexico':    {'gl': 'mx', 'hl': 'es', '_label': 'mexico_es'},
    'colombia':  {'gl': 'co', 'hl': 'es', '_label': 'colombia_es'},
}

# English-speaking HQ — no native-language search needed
ENGLISH_SPEAKING_HQ = {'uk', 'usa', 'canada', 'australia', 'ireland', 'new zealand', 'singapore'}

# Native language search configs keyed by lowercase country name
HQ_NATIVE_REGIONS = {
    # South America (primary markets)
    'brazil':       {'gl': 'br', 'hl': 'pt', '_label': 'brazil_pt'},
    'argentina':    {'gl': 'ar', 'hl': 'es', '_label': 'argentina_es'},
    'colombia':     {'gl': 'co', 'hl': 'es', '_label': 'colombia_es'},
    'chile':        {'gl': 'cl', 'hl': 'es', '_label': 'chile_es'},
    'peru':         {'gl': 'pe', 'hl': 'es', '_label': 'peru_es'},
    'venezuela':    {'gl': 've', 'hl': 'es', '_label': 'venezuela_es'},
    # North America / LATAM
    'mexico':       {'gl': 'mx', 'hl': 'es', '_label': 'mexico_es'},
    # Europe (secondary markets)
    'spain':        {'gl': 'es', 'hl': 'es', '_label': 'spain_es'},
    'germany':      {'gl': 'de', 'hl': 'de', '_label': 'germany_de'},
    'france':       {'gl': 'fr', 'hl': 'fr', '_label': 'france_fr'},
    'italy':        {'gl': 'it', 'hl': 'it', '_label': 'italy_it'},
    'netherlands':  {'gl': 'nl', 'hl': 'nl', '_label': 'netherlands_nl'},
    'sweden':       {'gl': 'se', 'hl': 'sv', '_label': 'sweden_sv'},
    'switzerland':  {'gl': 'ch', 'hl': 'de', '_label': 'switzerland_de'},
    'poland':       {'gl': 'pl', 'hl': 'pl', '_label': 'poland_pl'},
    # APAC (other)
    'japan':        {'gl': 'jp', 'hl': 'ja', '_label': 'japan_ja'},
    'china':        {'gl': 'cn', 'hl': 'zh-cn', '_label': 'china_zh'},
    'south korea':  {'gl': 'kr', 'hl': 'ko', '_label': 'korea_ko'},
    'korea':        {'gl': 'kr', 'hl': 'ko', '_label': 'korea_ko'},
}

def get_native_region(headquarters):
    """Return native language search config for a non-English-speaking HQ, or None."""
    if not headquarters:
        return None
    hq_lower = headquarters.lower()
    for eng in ENGLISH_SPEAKING_HQ:
        if eng in hq_lower:
            return None
    for country, config in HQ_NATIVE_REGIONS.items():
        if country in hq_lower:
            return config
    return None

# URLs that indicate non-news content
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


ANALYSIS_PROMPT = """You are a competitive intelligence analyst for CIMHSA, a Brazilian manufacturer of CNC machine tools, industrial machinery, and automation solutions.

I found these search results about {competitor_name}:

{articles}

CONTEXT:
Today is {today_date}.
{date_instruction}

IMPORTANT: Articles may be in Portuguese, Spanish, or English. Analyze ALL articles regardless of language. Always output your title and summary in ENGLISH.

For articles where 'Region Found' contains "GEMINI": Be more lenient. Include minor updates, blog posts, and general company activity unless completely irrelevant (spam/ads).

Your job is to find REAL NEWS EVENTS only. Include:
- New factory/plant openings or expansions (especially in South America or Europe)
- New contracts, tenders won (Government, Construction, Agriculture, Industry)
- Mergers, Acquisitions, Joint Ventures
- New product launches (CNC machines, heavy machinery, automation, tooling)
- Trade show appearances with new products (FEIMEC, EMO, JIMTOF, IMTS, etc.)
- Financial results, funding rounds, large investments
- Leadership changes (CEO, Country Manager, Regional Director)
- Market expansions into new countries or regions

STRICTLY EXCLUDE (these are NOT news):
- Product catalog pages or sales listings (MercadoLibre, OLX, Alibaba, etc.)
- Generic company profile descriptions ("Company X manufactures machines...")
- Job postings or career pages
- Social media posts without real news content
- "About us" or company overview pages
- Articles about a different company with a similar name (verify industry context)
- Price lists or quotation pages
- ANY sports/football/soccer content (UEFA, Copa América, Champions League, Messi, etc.) — these appear in Argentine and Spanish search results and are NEVER relevant.

If NONE of the articles contain real news events, respond with: {{"no_relevant_news": true}}

Otherwise, return JSON:

{{
  "news_items": [
    {{
      "event_type": "New Project" | "Investment" | "Product Launch" | "Partnership" | "Leadership Change" | "Market Expansion" | "Financial Performance" | "Other",
      "category": "Product" | "Expansion" | "Pricing" | "General",
      "title": "Clear headline in ENGLISH (max 100 chars)",
      "summary": "2-3 sentence summary in ENGLISH (max 500 chars). Focus on the 'So What?' for a competitor analysis.",
      "threat_level": 1-5,
      "date": "YYYY-MM-DD",
      "source_url": "The actual URL from the article",
      "region": "SOUTH_AMERICA" | "NORTH_AMERICA" | "EUROPE" | "APAC" | "GLOBAL",
      "details": {{
        "location": "City, Country or null",
        "financial_value": "Amount or null",
        "partners": ["Companies"],
        "products": ["Products"]
      }}
    }}
  ]
}}

Category Guide:
- "Product": New product/feature/machine launches
- "Expansion": New contracts, new markets, new factories, partnerships, deployments
- "Pricing": Funding rounds, revenue news, financial results, investments
- "General": Leadership changes, trade show appearances, other

Threat Level Guide:
- 1: Routine news, minimal impact
- 2: Minor development, worth monitoring
- 3: Moderate competitive move
- 4: Significant threat (e.g. new factory in Brazil/Argentina, major EU contract)
- 5: CRITICAL: Competitor winning a massive government tender in South America, or acquiring a key regional distributor.

CRITICAL: Assign highest threat levels (4-5) for news in SOUTH AMERICA (Brazil, Argentina, Colombia, Chile) and EUROPE (Spain, Germany, Italy).
Assign threat level 3-4 for significant moves in NORTH AMERICA (USA, Mexico).

DATE EXTRACTION INSTRUCTIONS:
- Use the EXACT "Published Date" provided.
- If no date is found, use the current date.
- Return ONLY valid JSON."""


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
    try:
        text = text.encode('ascii', 'ignore').decode('ascii')
    except:
        pass
    return text.strip()


def generate_cuid():
    return 'c' + uuid.uuid4().hex[:24]


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_competitors():
    """Fetch competitors from database, sorted by priority"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, website, industry, region, headquarters
        FROM "Competitor"
        WHERE status = 'active' OR status IS NULL
    """)
    all_competitors = cursor.fetchall()
    conn.close()

    def sort_key(c):
        name = c['name']
        if name in PRIORITY_COMPETITORS:
            return (0, PRIORITY_COMPETITORS.index(name))
        else:
            return (1, name)

    return sorted(all_competitors, key=sort_key)


def check_existing_url(cursor, url):
    """Check if URL already exists in database"""
    cursor.execute('SELECT id FROM "CompetitorNews" WHERE "sourceUrl" = %s', (url,))
    return cursor.fetchone() is not None


def save_news_item(competitor_id, news_item, days_back=None):
    """Save news item to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    source_url = sanitize_text(news_item.get('source_url', ''))
    
    if not source_url or 'example.com' in source_url:
        conn.close()
        return False, "invalid_url"
    
    if check_existing_url(cursor, source_url):
        conn.close()
        return False, "duplicate_url"

    title_check = sanitize_text(news_item.get('title', 'Untitled'))[:200]
    cursor.execute('SELECT id FROM "CompetitorNews" WHERE "competitorId" = %s AND "title" = %s', (competitor_id, title_check))
    if cursor.fetchone():
        conn.close()
        return False, "duplicate_title"
    
    try:
        news_id = generate_cuid()
        now = datetime.datetime.now(datetime.timezone.utc)
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

        if news_date > now:
            news_date = now

        news_date_str = news_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        # Dynamic cutoff: honour --days argument so a "420 day" run keeps 2024 articles.
        # Industrial sales cycles are 12-24 months so we never cut off more aggressively
        # than 18 months even when no explicit --days is given.
        if days_back and days_back > 0:
            cutoff = now - datetime.timedelta(days=days_back)
        else:
            cutoff = now - datetime.timedelta(days=548)  # 18-month default

        if news_date < cutoff:
            # Special case: Gemini sometimes returns a clearly bogus date (year < 2023)
            # because the grounding date extraction failed.  Re-anchor those to today
            # rather than discarding potentially valid niche content.
            if news_item.get('_search_region') == 'gemini_search' and news_date.year < 2023:
                news_date = now
                news_date_str = news_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            else:
                # Cutoff applies to every article — Gemini included.
                conn.close()
                print(f" [Skip: older than {cutoff.strftime('%Y-%m-%d')} ({news_date.strftime('%Y-%m-%d')})]", end="")
                return False, "too_old"
        
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
        category = news_item.get('category', '')
        if category:
            clean_details['category'] = sanitize_text(category)
        details_json = json.dumps(clean_details)
        
        cursor.execute("""
            INSERT INTO "CompetitorNews" (
                id, "competitorId", "eventType", date, title, summary,
                "threatLevel", details, "sourceUrl", "isRead", "isStarred", "extractedAt", region
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            news_id, competitor_id, event_type, news_date_str, title, summary,
            threat_level, details_json, source_url, False, False, iso_now_str, region
        ))
        
        conn.commit()
        conn.close()
        return True, "saved"
        
    except Exception as e:
        conn.close()
        return False, str(e)


def get_last_fetch_date():
    """Get the date of the most recent news item in the DB"""
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
    """Fetch all existing source URLs from DB"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT "sourceUrl" FROM "CompetitorNews"')
    urls = {row['sourceUrl'] for row in cursor.fetchall()}
    conn.close()
    return urls


def write_status(status, current_competitor=None, processed=0, total=0, error=None):
    """Write progress status to JSON file for Next.js API to read"""
    percent_complete = int((processed / total) * 100) if total > 0 else 0
    estimated_seconds_remaining = (total - processed) * 20  # ~20s per competitor (async is faster)

    status_data = {
        'status': status,
        'current_competitor': current_competitor,
        'processed': processed,
        'total': total,
        'percent_complete': percent_complete,
        'estimated_seconds_remaining': estimated_seconds_remaining,
        'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat() if status == 'running' and processed == 0 else None,
        'completed_at': datetime.datetime.now(datetime.timezone.utc).isoformat() if status == 'completed' else None,
        'error': error
    }

    status_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'public', 'refresh_status.json')
    os.makedirs(os.path.dirname(status_path), exist_ok=True)

    with open(status_path, 'w') as f:
        json.dump(status_data, f, indent=2)
        f.flush()

    return status_data


async def gather_all_articles(competitor, days_back, regions):
    """Run Serper + Gemini in parallel."""
    name = competitor['name']
    headquarters = competitor.get('headquarters') or ''
    website = competitor.get('website') or ''
    native_region = get_native_region(headquarters)

    serper_task = search_news_async(name, regions, days_back=days_back, native_region=native_region)
    gemini_task = search_gemini_async(name, days_back=days_back or 7)
    deep_task = None
    if website:
        deep_task = search_gemini_deep_async(name, website, days_back=days_back or 14)

    results = await asyncio.gather(
        serper_task, gemini_task, deep_task if deep_task else asyncio.sleep(0),
        return_exceptions=True
    )
    
    serper_results = results[0]
    gemini_results = results[1]
    deep_results = results[2] if deep_task else []

    if isinstance(serper_results, Exception):
        print(f"      [Serper error] {serper_results}")
        serper_results = []
    if isinstance(gemini_results, Exception):
        print(f"      [Gemini error] {gemini_results}")
        gemini_results = []
    if isinstance(deep_results, Exception):
        print(f"      [Gemini-deep error] {deep_results}")
        deep_results = []

    # Merge deep results — use .get() so a missing 'link' key never crashes the batch
    if deep_results:
        try:
            deep_urls = {a.get('link', '') for a in gemini_results}
            for a in deep_results:
                if a.get('link', '') and a.get('link') not in deep_urls:
                    gemini_results.append(a)
        except Exception as e:
            print(f"      [deep merge error] {e}")

    seen = set()
    merged = []
    for a in serper_results + gemini_results:
        url = a.get('link', '')
        if url and url not in seen:
            seen.add(url)
            merged.append(a)
    return merged


async def analyze_with_claude_async(competitor_name, articles, days_back=None):
    """Async Claude analysis."""
    if not articles or not ANTHROPIC_API_KEY:
        return None

    BATCH_SIZE = 12
    all_news_items = []
    async_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

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
            articles_text += f"\n---\nArticle {i}:\nTitle: {title}\nPublished Date: {date}\nURL: {url}\nRegion Found: {region}\nContent: {snippet[:500]}\n---\n"

        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        date_instr = ""
        if days_back:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days_back)
            date_instr = f"CRITICAL: IGNORE any news events that occurred before {cutoff.strftime('%Y-%m-%d')}. Only include news from the last {days_back} days."

        prompt = ANALYSIS_PROMPT.format(
            competitor_name=competitor_name,
            articles=articles_text,
            today_date=today_str,
            date_instruction=date_instr
        )

        for attempt in range(3):
            try:
                message = await async_client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=8000,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = message.content[0].text.strip()

                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                response_text = response_text.strip()

                result = None
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError:
                    m = re.search(r'\{[\s\S]*\}', response_text)
                    if m:
                        try:
                            result = json.loads(m.group())
                        except: pass

                if result is None:
                    if attempt < 2: continue
                    break

                if not result.get('no_relevant_news'):
                    items = result.get('news_items', [])
                    url_map = {a.get('link', ''): a.get('_search_region') for a in batch}
                    for item in items:
                        src = item.get('source_url', '')
                        if src in url_map:
                            item['_search_region'] = url_map[src]
                    all_news_items.extend(items)
                break

            except Exception:
                if attempt < 2: await asyncio.sleep(1)

        if batch_start + BATCH_SIZE < len(articles):
            await asyncio.sleep(0.5)

    return {'news_items': all_news_items} if all_news_items else {'no_relevant_news': True}


async def fetch_news_for_competitor_async(competitor, regions, existing_urls=None, days_back=None):
    """Async fetch for one competitor."""
    name = competitor['name']
    headquarters = competitor.get('headquarters') or ''
    industry = (competitor.get('industry') or '').lower()
    native_region = get_native_region(headquarters)

    # Industrial/machinery moves stay relevant for 12-18 months — extend the save cutoff
    # regardless of how many days the Serper search window covers.
    _industrial_keywords = ('machinery', 'industrial', 'manufactur', 'fabricat', 'equipment', 'cnc')
    if any(k in industry for k in _industrial_keywords):
        effective_days_back = max(days_back or 0, 540)  # at least 18 months
    else:
        effective_days_back = days_back

    if native_region:
        print(f"\n  🔍 {name} [{native_region['_label']}]", end="")
    else:
        print(f"\n  🔍 {name}", end="")

    articles = await gather_all_articles(competitor, days_back, regions)

    if not articles:
        print(" — no articles")
        return 0

    if existing_urls:
        new_articles = [a for a in articles if a.get('link', '') not in existing_urls]
        skipped = len(articles) - len(new_articles)
        if skipped > 0:
            print(f" — {len(articles)} found, {skipped} known", end="")
        if not new_articles:
            print(" — all known, skip")
            return 0
        articles = new_articles

    print(f" — {len(articles)} new...", end="")

    analysis = await analyze_with_claude_async(name, articles, days_back=days_back)

    if not analysis or analysis.get('no_relevant_news'):
        return 0

    news_items = analysis.get('news_items', [])
    saved = 0
    for item in news_items:
        success, status = await asyncio.to_thread(save_news_item, competitor['id'], item, effective_days_back)
        if success:
            saved += 1
        else:
            print(f" [Skip: {status}]", end="")

    if saved > 0:
        print(f" ✅ Saved {saved}", end="")
    else:
        print(f" (0 saved)", end="")
    return saved


async def _fetch_all_news_async_inner(limit=None, clean_start=False, regions=None, days=None, competitor_name=None):
    """Fetch all news async."""
    print("=" * 60)
    print("🎯 CIMHSA COMPETITOR INTELLIGENCE FETCHER")
    print("   Powered by Serper.dev + Gemini + Claude AI")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("\n❌ ANTHROPIC_API_KEY missing")
        write_status('error', error='ANTHROPIC_API_KEY not found in .env')
        return 0

    # Default region order: South America first, then Europe, then US/Mexico
    if regions is None:
        regions = ['global', 'brazil', 'argentina', 'europe', 'spain', 'us', 'mexico']

    if clean_start:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM "CompetitorNews"')
        conn.commit()
        conn.close()
        print(f"\n🧹 Cleared DB")

    # Determine search window
    search_days = days
    if not search_days:
        if not clean_start:
            last_fetch = await asyncio.to_thread(get_last_fetch_date)
            if last_fetch:
                if isinstance(last_fetch, str):
                    last_fetch = datetime.datetime.fromisoformat(last_fetch.replace('Z', '+00:00'))
                days_since = (datetime.datetime.now(datetime.timezone.utc) - last_fetch).days
                search_days = max(days_since + 1, 1)
                search_days = min(search_days, 14)  # Cap at 2 weeks
                print(f"\n📅 Last fetch: {last_fetch.strftime('%b %d, %Y')} — searching last {search_days} day(s)")
            else:
                search_days = 30
                print(f"\n📅 First run — searching last {search_days} days")
        else:
            search_days = 30
            print(f"\n📅 Clean start — searching last {search_days} days")
    else:
        print(f"\n📅 Searching last {search_days} day(s)")

    print(f"🌍 Regions: {', '.join(regions)}")
    print("📦 Loading existing URLs...")
    existing_urls = await asyncio.to_thread(get_all_existing_urls)
    print(f"   {len(existing_urls)} articles already in DB")

    competitors = await asyncio.to_thread(get_competitors)

    if competitor_name:
        competitors = [c for c in competitors if competitor_name.lower() in c['name'].lower()]

    if limit:
        competitors = competitors[:limit]

    total_competitors = len(competitors)
    print(f"📋 Found {total_competitors} competitors")

    write_status('running', current_competitor=None, processed=0, total=total_competitors)

    BATCH_SIZE = 5
    total_news = 0
    processed = 0

    try:
        for batch_start in range(0, total_competitors, BATCH_SIZE):
            batch = competitors[batch_start:batch_start + BATCH_SIZE]

            for comp in batch:
                write_status('running', current_competitor=comp['name'], processed=processed, total=total_competitors)

            tasks = [
                fetch_news_for_competitor_async(c, regions, existing_urls=existing_urls, days_back=search_days)
                for c in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, int):
                    total_news += result
                processed += 1
                write_status('running', current_competitor=batch[i]['name'], processed=processed, total=total_competitors)

            if batch_start + BATCH_SIZE < total_competitors:
                await asyncio.sleep(random.uniform(3.0, 5.0))

        write_status('completed', processed=total_competitors, total=total_competitors)
        print("\n" + "=" * 60)
        print(f"✅ COMPLETE: {total_news} items added")
        print("=" * 60)

    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        write_status('error', error=str(e), processed=processed, total=total_competitors)
        raise

    return total_news


def fetch_all_news(limit=None, clean_start=False, regions=None, days=None, competitor_name=None):
    """Sync wrapper."""
    return asyncio.run(_fetch_all_news_async_inner(limit, clean_start, regions, days, competitor_name))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fetch competitor news for CIMHSA using Serper.dev + Gemini + Claude AI')
    parser.add_argument('--limit', type=int, help='Limit number of competitors processed')
    parser.add_argument('--skip', type=int, default=0, help='Skip first N competitors')
    parser.add_argument('--test', action='store_true', help='Quick test: process 3 competitors with clean start')
    parser.add_argument('--clean', action='store_true', help='Clear all existing news before fetching')
    parser.add_argument('--days', type=int, help='Only search last N days (e.g. --days 7)')
    parser.add_argument('--competitor', type=str, help='Filter to a specific competitor name')
    parser.add_argument('--region', type=str, help='Override regions (comma-separated, e.g. brazil,argentina,europe)')
    args = parser.parse_args()

    # Build regions list
    regions = None
    if args.region:
        regions = [r.strip() for r in args.region.split(',')]

    if args.test:
        fetch_all_news(limit=3, clean_start=True, regions=regions, days=args.days or 14)
    elif args.limit:
        fetch_all_news(limit=args.limit, clean_start=args.clean, regions=regions, days=args.days, competitor_name=args.competitor)
    else:
        fetch_all_news(clean_start=args.clean, regions=regions, days=args.days, competitor_name=args.competitor)
