
import os
import sys
import json
import requests

# Setup paths
sys.path.append(os.getcwd())

from config import settings
from wewe_client import wewe_client
from content_processor import content_processor

# Use the user's URL
settings.wewe_rss_url = "https://inequilateral-homogenetically-stefanie.ngrok-free.dev"
settings.wewe_rss_auth_code = "techshrimp"

def check_all_authors():
    url = f"{settings.wewe_rss_url}/feeds/all.json"
    headers = {"Authorization": f"Bearer {settings.wewe_rss_auth_code}"}
    response = requests.get(url, headers=headers)
    data = response.json()
    
    items = data.get('items', [])
    print(f"Checking {len(items)} items...")
    
    for idx, item in enumerate(items):
        processed = content_processor.process_article(item, fetch_full_content=False)
        title = item.get('title', '')[:30]
        raw_author = item.get('author')
        raw_authors = item.get('authors')
        ext_author = processed.get('author')
        
        if ext_author == "Unknown" or not ext_author:
            print(f"!!! [FAIL] Item {idx}: {title}")
            print(f"    Raw author: {raw_author}")
            print(f"    Raw authors: {raw_authors}")
            print(f"    Full Item Keys: {list(item.keys())}")
        else:
             print(f"    [OK] Item {idx}: {ext_author} | {title}")

if __name__ == "__main__":
    check_all_authors()
