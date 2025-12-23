
from wewe_client import wewe_client
import json

# Get all accounts
from database import db
accounts = db.get_all_accounts()

if accounts:
    feed_id = accounts[0].feed_id
    print(f"Fetching feed for: {feed_id}")
    
    entries = wewe_client.get_feed_entries(feed_id, limit=5)
    print(f"Total entries: {len(entries)}")
    
    if entries:
        for i, entry in enumerate(entries):
            print(f"Entry {i}:")
            print(f"  title: {entry.get('title')}")
            print(f"  url: {entry.get('url')}")
            print(f"  link: {entry.get('link')}")
            print(f"  id: {entry.get('id')}")
else:
    print("No accounts found in DB")
