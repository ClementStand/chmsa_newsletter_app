
import sqlite3

DB_PATH = "prisma/dev.db"

def inspect_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- RAW DATA INSPECTION ---")
    cursor.execute("SELECT id, date, extractedAt, isRead FROM CompetitorNews LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]}")
        print(f"  date: '{row[1]}'")
        print(f"  extractedAt: '{row[2]}'")
        print(f"  isRead: {row[3]} (Type: {type(row[3])})")
        print("-" * 20)
        
    conn.close()

if __name__ == "__main__":
    inspect_db()
