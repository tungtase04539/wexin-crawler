"""
Metrics Fetcher module for Jizhile API
"""
import hashlib
import random
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from config import settings
from logger import setup_logger

logger = setup_logger(__name__)

class MetricsFetcher:
    """Fetch engagement metrics from Jizhile API"""
    
    API_URL = "https://www.dajiala.com/fbmain/monitor/v3/read_zan_pro"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with API key. If not provided, use from settings.
        """
        self.api_key = api_key or getattr(settings, 'jizhile_api_key', None)
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning("Jizhile API key not configured. Using simulated metrics for demo.")

    def _generate_simulated_metrics(self, url: str) -> Dict[str, Any]:
        """Generate deterministic simulated metrics based on URL"""
        seed = int(hashlib.md5(url.encode()).hexdigest(), 16) % (10**8)
        rng = random.Random(seed)
        
        read_count = rng.randint(100, 50000)
        return {
            "read_count": read_count,
            "like_count": int(read_count * rng.uniform(0.01, 0.05)),
            "wow_count": int(read_count * rng.uniform(0.005, 0.02)),
            "comment_count": int(read_count * rng.uniform(0.001, 0.01)),
            "share_count": int(read_count * rng.uniform(0.005, 0.03)),
            "favorite_count": int(read_count * rng.uniform(0.005, 0.02)),
            "is_simulated": True
        }

    def fetch_article_metrics(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch metrics for a single article URL. 
        Returns metrics and a 'is_simulated' flag.
        Falls back to simulation if API key is missing or API call fails.
        """
        if not self.enabled:
            return self._generate_simulated_metrics(url)

        # Real Jizhile API call (Pro API 17)
        try:
            payload = {
                "url": url,
                "key": self.api_key
            }
            
            logger.info(f"Fetching real metrics for: {url}")
            response = requests.post(self.API_URL, json=payload, timeout=20)
            
            if response.status_code != 200:
                logger.error(f"Jizhile API HTTP error {response.status_code}")
                return self._generate_simulated_metrics(url)
                
            data = response.json()
            
            # Adjust mapping based on actual Jizhile Pro API response
            if data.get('code') == 1 or data.get('code') == 0:
                # Try to get data from 'data' key first, then fallback to top-level
                res_data = data.get('data')
                if not isinstance(res_data, dict):
                    res_data = data
                
                # Check if we actually got metrics or just an empty success
                # Some API responses might be successful but lack metrics if article is too new
                if not any(res_data.get(k) for k in ["read_num", "real_read_num", "like_num", "read", "zan"]):
                    logger.warning(f"API success but no metrics found for {url}. Using simulation.")
                    return self._generate_simulated_metrics(url)

                metrics = {
                    "read_count": res_data.get("real_read_num") or res_data.get("read_num") or res_data.get("read", 0),
                    "like_count": res_data.get("old_like_num") if res_data.get("old_like_num") is not None else (res_data.get("like_num") if res_data.get("like_num") is not None else res_data.get("zan", 0)),
                    "wow_count": res_data.get("look_num") or res_data.get("looking", 0),
                    "share_count": res_data.get("share_num", 0),
                    "favorite_count": res_data.get("fav_num") or res_data.get("collect_num", 0),
                    "comment_count": res_data.get("comment_num") or res_data.get("comment_count", 0),
                    "is_simulated": False
                }
                logger.info(f"Successfully fetched real metrics: {metrics}")
                return metrics
            else:
                error_code = data.get('code')
                error_msg = data.get('msg', 'Unknown error')
                logger.error(f"Jizhile API error {error_code}: {error_msg}. Falling back to simulation.")
                return self._generate_simulated_metrics(url)
                
        except Exception as e:
            logger.error(f"Failed to fetch metrics for {url}: {e}. Falling back to simulation.")
            return self._generate_simulated_metrics(url)

# Global instance
metrics_fetcher = MetricsFetcher()
