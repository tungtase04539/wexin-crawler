
import os
import sys
import requests

# Setup paths
sys.path.append(os.getcwd())
from config import settings

settings.wewe_rss_url = "https://inequilateral-homogenetically-stefanie.ngrok-free.dev"
settings.wewe_rss_auth_code = "techshrimp"

def check_feed_titles():
    url = f"{settings.wewe_rss_url}/feeds/all.json"
    headers = {"Authorization": f"Bearer {settings.wewe_rss_auth_code}"}
    response = requests.get(url, headers=headers)
    data = response.json()
    
    print(f"ALL FEED TITLE: {data.get('title')}")
    print(f"ALL FEED KEYS: {list(data.keys())}")
    
    # Check a specific feed if authors are in the articles list
    items = data.get('items', [])
    if items:
        # Just to be sure, check if ANY item has a missing author in the processor's eyes
        from content_processor import content_processor
        for item in items[:3]:
            processed = content_processor.process_article(item, fetch_full_content=False)
            print(f"Item Title: {item.get('title')[:30]} | Extracted Author: {processed.get('author')}")

if __name__ == "__main__":
    check_feed_titles()
