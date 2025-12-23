
import sqlite3
from pathlib import Path

db_path = Path("data/articles.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(articles)")
columns = cursor.fetchall()
for col in columns:
    print(col[1])

conn.close()
