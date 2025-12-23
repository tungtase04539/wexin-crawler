"""
Debug script to check feed data structure
"""
from wewe_client import wewe_client
import json

print("Fetching feed data...")
feed_data = wewe_client.fetch_all_feeds(format="json")

if feed_data and 'items' in feed_data:
    print(f"\nTotal items: {len(feed_data['items'])}")
    
    # Show first item structure
    if feed_data['items']:
        first_item = feed_data['items'][0]
        print("\n=== First Item Structure ===")
        print(json.dumps(first_item, indent=2, ensure_ascii=False))
        
        print("\n=== Available Fields ===")
        for key in first_item.keys():
            value = first_item[key]
            value_type = type(value).__name__
            value_preview = str(value)[:100] if value else "None"
            print(f"  {key}: {value_type} = {value_preview}")
