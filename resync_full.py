"""
Re-sync all articles with full content fetching
This will take 2-5 minutes due to rate limiting
"""
from sync_manager import sync_manager
import time

print("=" * 60)
print("Re-syncing all articles with FULL CONTENT fetching")
print("This will take 2-5 minutes (2 seconds delay per article)")
print("=" * 60)
print()

start_time = time.time()

# Sync the "all" feed with full content
result = sync_manager.sync_account('all', 'manual', full_sync=False)

elapsed = time.time() - start_time

print()
print("=" * 60)
print("SYNC COMPLETED!")
print("=" * 60)
print(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
print(f"Success: {result['success']}")
print(f"Account: {result.get('account', 'N/A')}")
print(f"Stats: {result.get('stats', {})}")
print()

if result['success']:
    stats = result.get('stats', {})
    print(f"✓ {stats.get('new', 0)} new articles")
    print(f"✓ {stats.get('updated', 0)} updated articles")
    print(f"✗ {stats.get('failed', 0)} failed")
    print()
    print("Dashboard: http://localhost:5000")
