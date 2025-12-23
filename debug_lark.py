import os
import sys
from config import settings
from lark_service import lark_service
from logger import setup_logger

logger = setup_logger("lark_debug")

def test_lark_connection():
    print("--- Starting Lark Sync Debug ---")
    print(f"App ID: {settings.lark_app_id}")
    print(f"Base Token: {settings.lark_base_token}")
    print(f"Table ID: {settings.lark_table_id}")
    
    token = lark_service._get_tenant_access_token()
    if token:
        print("[SUCCESS] Obtained Tenant Access Token")
    else:
        print("[FAILED] Could not obtain Tenant Access Token. Check App ID and App Secret.")
        return

    # Test searching for a dummy record
    print("Testing record search...")
    try:
        record_id = lark_service._find_record_by_url("https://example.com/test", token)
        print(f"[INFO] Search completed. Record ID: {record_id}")
    except Exception as e:
        print(f"[FAILED] Search crashed: {e}")

if __name__ == "__main__":
    test_lark_connection()
