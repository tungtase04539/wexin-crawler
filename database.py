"""
Database operations and connection management
"""
from contextlib import contextmanager
from typing import Optional, List, Generator
from datetime import datetime
from sqlalchemy import create_engine, select, func, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from logger import setup_logger
from models import Base, Account, Article, SyncHistory

logger = setup_logger(__name__)


class Database:
    """Database manager class"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection
        
        Args:
            database_url: Database connection URL (uses settings if not provided)
        """
        self.database_url = database_url or settings.final_database_url
        
        # Create engine
        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,  # Keep objects usable after commit
            bind=self.engine
        )
        
        logger.info(f"Database initialized: {self.database_url}")
    
    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session context manager
        
        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # Account operations
    def create_account(
        self,
        feed_id: str,
        name: str,
        feed_url: str,
        description: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Account:
        """Create a new account"""
        with self.get_session() as session:
            account = Account(
                feed_id=feed_id,
                name=name,
                feed_url=feed_url,
                description=description,
                avatar_url=avatar_url
            )
            session.add(account)
            session.flush()
            session.refresh(account)
            logger.info(f"Created account: {name} (ID: {account.id})")
            return account
    
    def get_account_by_feed_id(self, feed_id: str) -> Optional[Account]:
        """Get account by feed ID"""
        with self.get_session() as session:
            stmt = select(Account).where(Account.feed_id == feed_id)
            account = session.scalar(stmt)
            return account
    
    def get_all_accounts(self, active_only: bool = True) -> List[Account]:
        """Get all accounts"""
        with self.get_session() as session:
            stmt = select(Account)
            if active_only:
                stmt = stmt.where(Account.is_active == True)
            return list(session.scalars(stmt).all())
            
    def get_accounts_with_summary(self, active_only: bool = False) -> List[dict]:
        """
        Get all accounts with article counts and latest sync info in an optimized way
        """
        from sqlalchemy import select, func, and_
        
        with self.get_session() as session:
            # 1. Get account details and article counts
            count_stmt = (
                select(
                    Account,
                    func.count(Article.id).label('articles_count')
                )
                .outerjoin(Article, Account.id == Article.account_id)
                .group_by(Account.id)
            )
            
            if active_only:
                count_stmt = count_stmt.where(Account.is_active == True)
                
            results = session.execute(count_stmt).all()
            
            # 2. Get latest sync for each account
            # Subquery to get latest sync ID per account
            latest_sync_sid = (
                select(
                    SyncHistory.account_id,
                    func.max(SyncHistory.started_at).label('max_start')
                )
                .group_by(SyncHistory.account_id)
                .subquery()
            )
            
            latest_sync_stmt = (
                select(SyncHistory)
                .join(
                    latest_sync_sid,
                    and_(
                        SyncHistory.account_id == latest_sync_sid.c.account_id,
                        SyncHistory.started_at == latest_sync_sid.c.max_start
                    )
                )
            )
            
            syncs = session.scalars(latest_sync_stmt).all()
            sync_map = {s.account_id: s for s in syncs}
            
            # Merge results
            summary = []
            for account, count in results:
                ls = sync_map.get(account.id)
                summary.append({
                    'account': account,
                    'articles_count': count,
                    'latest_sync': ls
                })
                
            return summary
    
    def update_account(self, account_id: int, **kwargs) -> Optional[Account]:
        """Update account fields"""
        with self.get_session() as session:
            account = session.get(Account, account_id)
            if account:
                for key, value in kwargs.items():
                    if hasattr(account, key):
                        setattr(account, key, value)
                account.updated_at = datetime.utcnow()
                session.flush()
                session.refresh(account)
                logger.info(f"Updated account ID: {account_id}")
            return account
    
    # Article operations
    def create_article(self, **kwargs) -> Article:
        """Create a new article"""
        with self.get_session() as session:
            article = Article(**kwargs)
            session.add(article)
            session.flush()
            session.refresh(article)
            logger.debug(f"Created article: {article.title[:50]}")
            return article
    
    def get_article_by_url(self, url: str) -> Optional[Article]:
        """Get article by URL"""
        with self.get_session() as session:
            stmt = select(Article).where(Article.url == url)
            return session.scalar(stmt)
    
    def get_articles_by_account(
        self,
        account_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_by: str = "published_at"
    ) -> List[Article]:
        """Get articles for an account"""
        with self.get_session() as session:
            stmt = select(Article).where(Article.account_id == account_id)
            
            # Sorting logic
            if sort_by == "heat_score":
                stmt = stmt.order_by(Article.heat_score.desc())
            elif sort_by == "engagement_rate":
                stmt = stmt.order_by(Article.engagement_rate.desc())
            elif sort_by == "published_at_asc":
                stmt = stmt.order_by(Article.published_at.asc())
            else:
                stmt = stmt.order_by(Article.published_at.desc())
                
            if limit:
                stmt = stmt.limit(limit).offset(offset)
            return list(session.scalars(stmt).all())
    
    def get_recent_articles(self, limit: int = 50, sort_by: str = "created_at") -> List[Article]:
        """Get recent articles across all accounts"""
        with self.get_session() as session:
            stmt = select(Article)
            
            # Sorting logic
            if sort_by == "heat_score":
                stmt = stmt.order_by(Article.heat_score.desc())
            elif sort_by == "engagement_rate":
                stmt = stmt.order_by(Article.engagement_rate.desc())
            elif sort_by == "published_at":
                stmt = stmt.order_by(Article.published_at.desc())
            else:
                stmt = stmt.order_by(Article.created_at.desc())
                
            stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())
    
    def update_article(self, article_id: int, **kwargs) -> Optional[Article]:
        """Update article fields"""
        with self.get_session() as session:
            article = session.get(Article, article_id)
            if article:
                for key, value in kwargs.items():
                    if hasattr(article, key):
                        setattr(article, key, value)
                article.updated_at = datetime.utcnow()
                session.flush()
                session.refresh(article)
            return article
    
    def article_exists(self, url: str) -> bool:
        """Check if article exists by URL"""
        with self.get_session() as session:
            stmt = select(func.count()).select_from(Article).where(Article.url == url)
            count = session.scalar(stmt)
            return count > 0
    
    # Sync history operations
    def create_sync_history(
        self,
        account_id: Optional[int] = None,
        sync_type: str = "manual"
    ) -> SyncHistory:
        """Create a new sync history record"""
        with self.get_session() as session:
            sync_history = SyncHistory(
                account_id=account_id,
                sync_type=sync_type,
                status="running"
            )
            session.add(sync_history)
            session.flush()
            session.refresh(sync_history)
            return sync_history
    
    def update_sync_history(self, sync_id: int, **kwargs) -> Optional[SyncHistory]:
        """Update sync history"""
        with self.get_session() as session:
            sync_history = session.get(SyncHistory, sync_id)
            if sync_history:
                for key, value in kwargs.items():
                    if hasattr(sync_history, key):
                        setattr(sync_history, key, value)
                
                # Calculate duration if completed
                if kwargs.get('completed_at'):
                    duration = (kwargs['completed_at'] - sync_history.started_at).total_seconds()
                    sync_history.duration_seconds = int(duration)
                
                session.flush()
                session.refresh(sync_history)
            return sync_history
    
    def get_latest_sync(self, account_id: Optional[int] = None) -> Optional[SyncHistory]:
        """Get latest sync history"""
        with self.get_session() as session:
            stmt = select(SyncHistory)
            if account_id:
                stmt = stmt.where(SyncHistory.account_id == account_id)
            stmt = stmt.order_by(SyncHistory.started_at.desc()).limit(1)
            return session.scalar(stmt)
    
    # Statistics
    def get_stats(self) -> dict:
        """Get database statistics"""
        with self.get_session() as session:
            total_accounts = session.scalar(select(func.count()).select_from(Account))
            total_articles = session.scalar(select(func.count()).select_from(Article))
            active_accounts = session.scalar(
                select(func.count()).select_from(Account).where(Account.is_active == True)
            )
            
            from sqlalchemy import cast, String
            uncategorized_count = session.scalar(
                select(func.count()).select_from(Article).where(
                    or_(
                        Article.tags.is_(None),
                        cast(Article.tags, String) == '[]',
                        cast(Article.tags, String) == 'null'
                    )
                )
            )
            categorized_count = total_articles - uncategorized_count
            
            return {
                "total_accounts": total_accounts,
                "active_accounts": active_accounts,
                "total_articles": total_articles,
                "uncategorized_count": uncategorized_count,
                "categorized_count": categorized_count
            }


# Global database instance
db = Database()
