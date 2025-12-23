import requests

def check_served_html():
    url = "http://localhost:5000/articles"
    try:
        response = requests.get(url)
        html = response.text
        
        print(f"Status: {response.status_code}")
        print(f"Contains 'heat_score': {'heat_score' in html}")
        print(f"Contains 'filters.sort': {'filters.sort' in html}")
        
        if 'heat_score' not in html:
            print("WARNING: 'heat_score' is MISSING from served HTML!")
            # Print a snippet of the filter area
            start = html.find('<!-- Filters -->')
            if start != -1:
                print("\nFilter area content:")
                print(html[start:start+1000])
        else:
            print("SUCCESS: 'heat_score' IS in served HTML.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_served_html()
