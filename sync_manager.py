"""
Sync manager for orchestrating content synchronization
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from config import settings
from logger import setup_logger
from database import db
from wewe_client import wewe_client
from content_processor import content_processor
from metrics_fetcher import metrics_fetcher
from models import Account, Article, SyncHistory

logger = setup_logger(__name__)


class SyncManager:
    """Manage synchronization of articles from WeWe-RSS"""
    
    def __init__(self):
        self.max_articles = settings.max_articles_per_sync
    
    def sync_account(
        self,
        feed_id: str,
        sync_type: str = "manual",
        full_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Sync articles for a specific account
        
        Args:
            feed_id: Feed/account ID
            sync_type: Type of sync (manual, auto)
            full_sync: Whether to fetch all articles or just new ones
        
        Returns:
            Sync results dictionary
        """
        logger.info(f"Starting sync for feed: {feed_id} (type: {sync_type})")
        
        # Get or create account
        account = db.get_account_by_feed_id(feed_id)
        if not account:
            logger.info(f"Account not found, creating new account for feed: {feed_id}")
            # Fetch feed to get account info
            feed_data = wewe_client.fetch_feed(feed_id)
            if not feed_data:
                logger.error(f"Failed to fetch feed data for {feed_id}")
                return {
                    "success": False,
                    "error": "Failed to fetch feed data"
                }
            
            account = db.create_account(
                feed_id=feed_id,
                name=feed_data.get("title", feed_id),
                feed_url=settings.get_feed_url(feed_id),
                description=feed_data.get("description", "")
            )
        
        # Store account info before session closes
        account_id = account.id
        account_name = account.name
        
        # Create sync history record
        sync_history = db.create_sync_history(
            account_id=account_id,
            sync_type=sync_type
        )
        
        try:
            # Fetch articles from feed
            entries = wewe_client.get_feed_entries(
                feed_id,
                limit=None if full_sync else self.max_articles
            )
            
            stats = {
                "fetched": len(entries),
                "new": 0,
                "updated": 0,
                "failed": 0,
                "skipped": 0
            }
            
            # Process each entry
            for entry in entries:
                try:
                    # Process entry
                    article_data = content_processor.process_article(entry)
                    
                    # Ensure author fallback to account name if still unknown
                    if not article_data.get("author") or article_data["author"].lower() == "unknown":
                        article_data["author"] = account_name
                    
                    # Check if article already exists
                    existing_article = db.get_article_by_url(article_data["url"])
                    
                    if existing_article:
                        # Skip if not full sync
                        if not full_sync:
                            stats["skipped"] += 1
                            continue
                        
                        # Update existing article if full_sync is enabled
                        db.update_article(existing_article.id, **article_data)
                        article_id = existing_article.id
                        stats["updated"] += 1
                        logger.debug(f"Updated article: {article_data['title'][:50]}")
                    else:
                        # Create new article
                        article = db.create_article(
                            account_id=account_id,
                            **article_data
                        )
                        article_id = article.id
                        stats["new"] += 1
                        logger.debug(f"Created new article: {article_data['title'][:50]}")
                    
                    # Calculate scores for all processed articles (new or updated)
                    try:
                        metrics = metrics_fetcher.fetch_article_metrics(article_data["url"])
                        with db.get_session() as session:
                            from models import Article as ArticleModel
                            article_db = session.get(ArticleModel, article_id)
                            if article_db:
                                if metrics:
                                    for key, val in metrics.items():
                                        if hasattr(article_db, key):
                                            setattr(article_db, key, val)
                                    article_db.is_simulated = metrics.get('is_simulated', False)
                                    article_db.metrics_updated_at = datetime.utcnow()
                                article_db.calculate_scores()
                                session.commit()
                    except Exception as e:
                        logger.error(f"Failed to calculate scores for article {article_id}: {e}")
                
                except Exception as e:
                    logger.error(f"Failed to process entry: {e}")
                    stats["failed"] += 1
            
            # Update sync history
            db.update_sync_history(
                sync_history.id,
                status="success",
                articles_fetched=stats["fetched"],
                articles_new=stats["new"],
                articles_updated=stats["updated"],
                articles_failed=stats["failed"],
                completed_at=datetime.utcnow()
            )
            
            logger.info(
                f"Sync completed for {feed_id}: "
                f"{stats['new']} new, {stats['updated']} updated, "
                f"{stats['skipped']} skipped, {stats['failed']} failed"
            )
            
            return {
                "success": True,
                "account": account_name,
                "stats": stats
            }
        
        except Exception as e:
            logger.error(f"Sync failed for {feed_id}: {e}")
            
            # Update sync history with error
            db.update_sync_history(
                sync_history.id,
                status="failed",
                error_message=str(e),
                completed_at=datetime.utcnow()
            )
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_all_accounts(self, sync_type: str = "auto") -> Dict[str, Any]:
        """
        Sync all active accounts
        
        Args:
            sync_type: Type of sync (manual, auto)
        
        Returns:
            Overall sync results
        """
        logger.info("Starting sync for all accounts")
        
        accounts = db.get_all_accounts(active_only=True)
        
        if not accounts:
            logger.warning("No active accounts found")
            return {
                "success": True,
                "total_accounts": 0,
                "results": []
            }
        
        results = []
        for account in accounts:
            result = self.sync_account(
                account.feed_id,
                sync_type=sync_type
            )
            results.append({
                "feed_id": account.feed_id,
                "account": account.name,
                **result
            })
        
        # Calculate overall stats
        total_new = sum(r.get("stats", {}).get("new", 0) for r in results)
        total_updated = sum(r.get("stats", {}).get("updated", 0) for r in results)
        total_failed = sum(r.get("stats", {}).get("failed", 0) for r in results)
        
        logger.info(
            f"Sync all completed: {len(accounts)} accounts, "
            f"{total_new} new articles, {total_updated} updated, {total_failed} failed"
        )
        
        return {
            "success": True,
            "total_accounts": len(accounts),
            "total_new": total_new,
            "total_updated": total_updated,
            "total_failed": total_failed,
            "results": results
        }
    
    def add_account(
        self,
        feed_id: str,
        name: Optional[str] = None,
        initial_sync: bool = True
    ) -> Dict[str, Any]:
        """
        Add a new account to track
        
        Args:
            feed_id: Feed/account ID
            name: Account name (fetched if not provided)
            initial_sync: Whether to perform initial sync
        
        Returns:
            Result dictionary
        """
        logger.info(f"Adding new account: {feed_id}")
        
        # Check if account already exists
        existing = db.get_account_by_feed_id(feed_id)
        if existing:
            logger.warning(f"Account already exists: {feed_id}")
            return {
                "success": False,
                "error": "Account already exists"
            }
        
        # Fetch feed to get account info
        feed_data = wewe_client.fetch_feed(feed_id)
        if not feed_data:
            logger.error(f"Failed to fetch feed data for {feed_id}")
            return {
                "success": False,
                "error": "Failed to fetch feed data"
            }
        
        # Create account
        account = db.create_account(
            feed_id=feed_id,
            name=name or feed_data.get("title", feed_id),
            feed_url=settings.get_feed_url(feed_id),
            description=feed_data.get("description", "")
        )
        
        # Perform initial sync if requested
        if initial_sync:
            sync_result = self.sync_account(feed_id, sync_type="manual", full_sync=True)
            return {
                "success": True,
                "account": account.name,
                "sync_result": sync_result
            }
        
        return {
            "success": True,
            "account": account.name
        }


# Global sync manager instance
sync_manager = SyncManager()
