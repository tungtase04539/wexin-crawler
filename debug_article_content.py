
import sqlite3
from pathlib import Path

db_path = Path("data/articles.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

title_pattern = "%腾讯开源世界第一生图模型%"
cursor.execute("SELECT id, title, url, content, content_html FROM articles WHERE title LIKE ?", (title_pattern,))
row = cursor.fetchone()

if row:
    colnames = [d[0] for d in cursor.description]
    res = dict(zip(colnames, row))
    print(f"ID: {res['id']}")
    print(f"URL: {res['url']}")
    print(f"Content: {len(res['content']) if res['content'] else 0}")
    print(f"HTML: {len(res['content_html']) if res['content_html'] else 0}")
else:
    print("Article not found")

conn.close()
