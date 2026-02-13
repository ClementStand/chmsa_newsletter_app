import sqlite3
import json

DB_PATH = "prisma/dev.db"

def get_region_from_location(location):
    if not location:
        return 'Global'
    
    loc = location.lower()
    
    # MENA
    if any(x in loc for x in ['uae', 'dubai', 'abu dhabi', 'saudi', 'riyadh', 'qatar', 'doha', 'kuwait', 'bahrain', 'oman', 'egypt', 'cairo', 'morocco', 'jordan', 'middle east', 'mena']):
        return 'MENA'
    
    # Europe
    if any(x in loc for x in ['uk', 'united kingdom', 'germany', 'france', 'spain', 'italy', 'netherlands', 'sweden', 'norway', 'denmark', 'finland', 'berlin', 'london', 'paris', 'amsterdam', 'switzerland', 'poland', 'europe', 'austria', 'brussels']):
        return 'Europe'
        
    # North America
    if any(x in loc for x in ['usa', 'united states', 'canada', 'mexico', 'san diego', 'new york', 'toronto', 'los angeles', 'chicago', 'atlanta', 'austin', 'boston', 'vancouver']):
        return 'North America'
        
    # APAC
    if any(x in loc for x in ['china', 'japan', 'korea', 'singapore', 'hong kong', 'india', 'australia', 'sydney', 'melbourne', 'tokyo', 'shanghai', 'mumbai', 'asia', 'pacific']):
        return 'APAC'
        
    # South America
    if any(x in loc for x in ['brazil', 'argentina', 'chile', 'peru', 'colombia', 'sao paulo']):
        return 'South America'
        
    return 'Global'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all news
    cursor.execute("SELECT id, details, region FROM CompetitorNews")
    rows = cursor.fetchall()
    
    updated = 0
    
    for row in rows:
        try:
            current_region = row['region']
            if current_region:
                continue

            details = json.loads(row['details'])
            loc = details.get('location', '')
            
            # Check for primary_region in details first
            new_region = details.get('primary_region')
            
            if not new_region:
                new_region = get_region_from_location(loc)
            
            cursor.execute("UPDATE CompetitorNews SET region = ? WHERE id = ?", (new_region, row['id']))
            updated += 1
            print(f"Updated {row['id']}: {loc} -> {new_region}")
            
        except Exception as e:
            print(f"Error row {row['id']}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Migration complete. Updated {updated} records.")

if __name__ == "__main__":
    migrate()
