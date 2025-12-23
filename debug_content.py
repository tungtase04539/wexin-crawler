"""
Debug: Check what data we're getting from feed
"""
from wewe_client import wewe_client
from content_processor import content_processor

# Fetch feed
feed_data = wewe_client.fetch_all_feeds(format="json")

if feed_data and 'items' in feed_data:
    first_item = feed_data['items'][0]
    
    print("=== Raw Feed Item ===")
    print(f"Title: {first_item.get('title', 'N/A')}")
    print(f"URL: {first_item.get('url', 'N/A')}")
    print(f"Summary length: {len(first_item.get('summary', ''))}")
    print(f"Summary: {first_item.get('summary', 'N/A')[:200]}")
    print()
    
    # Process with content_processor
    print("=== Processed Article ===")
    processed = content_processor.process_article(first_item)
    print(f"Title: {processed['title']}")
    print(f"URL: {processed['url']}")
    print(f"Content length: {len(processed['content'])}")
    print(f"Content preview: {processed['content'][:200]}")
    print(f"Word count: {processed['word_count']}")
    print(f"Summary: {processed['summary'][:100]}")
