from database import db
from models import Article
from metrics_fetcher import metrics_fetcher
from datetime import datetime

def test_refresh_persistence():
    with db.get_session() as session:
        # Get one article
        article = session.query(Article).first()
        if not article:
            print("No articles found.")
            return

        print(f"Testing refresh for ID: {article.id}, URL: {article.url}")
        print(f"Current is_simulated: {article.is_simulated}")
        
        # Call fetcher
        metrics = metrics_fetcher.fetch_article_metrics(article.url)
        if metrics:
            print(f"Fetcher returned is_simulated: {metrics.get('is_simulated')}")
            for key, val in metrics.items():
                if hasattr(article, key):
                    setattr(article, key, val)
            article.is_simulated = metrics.get('is_simulated', False)
            article.metrics_updated_at = datetime.utcnow()
            article.calculate_scores()
            session.commit()
            
            # Re-fetch from DB
            session.refresh(article)
            print(f"New is_simulated in DB: {article.is_simulated}")
        else:
            print("Fetcher failed to return metrics.")

if __name__ == "__main__":
    test_refresh_persistence()
