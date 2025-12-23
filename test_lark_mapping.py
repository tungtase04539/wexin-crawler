"""
Test script for Lark service field mapping
"""
from lark_service import lark_service
from models import Article, Account
from datetime import datetime

def test_mapping():
    # Setup mock article
    account = Account(name="Kênh AI")
    article = Article(
        title="ChatGPT vươn lên tầm cao mới",
        author="Tuấn Anh",
        url="https://example.com/ai-article",
        ai_summary="Bài viết nói về ChatGPT 5...",
        published_at=datetime(2025, 12, 23, 10, 0, 0),
        word_count=1200,
        read_count=5000,
        like_count=200,
        wow_count=50,
        comment_count=30,
        share_count=80,
        favorite_count=100,
        tags=["AI & LLM", "Tin tức công nghệ"]
    )
    article.account = account
    article.calculate_scores()
    
    # Map fields
    fields = lark_service._map_article_to_fields(article)
    
    # Print results
    print("--- Mapping Result ---")
    for k, v in fields.items():
        print(f"{k}: {v}")
        
    # Validation
    assert fields["Tiêu đề"] == article.title
    assert fields["Lượt đọc"] == 5000
    assert abs(fields["Điểm Nhiệt"] - article.heat_score) < 0.01
    assert "AI & LLM" in fields["Phân loại"]
    print("\nMapping test passed!")

if __name__ == "__main__":
    test_mapping()
