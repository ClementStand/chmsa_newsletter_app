
import sqlite3
from duckduckgo_search import DDGS
from urllib.parse import urlparse

DB_PATH = "prisma/dev.db"

def get_domain(url):
    try:
        return urlparse(url).netloc.replace('www.', '')
    except:
        return ""

def market_radar():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get known domains to exclude
    cursor.execute("SELECT website FROM Competitor")
    known_websites = {get_domain(row[0]) for row in cursor.fetchall()}
    
    # Get some key players to pivot search around
    cursor.execute("SELECT name, industry FROM Competitor WHERE status='Active' ORDER BY RANDOM() LIMIT 5")
    samples = cursor.fetchall()
    
    ddgs = DDGS()
    print("Scanning for new market entrants...")
    
    new_candidates = []
    
    # Blocklist for filtering
    BLOCKLIST = {'porn', 'xxx', 'sex', 'video', 'amateur', 'free', 'streaming', 'casino', 'gambling', 'dating'}
    
    # Sector mapping to get better search terms from the CSV categories
    def get_sector_keywords(category):
        if not category: return "Digital Wayfinding"
        cat = category.lower()
        if "kiosk" in cat: return "Interactive Kiosk Technology"
        if "mapping" in cat: return "Indoor Mapping Software"
        if "signage" in cat: return "Digital Signage CMS"
        if "positioning" in cat: return "Indoor Positioning System"
        if "mena" in cat: return "Digital Signage MENA"
        return "Digital Wayfinding Solution"

    for name, industry in samples:
        # Get specific sector terms
        sector = get_sector_keywords(industry)

        # Search query: Look for NEW things in this sector, not just competitors of X
        # We rotate between finding competitors and finding new startups
        queries = [
            f"top new {sector} startups 2024 2025",
            f"new {sector} companies",
            f"competitors of {name} {sector}"
        ]
        
        # Pick one query strategy per sample to mix it up
        import random
        query = random.choice(queries)
        print(f"  Radar Query: {query}")
        
        try:
            # IMPORTANT: safesearch="on" to avoid inappropriate content
            results = ddgs.text(keywords=query, region="wt-wt", safesearch="on", max_results=10)
            
            for res in results:
                url = res.get('href')
                title = res.get('title')
                body = res.get('body', '')
                domain = get_domain(url)
                
                if not domain: continue
                
                # Check blocklist
                content_text = (title + " " + body + " " + url).lower()
                if any(bad in content_text for bad in BLOCKLIST):
                    print(f"    Skipping blocked content: {domain}")
                    continue

                # Simple heuristic: if domain is not known and not a generic news site
                if domain not in known_websites:
                    # Let's verify if not already detected
                    cursor.execute("SELECT id FROM Competitor WHERE website LIKE ?", (f"%{domain}%",))
                    if not cursor.fetchone():
                        print(f"    Possible new competitor: {title} ({domain})")
                        
                        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        cursor.execute("""
                            INSERT INTO Competitor (name, website, status, industry, lastUpdated)
                            VALUES (?, ?, 'Detected', ?, ?)
                        """, (title[:50], url, sector, now_iso))
                        
                        known_websites.add(domain)
                        new_candidates.append(title)
                        
        except Exception as e:
            print(f"    Error: {e}")

    conn.commit()
    conn.close()
    if new_candidates:
        print(f"Radar detection complete. Found {len(new_candidates)} new candidates.")
    else:
        print("Radar complete. No new distinct candidates found.")

if __name__ == "__main__":
    market_radar()
