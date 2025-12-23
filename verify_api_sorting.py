import requests
import json

def verify_api():
    base_url = "http://localhost:5000/api/articles"
    
    print("Testing default sort...")
    r = requests.get(f"{base_url}?limit=5")
    data = r.json()
    if data['success']:
        print(f"Total articles returned: {len(data['articles'])}")
        for i, a in enumerate(data['articles']):
            print(f"{i+1}. {a['title'][:30]}... | Heat: {a.get('heat_score', 'N/A')}")
    
    print("\nTesting heat_score sort...")
    r = requests.get(f"{base_url}?limit=5&sort=heat_score")
    data = r.json()
    if data['success']:
        for i, a in enumerate(data['articles']):
            print(f"{i+1}. {a['title'][:30]}... | Heat: {a.get('heat_score', 'N/A')}")

if __name__ == "__main__":
    verify_api()
