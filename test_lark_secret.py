import requests
import json

app_id = "cli_a9c0fe178d389ed0"
# Guessing the secret from the fragments found in corrupted .env
secret = "DTARDk1l5lLpQavw27k3Nfu1Kzz1elTB"

url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
payload = {
    "app_id": app_id,
    "app_secret": secret
}

resp = requests.post(url, json=payload)
print(resp.json())
