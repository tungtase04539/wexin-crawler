"""
Content Fetcher - Fetch full article content from WeChat URLs
Includes text, images, and videos
"""
import time
import requests
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

from config import settings
from logger import setup_logger
from cache import cached

logger = setup_logger(__name__)


class ContentFetcher:
    """Fetch and parse full article content from WeChat URLs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,vi;q=0.7',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://mp.weixin.qq.com/'
        })
        self.request_delay = 2  # Seconds between requests
        self.last_request_time = 0
    
    def _wait_if_needed(self):
        """Rate limiting - wait between requests"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    @cached(ttl=86400)  # Cache for 24 hours
    def fetch_article_content(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full article content from WeChat URL
        
        Args:
            url: WeChat article URL
        
        Returns:
            Dictionary with content, images, videos or None if failed
        """
        if not url or not url.startswith('http'):
            logger.warning(f"Invalid URL: {url}")
            return None
        
        logger.info(f"Fetching content from: {url[:80]}...")
        
        self._wait_if_needed()
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            html = response.text
            return self._parse_wechat_html(html, url)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return None
    
    def _parse_wechat_html(self, html: str, base_url: str) -> Dict[str, Any]:
        """
        Parse WeChat article HTML
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs
        
        Returns:
            Parsed content dictionary
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract article content
        # WeChat articles typically use id="js_content"
        content_div = soup.find('div', {'id': 'js_content'})
        
        if not content_div:
            # Fallback: try other common containers
            content_div = soup.find('div', class_=re.compile(r'rich_media_content'))
        
        if not content_div:
            logger.warning(f"Could not find article content container for {base_url}")
            # Log first 200 chars of HTML for debugging
            logger.debug(f"HTML Sample: {html[:200]}")
            return {
                'content_text': '',
                'content_html': '',
                'images': [],
                'videos': []
            }
        
        # Extract text content
        content_text = self._extract_text(content_div)
        
        # Extract images and clean them for display
        images = self._extract_images(content_div, base_url)
        
        # Process all images in the HTML for reliable display
        for img in content_div.find_all('img'):
            # 1. Handle lazy loading (data-src is very common in WeChat)
            actual_src = img.get('data-src') or img.get('src')
            if actual_src:
                img['src'] = urljoin(base_url, actual_src)
                # Remove data-src to prevent double loading or interference
                if img.get('data-src'):
                    del img['data-src']
            
            # 2. Bypass anti-hotlinking
            img['referrerpolicy'] = 'no-referrer'
            
            # 3. Ensure responsive layout
            existing_style = img.get('style', '')
            if 'max-width' not in existing_style.lower():
                img['style'] = f"{existing_style}; max-width: 100%; height: auto;".strip('; ')
            
            # 4. Remove visibility:hidden/opacity:0 that WeChat sometimes uses for lazy loading
            if img.get('style'):
                img['style'] = img['style'].replace('visibility: hidden', '').replace('opacity: 0', '')

        # Extract videos
        videos = self._extract_videos(content_div, base_url)
        
        # Process video iframes
        for iframe in content_div.find_all('iframe'):
            # WeChat uses data-src for iframes too
            actual_iframe_src = iframe.get('data-src') or iframe.get('src')
            if actual_iframe_src:
                iframe['src'] = urljoin(base_url, actual_iframe_src)
                if iframe.get('data-src'):
                    del iframe['data-src']
            
            # Anti-hotlinking for iframes
            iframe['referrerpolicy'] = 'no-referrer'
            
            # Responsive width
            existing_iframe_style = iframe.get('style', '')
            iframe['style'] = f"{existing_iframe_style}; max-width: 100%;".strip('; ')
            if not iframe.get('width'):
                iframe['width'] = "100%"

        # Get HTML (wrapped in a full document for the iframe)
        # This is critical for the "no-referrer" meta tag to work inside the iframe srcdoc
        inner_html = str(content_div)
        
        # Cleanup remaining visibility/opacity issues
        inner_html = inner_html.replace('visibility: hidden;', '')
        inner_html = inner_html.replace('opacity: 0;', '')
        inner_html = inner_html.replace('display: none!important;', '')
        
        content_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="no-referrer">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            overflow-x: hidden;
        }}
        img {{ 
            max-width: 100% !important; 
            height: auto !important; 
            display: block;
            margin: 10px 0;
        }}
        iframe {{ 
            max-width: 100% !important; 
        }}
        .rich_media_content {{
            overflow: hidden;
        }}
        /* Hide some WeChat elements that might break layout */
        .qr_code_pc_outer {{ display: none !important; }}
    </style>
</head>
<body>
    {inner_html}
</body>
</html>"""
        
        logger.info(f"Extracted: {len(content_text)} chars, {len(images)} images, {len(videos)} videos")
        
        return {
            'content_text': content_text,
            'content_html': content_html,
            'images': images,
            'videos': videos
        }
    
    def _extract_text(self, element) -> str:
        """Extract clean text from HTML element"""
        # Remove script and style elements
        for script in element(['script', 'style', 'iframe']):
            script.decompose()
        
        # Get text
        text = element.get_text(separator='\n')
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        
        return '\n'.join(lines)
    
    def _extract_images(self, element, base_url: str) -> List[Dict[str, str]]:
        """
        Extract all images from element
        
        Returns:
            List of dicts with 'url', 'alt', 'width', 'height'
        """
        images = []
        
        for img in element.find_all('img'):
            # WeChat images use data-src or src
            img_url = img.get('data-src') or img.get('src')
            
            if not img_url:
                continue
            
            # Resolve relative URLs
            img_url = urljoin(base_url, img_url)
            
            # Skip small images (likely icons)
            width = img.get('width', '')
            height = img.get('height', '')
            
            try:
                if width and int(width) < 50:
                    continue
                if height and int(height) < 50:
                    continue
            except (ValueError, TypeError):
                pass
            
            images.append({
                'url': img_url,
                'alt': img.get('alt', ''),
                'width': width,
                'height': height
            })
        
        return images
    
    def _extract_videos(self, element, base_url: str) -> List[Dict[str, str]]:
        """
        Extract all videos from element
        
        Returns:
            List of dicts with 'url', 'poster', 'type'
        """
        videos = []
        
        # Look for video tags
        for video in element.find_all('video'):
            video_url = video.get('src')
            
            if not video_url:
                # Check source tags
                source = video.find('source')
                if source:
                    video_url = source.get('src')
            
            if video_url:
                video_url = urljoin(base_url, video_url)
                videos.append({
                    'url': video_url,
                    'poster': video.get('poster', ''),
                    'type': 'video'
                })
        
        # Look for iframe embeds (common for WeChat videos)
        for iframe in element.find_all('iframe'):
            iframe_src = iframe.get('src', '')
            if 'video' in iframe_src.lower() or 'v.qq.com' in iframe_src:
                videos.append({
                    'url': iframe_src,
                    'poster': '',
                    'type': 'iframe'
                })
        
        return videos


# Global instance
content_fetcher = ContentFetcher()
