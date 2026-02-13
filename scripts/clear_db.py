
import sqlite3

DB_PATH = "prisma/dev.db"

def clear_news():
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Clearing CompetitorNews...")
    cursor.execute("DELETE FROM CompetitorNews")
    print(f"  Deleted {cursor.rowcount} rows")
    
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    clear_news()
