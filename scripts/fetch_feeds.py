import sqlite3
import feedparser
from dateutil import parser as date_parser
import datetime
import urllib.parse
from ddgs import DDGS
import time

DB_PATH = "prisma/dev.db"

def fetch_feeds():
    print("Starting Hybrid Intelligence Sync (RSS + Search)...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all competitors
    cursor.execute("SELECT id, name, rssUrl, website FROM Competitor")
    competitors = cursor.fetchall()

    print(f"Processing {len(competitors)} competitors...")

    ddgs = DDGS()
    total_new_articles = 0

    for comp_id, name, rss_url, website in competitors:
        print(f"\nProcessing: {name}")
        articles_found = 0
        
        # STRATEGY 1: RSS Feed (Prioritized)
        if rss_url:
            try:
                print(f"  Attempting RSS: {rss_url}")
                feed = feedparser.parse(rss_url, agent="Mozilla/5.0")
                if not feed.entries:
                    print("  RSS empty or blocked.")
                
                for entry in feed.entries:
                    title = entry.get('title', 'No Title')
                    link = entry.get('link', '')
                    snippet = entry.get('summary', '') or entry.get('description', '')
                    
                    # Date parsing
                    published_at_str = entry.get('published', '') or entry.get('updated', '')
                    try:
                        if published_at_str:
                            dt = date_parser.parse(published_at_str)
                            if dt.tzinfo is None: dt = dt.replace(tzinfo=datetime.timezone.utc)
                            published_at = dt.isoformat()
                        else:
                            published_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    except:
                        published_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

                    if not link: continue

                    if save_article(cursor, title, link, published_at, snippet[:500], comp_id):
                        articles_found += 1
                        
            except Exception as e:
                print(f"  RSS Error: {e}")

        # STRATEGY 2: Bing News RSS (Fallback)
        # If RSS yielded < 2 articles, or no RSS, run Bing RSS Search.
        if articles_found < 2:
            print("  Running Bing RSS Fallback...")
            # Use strict search for company name or domain
            raw_query = f'"{name}" OR site:{get_domain(website)}'
            encoded_query = urllib.parse.quote_plus(raw_query)
            bing_url = f"https://www.bing.com/news/search?q={encoded_query}&format=rss"
            
            try:
                # Add User-Agent is critical for Bing
                feed = feedparser.parse(bing_url, agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                if not feed.entries:
                     print("  Bing RSS empty.")

                for entry in feed.entries:
                    title = entry.get('title', 'No Title')
                    link = entry.get('link', '')
                    snippet = entry.get('summary', '') or entry.get('description', '')
                    
                    # Bing often puts the source in the title or description, let's keep it simple
                    
                    # Date parsing
                    published_at_str = entry.get('published', '') or entry.get('updated', '')
                    try:
                         if published_at_str:
                            dt = date_parser.parse(published_at_str)
                            if dt.tzinfo is None: dt = dt.replace(tzinfo=datetime.timezone.utc)
                            published_at = dt.isoformat()
                         else:
                            published_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    except:
                         published_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

                    if not link: continue
                    
                    # Dedup check (redundant with SQL but saves processing)
                    
                    if save_article(cursor, title, link, published_at, snippet[:500], comp_id):
                        articles_found += 1

            except Exception as e:
                print(f"  Bing RSS Error: {e}")

        # STRATEGY 3: Deep Signal Search (Hiring, Projects, Investing)
        # If no standard news found, look for specific non-news signals.
        if articles_found == 0:
            print("  Running Deep Signal Search...")
            
            # Use broader queries to catch signals on external sites (LinkedIn, Glassdoor, News)
            # as proved by debug script. Strict site: search was too limiting.
            signal_queries = [
                (f'"{name}" "hiring" OR "jobs" OR "careers" -site:linkedin.com/jobs', "Hiring Signal"),
                (f'"{name}" "investment" OR "funding" OR "contract" OR "new project" -crypto', "Growth Signal")
            ]
            
            for query, label in signal_queries:
                try:
                    # Use ddgs web search (not news) with time limit
                    # Fixed: Use positional argument for query
                    results = ddgs.text(query, max_results=1, timelimit="y")
                    if not results: continue

                    for res in results:
                         title = f"{label}: {res.get('title')}"
                         link = res.get('href', '')
                         snippet = res.get('body', '')
                         
                         # Dedup
                         published_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
                         
                         if save_article(cursor, title, link, published_at, snippet[:500], comp_id):
                             articles_found += 1
                except Exception as e:
                    # print(f"  Signal Error ({label}): {e}")
                    pass

        # STRATEGY 4: Monitoring Fallback (Last Resort)
        if articles_found == 0:
             print("  No signals found. Inserting monitoring placeholder...")
             title = f"Monitoring: {name}"
             link = f"{website}#monitoring" 
             snippet = f"We are actively tracking {name} for new updates. No specific news articles were detected in the last cycle. Click to visit their official site."
             published_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
             save_article(cursor, title, link, published_at, snippet, comp_id)

        print(f"  Total new: {articles_found}")
        total_new_articles += articles_found

    conn.commit()
    conn.close()
    print(f"\nSync Complete. Total new articles: {total_new_articles}")

def get_domain(url):
    try:
        from urllib.parse import urlparse
        if "://" not in url: url = "http://" + url
        return urlparse(url).netloc.replace('www.', '')
    except:
        return ""

def save_article(cursor, title, link, published_at, snippet, comp_id):
    try:
        cursor.execute("""
            INSERT INTO Article (title, link, publishedAt, snippet, competitorId, isRead)
            VALUES (?, ?, ?, ?, ?, 0)
            ON CONFLICT(link) DO NOTHING
        """, (title, link, published_at, snippet, comp_id))
        return cursor.rowcount > 0
    except Exception as e:
        return False

if __name__ == "__main__":
    fetch_feeds()
