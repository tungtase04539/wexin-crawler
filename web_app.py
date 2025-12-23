"""
Web Dashboard for WeChat Content Integration System
Flask + HTMX + Alpine.js + TailwindCSS
"""
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
import json
from pathlib import Path

try:
    from config import settings
    from database import db
    from sync_manager import sync_manager
    from wewe_client import wewe_client
    from metrics_fetcher import metrics_fetcher
    from pdf_service import pdf_service
    from logger import setup_logger
    logger = setup_logger(__name__)
except Exception as e:
    import traceback
    import sys
    print("CRITICAL: Failed to import internal modules!", file=sys.stderr)
    traceback.print_exc()
    # Re-raise to let Vercel handle the crash but now we have logs
    raise e

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'wewe-rss-integration-secret-key'
app.config['JSON_AS_ASCII'] = False  # Support Chinese characters

# Initialize database
# Database tables will be created on first request or in main block
# if not db.inspector.get_table_names():
#    db.create_tables()


# ============================================================================
# PAGES
# ============================================================================

@app.route('/')
def index():
    """Dashboard home page"""
    return render_template('dashboard.html')


@app.route('/accounts')
def accounts_page():
    """Accounts management page"""
    return render_template('accounts.html')


@app.route('/articles')
def articles_page():
    """Articles browser page"""
    return render_template('articles.html')


@app.route('/sync')
def sync_page():
    """Sync management page"""
    return render_template('sync.html')


@app.route('/export')
def export_page():
    """Export interface page"""
    return render_template('export.html')


