
import requests
from bs4 import BeautifulSoup
import re

def test_crawl(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://mp.weixin.qq.com/'
    }
    
    print(f"Testing crawl for: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for common WeChat containers
        content_div = soup.find('div', {'id': 'js_content'})
        if not content_div:
             content_div = soup.find('div', class_=re.compile(r'rich_media_content'))
        
        if content_div:
            text = content_div.get_text(strip=True)
            print(f"Success! Found content container. Text length: {len(text)}")
            print(f"Sample text: {text[:200]}...")
            
            # Check for author in HTML
            author_span = soup.find('span', class_='rich_media_meta rich_media_meta_text')
            if author_span:
                print(f"Found author in HTML: {author_span.get_text(strip=True)}")
            
            nickname = soup.find('strong', class_='profile_nickname')
            if nickname:
                print(f"Found nickname in HTML: {nickname.get_text(strip=True)}")
        else:
            print("Failed to find content container!")
            with open('failed_page.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("Saved HTML to failed_page.html for inspection.")
            
    except Exception as e:
        print(f"Error during crawl: {e}")

if __name__ == "__main__":
    test_url = "https://mp.weixin.qq.com/s/vG8nsHXUiXCm5u1PAS8cSw"
    test_crawl(test_url)
