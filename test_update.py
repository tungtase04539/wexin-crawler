
import sqlite3
conn = sqlite3.connect('data/articles.db')
cursor = conn.cursor()
try:
    cursor.execute('UPDATE articles SET tags=null WHERE id=1')
    conn.commit()
    print("Tags column update SUCCESS")
except Exception as e:
    print(f"Tags column update FAILED: {e}")
conn.close()
