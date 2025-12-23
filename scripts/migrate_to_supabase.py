import os
import sys
import logging
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Add parent dir to path to import models and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from models import Base, Account, Article, SyncHistory
from database import Database

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

def migrate():
    # Target (Postgres/Supabase) - loaded from .env via settings
    supabase_url = settings.database_url
    
    logger.info(f"Source DB: SQLite (Local)")
    logger.info(f"Target DB: {supabase_url}")

    # Source (SQLite) - Forced local path
    src_db = Database("sqlite:///data/articles.db")
    
    # Target Engine
    dest_engine = create_engine(supabase_url)
    DestSession = sessionmaker(bind=dest_engine)
    
    # 1. Create Tables in Destination
    logger.info("Creating tables in destination...")
    Base.metadata.create_all(dest_engine)
    
    # 2. Migrate Data
    with src_db.get_session() as src_sess:
        with DestSession() as dest_sess:
            # --- Migrate Accounts ---
            accounts = src_sess.scalars(select(Account)).all()
            logger.info(f"Migrating {len(accounts)} accounts...")
            for acc in accounts:
                # Check if exists
                existing = dest_sess.scalar(select(Account).where(Account.feed_id == acc.feed_id))
                if not existing:
                    new_acc = Account(
                        feed_id=acc.feed_id,
                        name=acc.name,
                        description=acc.description,
                        avatar_url=acc.avatar_url,
                        feed_url=acc.feed_url,
                        is_active=acc.is_active,
                        created_at=acc.created_at,
                        updated_at=acc.updated_at
                    )
                    dest_sess.add(new_acc)
            dest_sess.commit()
            
            # --- Migrate Articles ---
            # Need to map account_ids correctly if they changed, strictly assuming feed_id match
            # But for simplicity, we assume IDs are preserved or we lookup by feed_id
            
            articles = src_sess.scalars(select(Article)).all()
            logger.info(f"Migrating {len(articles)} articles...")
            
            # Cache account mapping: src_id -> dest_id
            acc_map = {}
            dest_accounts = dest_sess.scalars(select(Account)).all()
            for da in dest_accounts:
                 # Find src account with same feed_id
                 src_acc = next((sa for sa in accounts if sa.feed_id == da.feed_id), None)
                 if src_acc:
                     acc_map[src_acc.id] = da.id
            
            for art in articles:
                if art.account_id not in acc_map:
                    continue
                    
                existing = dest_sess.scalar(select(Article).where(Article.url == art.url))
                if not existing:
                    new_art = Article(
                        account_id=acc_map[art.account_id],
                        title=art.title,
                        author=art.author,
                        url=art.url,
                        guid=art.guid,
                        content=art.content,
                        summary=art.summary,
                        ai_summary=art.ai_summary,
                        content_html=art.content_html, # Note: Large text
                        cover_image=art.cover_image,
                        images=art.images,
                        videos=art.videos,
                        published_at=art.published_at,
                        word_count=art.word_count,
                        tags=art.tags,
                        categories=art.categories,
                        read_count=art.read_count,
                        like_count=art.like_count,
                        heat_score=art.heat_score,
                        engagement_rate=art.engagement_rate,
                        is_simulated=art.is_simulated,
                        created_at=art.created_at,
                        updated_at=art.updated_at
                    )
                    dest_sess.add(new_art)
            
            dest_sess.commit()
            logger.info("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
