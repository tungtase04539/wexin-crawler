"""
Database models for WeChat Content Integration System
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey, JSON, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Account(Base):
    """WeChat Official Account model"""
    __tablename__ = "accounts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    feed_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    feed_url: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    articles: Mapped[List["Article"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    sync_histories: Mapped[List["SyncHistory"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name='{self.name}', feed_id='{self.feed_id}')>"


class Article(Base):
    """Article/Post model"""
    __tablename__ = "articles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    
    # Article metadata
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    guid: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    
    # Content
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Images and Media
    cover_image: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    images: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of image URLs
    videos: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of video URLs
    
    # Metadata
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reading_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Tags and categories
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    categories: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # System fields
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metrics (Jizhile API)
    read_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    like_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    wow_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0) # 在看
    comment_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    share_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    favorite_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0) # 收藏
    
    # Computed Scores
    engagement_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    virality_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    content_value_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    heat_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    
    metrics_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account: Mapped["Account"] = relationship(back_populates="articles")
    
    def __repr__(self) -> str:
        return f"<Article(id={self.id}, title='{self.title[:50]}...', account_id={self.account_id})>"
    
    def calculate_reading_time(self) -> int:
        """Calculate estimated reading time in minutes (assuming 200 words/minute)"""
        if self.word_count:
            return max(1, self.word_count // 200)
        return 0

    def calculate_scores(self):
        """
        Calculate importance scores based on engagement metrics.
        Formulas based on: https://mp.weixin.qq.com/s/zTpijiDuZQsWPJxMcfW-2g
        """
        read = max(1, self.read_count or 0)
        likes = self.like_count or 0
        wow = self.wow_count or 0
        comments = self.comment_count or 0
        shares = self.share_count or 0
        favorites = self.favorite_count or 0

        # 1. Engagement Rate (互动率): (Likes + Wow) / Read Count * 1000
        self.engagement_rate = (likes + wow) / read * 1000

        # 2. Virality Index (传播指数): (Shares * 2 + Wow) / Read Count * 1000
        self.virality_index = (shares * 2 + wow) / read * 1000

        # 3. Content Value Index (内容价值指数): (Favorites * 2 + Comments) / Read Count * 1000
        self.content_value_index = (favorites * 2 + comments) / read * 1000

        # 4. Comprehensive Heat Score (综合热度分): 
        # (Likes*1 + Wow*2 + Comments*3 + Favorites*4 + Shares*5) / Read Count * 100
        self.heat_score = (likes * 1 + wow * 2 + comments * 3 + favorites * 4 + shares * 5) / read * 100



class SyncHistory(Base):
    """Sync history tracking"""
    __tablename__ = "sync_histories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), nullable=True, index=True)
    
    # Sync details
    sync_type: Mapped[str] = mapped_column(String(50))  # 'manual', 'auto', 'full'
    status: Mapped[str] = mapped_column(String(50))  # 'success', 'failed', 'partial'
    
    # Statistics
    articles_fetched: Mapped[int] = mapped_column(Integer, default=0)
    articles_new: Mapped[int] = mapped_column(Integer, default=0)
    articles_updated: Mapped[int] = mapped_column(Integer, default=0)
    articles_failed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    account: Mapped[Optional["Account"]] = relationship(back_populates="sync_histories")
    
    def __repr__(self) -> str:
        return f"<SyncHistory(id={self.id}, status='{self.status}', articles_new={self.articles_new})>"
