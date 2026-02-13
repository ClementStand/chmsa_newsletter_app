
import sqlite3

DB_PATH = "prisma/dev.db"

def fix_booleans():
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fix isRead
    print("Fixing isRead column...")
    cursor.execute("UPDATE CompetitorNews SET isRead = 0 WHERE isRead != 1 AND isRead != 0")
    print(f"  Fixed {cursor.rowcount} rows in isRead")

    # Fix isStarred
    print("Fixing isStarred column...")
    cursor.execute("UPDATE CompetitorNews SET isStarred = 0 WHERE isStarred != 1 AND isStarred != 0")
    print(f"  Fixed {cursor.rowcount} rows in isStarred")
    
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    fix_booleans()
