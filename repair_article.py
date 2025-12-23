
from wewe_client import wewe_client
from database import db
from content_processor import content_processor
from models import Article, Account

try:
    with db.get_session() as session:
        # Find articles with empty content or URL
        from sqlalchemy import select, or_
        stmt = select(Article).where(or_(Article.content == '', Article.url == ''))
        articles = list(session.scalars(stmt).all())
        
        print(f"Found {len(articles)} problematic articles")
        
        for article in articles:
            print(f"Repairing: {article.title}")
            account = session.get(Account, article.account_id)
            if not account: continue
            
            # Fetch entries for this account
            entries = wewe_client.get_feed_entries(account.feed_id)
            
            # Try to find matching entry by title
            match = None
            for entry in entries:
                entry_title = entry.get('title', '').strip()
                if entry_title == article.title.strip():
                    match = entry
                    break
            
            if match:
                print(f"  Found match in feed!")
                # Re-process
                article_data = content_processor.process_article(match)
                
                # Update article
                for k, v in article_data.items():
                    if hasattr(article, k):
                        setattr(article, k, v)
                print(f"  Updated successfully. New URL: {article.url}, Content length: {len(article.content)}")
            else:
                print(f"  Could not find match in feed for this title.")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
