
import os
import sys
import json
from datetime import datetime

# Setup paths
sys.path.append(os.getcwd())

from config import settings
from wewe_client import wewe_client
from content_processor import content_processor

# Override settings for debug
settings.wewe_rss_url = "https://inequilateral-homogenetically-stefanie.ngrok-free.dev"
settings.wewe_rss_auth_code = "techshrimp"

def debug_sync():
    print(f"Using WeWe-RSS URL: {settings.wewe_rss_url}")
    
    # 1. Fetch entries
    print("Fetching entries from 'all' feed...")
    entries = wewe_client.get_feed_entries("all", limit=5)
    
    if not entries:
        print("Error: No entries found. Is the Ngrok URL active?")
        return

    print(f"Found {len(entries)} entries.")
    
    processed_articles = []
    
    # 2. Process entries
    for idx, entry in enumerate(entries):
        print(f"\n--- Article [{idx}] Processing ---")
        print(f"Title: {entry.get('title')}")
        print(f"Raw Author: {entry.get('author')}")
        
        # We'll try fetching content too
        article_data = content_processor.process_article(entry, fetch_full_content=True)
        
        print(f"Extracted Author: {article_data.get('author')}")
        print(f"Content length: {len(article_data.get('content', ''))}")
        print(f"Content sample: {article_data.get('content')[:100] if article_data.get('content') else 'EMPTY'}")
        
        processed_articles.append({
            "title": article_data.get("title"),
            "author": article_data.get("author"),
            "content_len": len(article_data.get("content", "")),
            "url": article_data.get("url")
        })

    # Save results
    with open('debug_sync_results.json', 'w', encoding='utf-8') as f:
        json.dump(processed_articles, f, indent=2, ensure_ascii=False)
    print("\nResults saved to debug_sync_results.json")

if __name__ == "__main__":
    debug_sync()
