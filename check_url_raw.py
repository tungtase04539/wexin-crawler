
import requests
from config import settings

url = "http://mp.weixin.qq.com/s?__biz=MzkxODQzMzExMA==&mid=2247492166&idx=1&sn=9e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e" # Placeholder, I need the real URL
# Actually I'll get the real URL from the DB

import sqlite3
from pathlib import Path

db_path = Path("data/articles.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

title_pattern = "%腾讯开源世界第一生图模型%"
cursor.execute("SELECT url FROM articles WHERE title LIKE ?", (title_pattern,))
row = cursor.fetchone()

if row:
    url = row[0]
    print(f"URL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://mp.weixin.qq.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        with open("raw_article.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Raw HTML saved to raw_article.html")
        
        # Check if js_content is in there
        if 'id="js_content"' in response.text:
            print("FOUND js_content")
        else:
            print("NOT FOUND js_content")
            
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Article not found in DB")

conn.close()