@app.route('/settings')
def settings_page():
    """Settings page"""
    return render_template('settings.html')


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/stats')
def api_stats():
    """Get dashboard statistics"""
    try:
        stats = db.get_stats()
        
        # Get recent sync
        latest_sync = db.get_latest_sync()
        last_sync_time = latest_sync.started_at.isoformat() + 'Z' if latest_sync else None
        
        # Get recent articles count (last 24h)
        recent_articles = db.get_recent_articles(limit=1000)
        yesterday = datetime.utcnow() - timedelta(days=1)
        new_today = len([a for a in recent_articles if a.created_at > yesterday])
        
        return jsonify({
            'success': True,
            'stats': {
                'total_accounts': stats['total_accounts'],
                'active_accounts': stats['active_accounts'],
                'total_articles': stats['total_articles'],
                'uncategorized_count': stats.get('uncategorized_count', 0),
                'categorized_count': stats.get('categorized_count', 0),
                'new_today': new_today,
                'last_sync': last_sync_time
            }
        })
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/accounts')
def api_accounts():
    """Get all accounts"""
    try:
        accounts = db.get_all_accounts(active_only=False)
        
        accounts_data = []
        for account in accounts:
            articles_count = len(db.get_articles_by_account(account.id))
            latest_sync = db.get_latest_sync(account.id)
            
            accounts_data.append({
                'id': account.id,
                'feed_id': account.feed_id,
                'name': account.name,
                'description': account.description,
                'avatar_url': account.avatar_url,
                'is_active': account.is_active,
                'articles_count': articles_count,
                'created_at': account.created_at.isoformat() + 'Z',
                'updated_at': account.updated_at.isoformat() + 'Z',
                'last_sync': latest_sync.started_at.isoformat() + 'Z' if latest_sync else None,
                'last_sync_status': latest_sync.status if latest_sync else None
            })
        
        return jsonify({
            'success': True,
            'accounts': accounts_data
        })
    except Exception as e:
        logger.error(f"Failed to get accounts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/articles/<int:article_id>/summarize', methods=['POST'])
def api_summarize_article(article_id):
    """Generate AI summary for an article"""
    try:
        from ai_summarizer import ai_summarizer
        from models import Article
        with db.get_session() as session:
            article = session.get(Article, article_id)
            if not article:
                return jsonify({'success': False, 'message': 'Article not found'}), 404
            
            if not settings.gemini_api_key:
                return jsonify({'success': False, 'message': 'Gemini API key not configured'}), 400

            # Use full content if available, else summary
            text_to_summarize = article.content or article.summary
            if not text_to_summarize:
                return jsonify({'success': False, 'message': 'No content to summarize'}), 400

            # Get summary and tags from AI
            result = ai_summarizer.summarize(text_to_summarize)
            summary = result.get('summary')
            tags = result.get('tags', [])

            if summary:
                article.ai_summary = summary
                if tags:
                    article.tags = tags
                
                session.commit()
                
                # Optional: Sync to Lark if enabled
                lark_status = None
                sync_msg = ""
                if settings.enable_lark_sync:
                    try:
                        from lark_service import lark_service
                        article.calculate_scores()
                        sync_success = lark_service.upsert_article(article)
                        if sync_success:
                            lark_status = "synced"
                            sync_msg = " and pushed to Lark"
                        else:
                            lark_status = "failed"
                            sync_msg = " but failed to push to Lark"
                    except Exception as le:
                        logger.error(f"Auto-sync to Lark failed: {le}")
                        lark_status = "failed"
                        sync_msg = " but Lark sync encountered an error"

                return jsonify({
                    'success': True, 
                    'message': f'Summary and tags generated{sync_msg}',
                    'ai_summary': summary,
                    'tags': tags,
                    'lark_sync': lark_status
                })
            else:
                return jsonify({'success': False, 'message': 'Failed to generate summary'}), 500
    except Exception as e:
        logger.error(f"Failed to summarize article {article_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/accounts', methods=['POST'])
def api_create_account():
    """Create new account"""
    try:
        data = request.get_json()
        feed_id = data.get('feed_id')
        name = data.get('name')
        
        if not feed_id:
            return jsonify({'success': False, 'error': 'feed_id is required'}), 400
        
        result = sync_manager.add_account(
            feed_id=feed_id,
            name=name,
            initial_sync=data.get('initial_sync', True)
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to create account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/accounts/<int:account_id>', methods=['PUT'])
def api_update_account(account_id):
    """Update account"""
    try:
        data = request.get_json()
        
        account = db.update_account(account_id, **data)
        
        if account:
            return jsonify({
                'success': True,
                'account': {
                    'id': account.id,
                    'name': account.name,
                    'is_active': account.is_active
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Account not found'}), 404
    except Exception as e:
        logger.error(f"Failed to update account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def api_delete_account(account_id):
    """Delete account"""
    try:
        # Note: This would need to be implemented in database.py
        # For now, just deactivate
        account = db.update_account(account_id, is_active=False)
        
        if account:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Account not found'}), 404
    except Exception as e:
        logger.error(f"Failed to delete account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/articles')
def api_articles():
    """Get articles with filters"""
    try:
        account_id = request.args.get('account_id')
        search = request.args.get('search', '')
        tag = request.args.get('tag', '')
        categorized = request.args.get('categorized', type=int)
        heat_level = request.args.get('heat_level', '') # low, mid, high
        engagement_level = request.args.get('engagement_level', '') # low, mid, high
        min_heat = request.args.get('min_heat', type=float)
        min_engagement = request.args.get('min_engagement', type=float)
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        sort_by = request.args.get('sort', 'published_at_desc')
        
        # Get articles
        with db.get_session() as session:
            from models import Article
            from sqlalchemy import select, or_, and_
            
            stmt = select(Article)
            
            # Apply filters
            filters = []
            if account_id:
                filters.append(Article.account_id == account_id)
            if search:
                filters.append(or_(
                    Article.title.ilike(f"%{search}%"),
                    Article.content.ilike(f"%{search}%"),
                    Article.summary.ilike(f"%{search}%")
                ))
            if tag:
                filters.append(Article.tags.contains([tag]))
            
            if categorized is not None:
                from sqlalchemy import cast, String
                if categorized == 1:
                    filters.append(and_(
                        Article.tags.is_not(None), 
                        cast(Article.tags, String) != '[]',
                        cast(Article.tags, String) != 'null'
                    ))
                else:  # categorized == 0
                    filters.append(or_(
                        Article.tags.is_(None),
                        cast(Article.tags, String) == '[]',
                        cast(Article.tags, String) == 'null'
                    ))
            
            # Map levels to ranges
            # Heat: Low (<60), Mid (60-100), High (>100)
            if heat_level == 'low':
                filters.append(Article.heat_score < 60)
            elif heat_level == 'mid':
                filters.append(and_(Article.heat_score >= 60, Article.heat_score <= 100))
            elif heat_level == 'high':
                filters.append(Article.heat_score > 100)
            elif min_heat is not None:
                filters.append(Article.heat_score >= min_heat)
                
            # Engagement: Low (<30), Mid (30-50), High (>50)
            if engagement_level == 'low':
                filters.append(Article.engagement_rate < 30)
            elif engagement_level == 'mid':
                filters.append(and_(Article.engagement_rate >= 30, Article.engagement_rate <= 50))
            elif engagement_level == 'high':
                filters.append(Article.engagement_rate > 50)
            elif min_engagement is not None:
                filters.append(Article.engagement_rate >= min_engagement)
                
            if filters:
                stmt = stmt.where(and_(*filters))
                
            # Apply sorting
            if sort_by == 'published_at_desc':
                stmt = stmt.order_by(Article.published_at.desc())
            elif sort_by == 'published_at_asc':
                stmt = stmt.order_by(Article.published_at.asc())
            elif sort_by == 'heat_score':
                stmt = stmt.order_by(Article.heat_score.desc())
            elif sort_by == 'engagement_rate':
                stmt = stmt.order_by(Article.engagement_rate.desc())
                
            # Apply pagination
            if not search and not tag and min_heat is None and min_engagement is None:
                stmt = stmt.offset(offset).limit(limit)
            
            articles = session.scalars(stmt).all()
        
            articles_data = []
            for article in articles:
                articles_data.append({
                    'id': article.id,
                    'title': article.title,
                    'author': article.author,
                    'url': article.url,
                    'summary': article.summary,
                    'ai_summary': article.ai_summary,
                    'tags': article.tags,
                    'cover_image': article.cover_image,
                    'published_at': article.published_at.isoformat() + 'Z' if article.published_at else None,
                    'word_count': article.word_count,
                    'reading_time_minutes': article.reading_time_minutes,
                    'is_read': article.is_read,
                    'is_favorite': article.is_favorite,
                    'created_at': article.created_at.isoformat() + 'Z',
                    # Include scores for the list view
                    'heat_score': round(article.heat_score or 0, 1),
                    'engagement_rate': round(article.engagement_rate or 0, 1),
                    'is_simulated': article.is_simulated,
                    'has_api_key': bool(settings.jizhile_api_key)
                })
        
        return jsonify({
            'success': True,
            'articles': articles_data,
            'total': len(articles_data)
        })
    except Exception as e:
        import traceback
        error_tb = traceback.format_exc()
        logger.error(f"Failed to get articles: {e}\n{error_tb}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'traceback': error_tb if settings.debug else None
        }), 500


@app.route('/api/articles/<int:article_id>')
def api_article_detail(article_id):
    """Get article detail"""
    try:
        with db.get_session() as session:
            from models import Article
            article = session.get(Article, article_id)
            
            if not article:
                return jsonify({'success': False, 'error': 'Article not found'}), 404
            
            return jsonify({
                'success': True,
                'article': {
                    'id': article.id,
                    'title': article.title,
                    'author': article.author,
                    'url': article.url,
                    'content': article.content,
                    'content_html': article.content_html,
                    'summary': article.summary,
                    'ai_summary': article.ai_summary,
                    'tags': article.tags,
                    'cover_image': article.cover_image,
                    'images': article.images,
                    'published_at': article.published_at.isoformat() + 'Z' if article.published_at else None,
                    'word_count': article.word_count,
                    'reading_time_minutes': article.reading_time_minutes,
                    'created_at': article.created_at.isoformat() + 'Z',
                    # Metrics & Scores
                    'read_count': article.read_count or 0,
                    'like_count': article.like_count or 0,
                    'wow_count': article.wow_count or 0,
                    'comment_count': article.comment_count or 0,
                    'share_count': article.share_count or 0,
                    'favorite_count': article.favorite_count or 0,
                    'engagement_rate': round(article.engagement_rate or 0, 2),
                    'virality_index': round(article.virality_index or 0, 2),
                    'content_value_index': round(article.content_value_index or 0, 2),
                    'heat_score': round(article.heat_score or 0, 2),
                    'is_simulated': article.is_simulated,
                    'has_api_key': bool(settings.jizhile_api_key),
                    'metrics_updated_at': article.metrics_updated_at.isoformat() + 'Z' if article.metrics_updated_at else None
                }
            })
    except Exception as e:
        logger.error(f"Failed to get article detail: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/articles/<int:article_id>/pdf')
def download_article_pdf(article_id):
    """Generate and download PDF for an article"""
    try:
        from models import Article
        with db.get_session() as session:
            article = session.get(Article, article_id)
            if not article:
                return jsonify({"success": False, "error": "Article not found"}), 404
            
            # Use specific name for PDF
            filename = f"article_{article_id}.pdf"
            output_path = settings.exports_dir / filename
            settings.exports_dir.mkdir(parents=True, exist_ok=True)
            
            import asyncio
            # We use the article's high-quality HTML
            # Note: This might need some prepending of Styles for Playwright
            success = asyncio.run(pdf_service.generate_pdf(article.content_html, str(output_path)))
            
            if success:
                return send_file(str(output_path), as_attachment=True, download_name=f"{article.title}.pdf")
            else:
                return jsonify({"success": False, "error": "Failed to generate PDF"}), 500
    except Exception as e:
        logger.error(f"PDF Export error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/articles/<int:article_id>/lark-sync', methods=['POST'])
def sync_article_to_lark(article_id):
    """Sync a single article to Lark Bitable"""
    try:
        from models import Article
        from lark_service import lark_service
        with db.get_session() as session:
            article = session.get(Article, article_id)
            if not article:
                return jsonify({"success": False, "error": "Article not found"}), 404
            
            # Ensure scores are fresh before sync
            article.calculate_scores()
            
            success = lark_service.upsert_article(article)
            if success:
                return jsonify({"success": True, "message": "Article synced to Lark successfully"})
            else:
                return jsonify({"success": False, "error": "Failed to sync to Lark. Check logs for details."}), 500
    except Exception as e:
        logger.error(f"Lark sync error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/articles/<int:article_id>/update-metrics', methods=['POST'])
def update_article_metrics(article_id):
    """Update metrics for a single article and recalculate scores"""
    try:
        from models import Article
        with db.get_session() as session:
            article = session.get(Article, article_id)
            if not article:
                return jsonify({"success": False, "error": "Article not found"}), 404
            
            metrics = metrics_fetcher.fetch_article_metrics(article.url)
            if metrics:
                # Update article metrics
                for key, val in metrics.items():
                    if hasattr(article, key):
                        setattr(article, key, val)
                article.is_simulated = metrics.get('is_simulated', False)
                article.metrics_updated_at = datetime.utcnow()
            else:
                logger.info(f"No new metrics for {article_id}, just recalculating scores.")
                
            # Always re-calculate scores based on whatever we have in DB
            article.calculate_scores()
            session.commit()
            
            # Optional: Sync to Lark if enabled
            lark_status = None
            if settings.enable_lark_sync:
                try:
                    from lark_service import lark_service
                    lark_service.upsert_article(article)
                    lark_status = "synced"
                except Exception as le:
                    logger.error(f"Auto-sync to Lark failed: {le}")
                    lark_status = "failed"

            return jsonify({
                "success": True, 
                "metrics_updated": bool(metrics),
                "scores": {
                    "engagement_rate": round(article.engagement_rate or 0, 2),
                    "virality_index": round(article.virality_index or 0, 2),
                    "content_value_index": round(article.content_value_index or 0, 2),
                    "heat_score": round(article.heat_score or 0, 2)
                },
                "is_simulated": article.is_simulated,
                "lark_sync": lark_status
            })
    except Exception as e:
        logger.error(f"Manual metrics update error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/sync/<feed_id>', methods=['POST'])
def api_sync_account(feed_id):
    """Trigger sync for an account"""
    try:
        data = request.get_json() or {}
        full_sync = data.get('full_sync', False)
        
        result = sync_manager.sync_account(
            feed_id=feed_id,
            sync_type='manual',
            full_sync=full_sync
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to sync account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sync/all', methods=['POST'])
def api_sync_all():
    """Trigger sync for all accounts"""
    try:
        result = sync_manager.sync_all_accounts(sync_type='manual')
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to sync all: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sync/history')
def api_sync_history():
    """Get sync history"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        with db.get_session() as session:
            from models import SyncHistory, Account
            from sqlalchemy import select
            
            stmt = select(SyncHistory).order_by(SyncHistory.started_at.desc()).limit(limit)
            syncs = list(session.scalars(stmt).all())
            
            history_data = []
            for sync in syncs:
                account_name = None
                if sync.account_id:
                    account = session.get(Account, sync.account_id)
                    account_name = account.name if account else None
                
                history_data.append({
                    'id': sync.id,
                    'account_name': account_name or 'All Accounts',
                    'sync_type': sync.sync_type,
                    'status': sync.status,
                    'articles_new': sync.articles_new,
                    'articles_updated': sync.articles_updated,
                    'articles_failed': sync.articles_failed,
                    'started_at': sync.started_at.isoformat(),
                    'duration_seconds': sync.duration_seconds
                })
            
            return jsonify({
                'success': True,
                'history': history_data
            })
    except Exception as e:
        logger.error(f"Failed to get sync history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export', methods=['POST'])
def api_export():
    """Export articles"""
    try:
        data = request.get_json()
        format_type = data.get('format', 'json')
        feed_id = data.get('feed_id')
        
        # Get articles
        if feed_id:
            account = db.get_account_by_feed_id(feed_id)
            if not account:
                return jsonify({'success': False, 'error': 'Account not found'}), 404
            articles = db.get_articles_by_account(account.id)
            filename = f"{feed_id}_{datetime.now().strftime('%Y%m%d')}.{format_type}"
        else:
            articles = db.get_recent_articles(limit=1000)
            filename = f"all_articles_{datetime.now().strftime('%Y%m%d')}.{format_type}"
        
        # Export
        output_path = settings.exports_dir / filename
        
        if format_type == 'json':
            data_list = []
            for article in articles:
                data_list.append({
                    'id': article.id,
                    'title': article.title,
                    'author': article.author,
                    'url': article.url,
                    'content': article.content,
                    'published_at': article.published_at.isoformat() if article.published_at else None
                })
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data_list, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': str(output_path),
            'count': len(articles)
        })
    except Exception as e:
        logger.error(f"Failed to export: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<filename>')
def api_download(filename):
    """Download exported file"""
    try:
        file_path = settings.exports_dir / filename
        if not file_path.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Failed to download: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    logger.info(f"Starting web dashboard on {settings.web_host}:{settings.web_port}")
    app.run(
        host=settings.web_host,
        port=settings.web_port,
        debug=settings.web_debug
    )
