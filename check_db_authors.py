
import os
import sys
from sqlalchemy import select

# Setup paths
sys.path.append(os.getcwd())
from database import db
from models import Article

def check_db_authors():
    with db.get_session() as session:
        stmt = select(Article).limit(10)
        articles = session.scalars(stmt).all()
        
        print(f"Total articles in DB sample: {len(articles)}")
        for i, a in enumerate(articles):
            print(f"[{i}] ID: {a.id} | Title: {a.title[:30]}... | Author: '{a.author}'")

if __name__ == "__main__":
    check_db_authors()
