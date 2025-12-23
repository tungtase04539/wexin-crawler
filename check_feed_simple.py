import json
import requests

# Direct HTTP check
response = requests.get("http://localhost:4000/feeds/all.json")
data = response.json()

first_item = data['items'][0]

# Save to file to avoid unicode issues
with open("feed_sample.json", "w", encoding="utf-8") as f:
    json.dump(first_item, f, indent=2, ensure_ascii=False)

print(f"Saved first item to feed_sample.json")
print(f"Has summary: {'summary' in first_item}")
print(f"Summary length: {len(first_item.get('summary', ''))}")
print(f"Has content_html: {'content_html' in first_item}")
print(f"Has content_text: {'content_text' in first_item}")
print(f"Has url: {'url' in first_item}")
print(f"URL: {first_item.get('url', 'N/A')}")
