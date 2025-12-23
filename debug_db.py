from database import db
from models import Account, Article

db.create_tables()

with db.get_session() as session:
    accounts = session.query(Account).all()
    articles = session.query(Article).all()
    
    print(f"\n=== Database Status ===")
    print(f"Accounts: {len(accounts)}")
    for acc in accounts:
        print(f"  - ID: {acc.id}, Feed: {acc.feed_id}, Name: {acc.name}")
    
    print(f"\nArticles: {len(articles)}")
    for art in articles[:5]:
        print(f"  - {art.title[:60]}...")
    
    if len(articles) > 5:
        print(f"  ...and {len(articles) - 5} more")
