"""
Test content fetcher with a real WeChat URL
"""
from content_fetcher import content_fetcher

# Test URL (from feed_sample.json if available, or use a sample)
test_url = "https://mp.weixin.qq.com/s/IWimsldbLPnNx2gfToYTig"

print(f"Testing content fetcher with URL: {test_url}\n")

result = content_fetcher.fetch_article_content(test_url)

if result:
    print("✓ Content fetched successfully!")
    print(f"  Content length: {len(result['content_text'])} characters")
    print(f"  Images: {len(result['images'])}")
    print(f"  Videos: {len(result['videos'])}")
    print(f"\n  Content preview:")
    print(f"  {result['content_text'][:300]}...")
else:
    print("✗ Failed to fetch content")
