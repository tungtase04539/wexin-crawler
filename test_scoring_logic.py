
from database import db
from models import Article
from sqlalchemy import select

def test_scoring():
    with db.get_session() as session:
        # Get first article
        stmt = select(Article).limit(1)
        article = session.scalar(stmt)
        
        if not article:
            print("No articles found to test")
            return
            
        print(f"Testing scoring for: {article.title}")
        
        # Inject mock metrics
        article.read_count = 1000
        article.like_count = 50
        article.wow_count = 20
        article.comment_count = 5
        article.share_count = 15
        article.favorite_count = 10
        
        # Calculate scores
        article.calculate_scores()
        
        print(f"Read: {article.read_count}")
        print(f"Engagement Rate (Expected 70.0): {article.engagement_rate}")
        print(f"Virality Index (Expected 50.0): {article.virality_index}")
        print(f"Value Index (Expected 25.0): {article.content_value_index}")
        print(f"Heat Score (Expected 21.0?): {article.heat_score}")
        
        # (Likes*1 + Wow*2 + Comments*3 + Favorites*4 + Shares*5) / Read Count * 100
        # (50*1 + 20*2 + 5*3 + 10*4 + 15*5) / 1000 * 100
        # (50 + 40 + 15 + 40 + 75) / 1000 * 100
        # 220 / 10 = 22.0
        
        session.commit()
        print("Scores saved to database.")

if __name__ == "__main__":
    test_scoring()
