"""
Caching utilities for reducing redundant requests
"""
from typing import Optional, Any, Callable
from functools import wraps
from datetime import datetime, timedelta
import json
import hashlib
from pathlib import Path

from config import settings
from logger import setup_logger

logger = setup_logger(__name__)


class SimpleCache:
    """Simple file-based cache implementation"""
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize cache
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = settings.cache_ttl_seconds
        self.enabled = settings.enable_cache
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key"""
        # Hash the key to create a valid filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled:
            return None
        
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check expiration
            expires_at = datetime.fromisoformat(cache_data['expires_at'])
            if datetime.utcnow() > expires_at:
                logger.debug(f"Cache expired for key: {key[:50]}")
                cache_path.unlink()
                return None
            
            logger.debug(f"Cache hit for key: {key[:50]}")
            return cache_data['value']
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to read cache for key {key[:50]}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if not provided)
        """
        if not self.enabled:
            return
        
        cache_path = self._get_cache_path(key)
        ttl_seconds = ttl or self.ttl
        
        cache_data = {
            'key': key,
            'value': value,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cached value for key: {key[:50]}")
        except Exception as e:
            logger.warning(f"Failed to write cache for key {key[:50]}: {e}")
    
    def delete(self, key: str) -> None:
        """Delete cache entry"""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            logger.debug(f"Deleted cache for key: {key[:50]}")
    
    def clear(self) -> None:
        """Clear all cache"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        logger.info("Cleared all cache")


# Global cache instance
cache = SimpleCache()


def cached(ttl: Optional[int] = None):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds
    
    Usage:
        @cached(ttl=3600)
        def expensive_function(arg1, arg2):
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator
