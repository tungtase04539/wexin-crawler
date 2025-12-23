
import sqlite3
from pathlib import Path

db_path = Path("data/articles.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Convert data-src to src
cursor.execute("UPDATE articles SET content_html = REPLACE(content_html, 'data-src=', 'src=')")

# 2. Inject meta referrer if not present
cursor.execute("SELECT id, content_html FROM articles")
rows = cursor.fetchall()
updated_count = 0

for article_id, html in rows:
    if html and '<meta name="referrer" content="no-referrer">' not in html:
        # Prepend to the HTML
        new_html = '<meta name="referrer" content="no-referrer">' + html
        cursor.execute("UPDATE articles SET content_html = ? WHERE id = ?", (new_html, article_id))
        updated_count += 1

conn.commit()
print(f"Fixed {updated_count} articles with meta referrer and converted lazy images.")
conn.close()
