import requests
import json

def check_api():
    url = "http://localhost:5000/api/articles?limit=5"
    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get('articles', [])
        for a in articles:
            print(f"ID: {a['id']}, Title: {a['title'][:20]}..., Simulated: {a['is_simulated']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_api()
