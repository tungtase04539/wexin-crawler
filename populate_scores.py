from database import db
from models import Article
from metrics_fetcher import metrics_fetcher
from sqlalchemy import select
from datetime import datetime

def populate_all_scores():
    print("Starting population of scores for all articles...")
    with db.get_session() as session:
        stmt = select(Article)
        articles = session.scalars(stmt).all()
        
        print(f"Found {len(articles)} articles.")
        
        for article in articles:
            # Always fetch new metrics during this transition to ensure is_simulated is set
            metrics = metrics_fetcher.fetch_article_metrics(article.url)
            if metrics:
                print(f"Metrics for ID {article.id}: Simulated={metrics.get('is_simulated')}")
                for key, val in metrics.items():
                    if hasattr(article, key):
                        setattr(article, key, val)
                article.is_simulated = metrics.get('is_simulated', False)
                article.metrics_updated_at = datetime.utcnow()
                print(f"Article {article.id} is_simulated set to: {article.is_simulated}")
            
            # Recalculate scores
            article.calculate_scores()
            print(f"Scored: {article.title[:40]} | Heat: {article.heat_score}")
            
        session.commit()
    print("Finished populating scores.")

if __name__ == "__main__":
    populate_all_scores()
