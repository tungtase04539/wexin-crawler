from database import db
from models import Article
from sqlalchemy import select, func

def check_db():
    with db.get_session() as session:
        stmt = select(func.count(Article.id)).where(Article.heat_score > 0)
        count = session.scalar(stmt)
        print(f"Articles with heat_score > 0: {count}")
        
        if count > 0:
            stmt = select(Article).where(Article.heat_score > 0).limit(5)
            articles = session.scalars(stmt).all()
            for a in articles:
                print(f"Article: {a.title[:30]} | Score: {a.heat_score}")

if __name__ == "__main__":
    check_db()
