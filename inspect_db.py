import sqlite3
import os

db_path = 'data/articles.db'
if not os.path.exists(db_path):
    print(f"Database {db_path} not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check schema
    cursor.execute("PRAGMA table_info(articles)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"Columns: {columns}")
    
    # Check data
    cursor.execute("SELECT id, is_simulated FROM articles LIMIT 20")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID:{row[0]},SIM:{row[1]}")
    
    conn.close()
