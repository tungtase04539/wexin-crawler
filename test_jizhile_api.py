import requests
import json
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from config import settings
from metrics_fetcher import MetricsFetcher

def test_api():
    fetcher = MetricsFetcher(settings.jizhile_api_key)
    # Use a real WeChat article URL for testing
    test_url = "https://mp.weixin.qq.com/s/zTpijiDuZQsWPJxMcfW-2g"
    
    print(f"Testing API with URL: {test_url}")
    print(f"API Key: {settings.jizhile_api_key[:5]}...{settings.jizhile_api_key[-5:]}")
    
    metrics = fetcher.fetch_article_metrics(test_url)
    
    if metrics:
        print("\nSuccess! Metrics fetched:")
        print(json.dumps(metrics, indent=2))
        if not metrics.get('is_simulated'):
            print("\nVERIFIED: Data is REAL (not simulated).")
        else:
            print("\nWARNING: Data is still SIMULATED.")
    else:
        print("\nFailed to fetch metrics. Check logs.")

if __name__ == "__main__":
    test_api()
