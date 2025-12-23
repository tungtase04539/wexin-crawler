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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
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
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract article content
        # WeChat articles typically use id="js_content"
        content_div = soup.find('div', {'id': 'js_content'})
        
        if not content_div:
            # Fallback: try other common containers
            content_div = soup.find('div', class_=re.compile(r'rich_media_content'))
        
        if not content_div:
            logger.warning("Could not find article content container")
            return {
                'content_text': '',
                'content_html': '',
                'images': [],
                'videos': []
            }
        
        # Extract text content
        content_text = self._extract_text(content_div)
        
        # Inject no-referrer meta tag to bypass WeChat anti-hotlinking
        meta_tag = soup.new_tag('meta')
        meta_tag.attrs['name'] = 'referrer'
        meta_tag.attrs['content'] = 'no-referrer'
        if soup.head:
            soup.head.insert(0, meta_tag)
        else:
            head = soup.new_tag('head')
            head.append(meta_tag)
            soup.insert(0, head)

        # Extract images
        images = self._extract_images(content_div, base_url)
        
        # Convert lazy-load data-src to src
        for img in content_div.find_all('img'):
            if img.get('data-src'):
                img['src'] = img['data-src']
                # Optionally remove data-src to clean up
                del img['data-src']
        
        # Get HTML (cleaned)
        content_html = str(content_div)
        
        # Strip WeChat's visibility:hidden and opacity:0
        content_html = content_html.replace('visibility: hidden;', '')
        content_html = content_html.replace('opacity: 0;', '')
        
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
