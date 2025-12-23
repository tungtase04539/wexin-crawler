"""
WeWe-RSS Client for fetching RSS feeds
"""
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import settings
from logger import setup_logger
from cache import cached

logger = setup_logger(__name__)


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, max_requests_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.requests = []
    
    def wait_if_needed(self):
        """Wait if rate limit is exceeded"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        # Check if we need to wait
        if len(self.requests) >= self.max_requests:
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached, waiting {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                self.requests = []
        
        self.requests.append(now)


class WeWeRSSClient:
    """Client for interacting with WeWe-RSS"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_code: Optional[str] = None
    ):
        """
        Initialize WeWe-RSS client
        
        Args:
            base_url: Base URL of WeWe-RSS server
            auth_code: Authentication code (if required)
        """
        self.base_url = (base_url or settings.wewe_rss_url).rstrip('/')
        self.auth_code = auth_code or settings.wewe_rss_auth_code
        
        # Setup session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Rate limiter
        self.rate_limiter = RateLimiter(settings.max_requests_per_minute)
        
        logger.info(f"WeWe-RSS client initialized: {self.base_url}")
    
    def _make_request(self, url: str, timeout: int = 30) -> Optional[requests.Response]:
        """
        Make HTTP request with rate limiting
        
        Args:
            url: URL to request
            timeout: Request timeout in seconds
        
        Returns:
            Response object or None if failed
        """
        self.rate_limiter.wait_if_needed()
        
        try:
            headers = {}
            if self.auth_code:
                headers['Authorization'] = f"Bearer {self.auth_code}"
            
            response = self.session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    @cached(ttl=1800)  # Cache for 30 minutes
    def fetch_feed(
        self,
        feed_id: str,
        format: str = "json"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch RSS feed for a specific account
        
        Args:
            feed_id: Feed/account ID
            format: Feed format (json, rss, atom)
        
        Returns:
            Parsed feed data or None if failed
        """
        url = f"{self.base_url}/feeds/{feed_id}.{format}"
        logger.info(f"Fetching feed: {feed_id} (format: {format})")
        
        response = self._make_request(url)
        if not response:
            return None
        
        try:
            if format == "json":
                return response.json()
            else:
                # Parse RSS/Atom with feedparser
                feed = feedparser.parse(response.content)
                return self._normalize_feed(feed)
        
        except Exception as e:
            logger.error(f"Failed to parse feed {feed_id}: {e}")
            return None
    
    @cached(ttl=1800)
    def fetch_all_feeds(self, format: str = "json") -> Optional[Dict[str, Any]]:
        """
        Fetch all feeds
        
        Args:
            format: Feed format (json, rss, atom)
        
        Returns:
            Parsed feed data or None if failed
        """
        url = f"{self.base_url}/feeds/all.{format}"
        logger.info(f"Fetching all feeds (format: {format})")
        
        response = self._make_request(url)
        if not response:
            return None
        
        try:
            if format == "json":
                return response.json()
            else:
                feed = feedparser.parse(response.content)
                return self._normalize_feed(feed)
        
        except Exception as e:
            logger.error(f"Failed to parse all feeds: {e}")
            return None
    
    def _normalize_feed(self, feed: feedparser.FeedParserDict) -> Dict[str, Any]:
        """
        Normalize feedparser output to consistent format
        
        Args:
            feed: Parsed feed from feedparser
        
        Returns:
            Normalized feed dictionary
        """
        normalized = {
            "title": feed.feed.get("title", ""),
            "description": feed.feed.get("description", ""),
            "link": feed.feed.get("link", ""),
            "updated": feed.feed.get("updated", ""),
            "items": []
        }
        
        for entry in feed.entries:
            item = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "description": entry.get("description", ""),
                "content": self._extract_content(entry),
                "author": entry.get("author", ""),
                "published": entry.get("published", ""),
                "updated": entry.get("updated", ""),
                "id": entry.get("id", entry.get("link", "")),
                "summary": entry.get("summary", "")
            }
            normalized["items"].append(item)
        
        return normalized
    
    def _extract_content(self, entry: Dict[str, Any]) -> str:
        """Extract full content from feed entry"""
        # Try different content fields
        if "content" in entry:
            if isinstance(entry["content"], list) and len(entry["content"]) > 0:
                return entry["content"][0].get("value", "")
            return str(entry["content"])
        
        if "summary" in entry:
            return entry["summary"]
        
        if "description" in entry:
            return entry["description"]
        
        return ""
    
    def get_feed_entries(
        self,
        feed_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entries from a feed
        
        Args:
            feed_id: Feed/account ID
            limit: Maximum number of entries to return
        
        Returns:
            List of feed entries
        """
        feed_data = self.fetch_feed(feed_id, format="json")
        
        if not feed_data:
            return []
        
        # Handle JSON feed format
        if "items" in feed_data:
            items = feed_data["items"]
        else:
            items = []
        
        if limit:
            items = items[:limit]
        
        logger.info(f"Retrieved {len(items)} entries from feed {feed_id}")
        return items
    
    def test_connection(self) -> bool:
        """
        Test connection to WeWe-RSS server
        
        Returns:
            True if connection successful
        """
        try:
            response = self._make_request(self.base_url, timeout=10)
            if response:
                logger.info("Connection to WeWe-RSS successful")
                return True
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Global client instance
wewe_client = WeWeRSSClient()
