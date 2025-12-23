from sync_manager import sync_manager

print("Testing sync...")
result = sync_manager.sync_account('all', 'manual', True)

if result['success']:
    print(f"✓ Success!")
    print(f"  Account: {result['account']}")
    print(f"  Stats: {result['stats']}")
else:
    print(f"✗ Failed: {result.get('error')}")
