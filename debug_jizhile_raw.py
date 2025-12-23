
import requests
import json
from config import settings

def debug_jizhile():
    url = "https://mp.weixin.qq.com/s/zTpijiDuZQsWPJxMcfW-2g"
    api_url = "https://www.dajiala.com/fbmain/monitor/v3/read_zan_pro"
    
    payload = {
        "url": url,
        "key": settings.jizhile_api_key
    }
    
    print(f"Testing URL: {url}")
    print(f"Using Key: {settings.jizhile_api_key}")
    
    response = requests.post(api_url, json=payload, timeout=20)
    print(f"Status Code: {response.status_code}")
    print("Raw Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    debug_jizhile()
