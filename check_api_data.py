import requests
import json

def check_api_data():
    url = "http://localhost:5000/api/articles?limit=5"
    try:
        response = requests.get(url)
        data = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Success: {data.get('success')}")
        
        articles = data.get('articles', [])
        print(f"Count: {len(articles)}")
        if articles:
            print(f"Keys in first article: {list(articles[0].keys())}")
        
        for i, a in enumerate(articles):
            print(f"{i+1}. {a['title'][:30]}...")
            print(f"   Heat Score: {a.get('heat_score')}")
            print(f"   Engagement: {a.get('engagement_rate')}")
            print(f"   Simulated:  {a.get('is_simulated')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_api_data()
