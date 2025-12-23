
import json
import sys
import os

# Mock settings/logger for standalone test
class MockSettings:
    openai_api_key = None
    enable_content_cleaning = True

import logging
logger = logging.getLogger(__name__)

# Import the actual processor
sys.path.append(os.getcwd())
from content_processor import content_processor

def test_author_extraction():
    # Load the remote feed sample we saved earlier
    try:
        with open('remote_feed_items.json', 'r', encoding='utf-8') as f:
            items = json.load(f)
    except FileNotFoundError:
        print("remote_feed_items.json not found. Run inspect_remote_feed.py first.")
        return

    print(f"Testing author extraction for {len(items)} items...")
    
    for idx, item in enumerate(items):
        # We process manually to skip full content fetch for now
        processed = content_processor.process_article(item, fetch_full_content=False)
        print(f"[{idx}] {item.get('title')[:30]}...")
        print(f"    Original Author: {item.get('author')}")
        print(f"    Extracted Author: {processed.get('author')}")
        
if __name__ == "__main__":
    test_author_extraction()
