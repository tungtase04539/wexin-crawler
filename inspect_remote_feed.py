
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

WEWE_RSS_URL = "https://inequilateral-homogenetically-stefanie.ngrok-free.dev"
AUTH_CODE = "techshrimp"

def check_feed():
    url = f"{WEWE_RSS_URL}/feeds/all.json"
    headers = {"Authorization": f"Bearer {AUTH_CODE}"}
    
    print(f"Fetching from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        items = data.get('items', [])
        print(f"Found {len(items)} articles.")
        
        # Save first 5 items to a file for deep inspection
        with open('remote_feed_items.json', 'w', encoding='utf-8') as f:
            json.dump(items[:5], f, indent=2, ensure_ascii=False)
        print("First 5 items saved to remote_feed_items.json")
        
        for idx, item in enumerate(items[:10]):
            author_data = item.get('author')
            authors_data = item.get('authors')
            content_html_len = len(item.get('content_html', ''))
            print(f"[{idx}] {item.get('title')[:30]}...")
            print(f"    author: {author_data}")
            print(f"    authors: {authors_data}")
            print(f"    content_html len: {content_html_len}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_feed()
