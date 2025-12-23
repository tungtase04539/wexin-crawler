import time
import requests
from config import settings
from lark_service import lark_service

def test_create_record():
    print("--- Testing Lark Record Creation ---")
    token = lark_service._get_tenant_access_token()
    if not token:
        print("Failed to get token")
        return

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{settings.lark_base_token}/tables/{settings.lark_table_id}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    # Use basic fields first to narrow down the issue
    payload = {
        "fields": {
            "Tiêu đề": "Test Article " + str(int(time.time())),
            "Link Gốc": "https://example.com/test-" + str(int(time.time())),
            "Tác giả": "Agent",
            "Tài khoản": "Debug",
            "Ngày đăng": int(time.time() * 1000)
        }
    }

    try:
        print(f"Sending request to: {url}")
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        print(f"Response Code: {data.get('code')}")
        print(f"Response Msg: {data.get('msg')}")
        if data.get('code') != 0:
            print(f"Full Error Detail: {data}")
        else:
            print("[SUCCESS] Record created!")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_create_record()
