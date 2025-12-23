from database import db
from models import Article
import json

with db.get_session() as session:
    articles = session.query(Article).all()
    
    print(f"Total articles in DB: {len(articles)}\n")
    
    for i, art in enumerate(articles[:3], 1):
        print(f"=== Article {i} ===")
        print(f"ID: {art.id}")
        print(f"Title: {art.title}")
        print(f"Author: {art.author}")
        print(f"URL: {art.url}")
        print(f"GUID: {art.guid}")
        print(f"Content length: {len(art.content) if art.content else 0}")
        print(f"Published: {art.published_at}")
        print(f"Word count: {art.word_count}")
        print()
