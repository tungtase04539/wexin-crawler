"""
Command-line interface for WeChat Content Integration System
"""
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from pathlib import Path

from config import settings
from logger import setup_logger
from database import db
from sync_manager import sync_manager
from wewe_client import wewe_client

logger = setup_logger(__name__)
console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """WeChat Content Integration System - CLI Tool"""
    # Initialize database
    db.create_tables()


@cli.command()
@click.option('--feed-id', required=True, help='Feed ID of the WeChat account')
@click.option('--name', help='Account name (optional)')
@click.option('--no-sync', is_flag=True, help='Skip initial sync')
def add(feed_id: str, name: str, no_sync: bool):
    """Add a new WeChat account to track"""
    console.print(f"\n[bold cyan]Adding account:[/bold cyan] {feed_id}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Adding account...", total=None)
        
        result = sync_manager.add_account(
            feed_id=feed_id,
            name=name,
            initial_sync=not no_sync
        )
        
        progress.update(task, completed=True)
    
    if result["success"]:
        console.print(f"\n[bold green]✓[/bold green] Account added: {result['account']}")
        
        if not no_sync and "sync_result" in result:
            stats = result["sync_result"].get("stats", {})
            console.print(f"  • New articles: {stats.get('new', 0)}")
            console.print(f"  • Updated: {stats.get('updated', 0)}")
    else:
        console.print(f"\n[bold red]✗[/bold red] Failed: {result.get('error', 'Unknown error')}")


@cli.command()
@click.option('--feed-id', help='Sync specific feed ID')
@click.option('--all', 'sync_all', is_flag=True, help='Sync all accounts')
@click.option('--full', is_flag=True, help='Full sync (update existing articles)')
def sync(feed_id: str, sync_all: bool, full: bool):
    """Sync articles from WeWe-RSS"""
    
    if not feed_id and not sync_all:
        console.print("[bold red]Error:[/bold red] Please specify --feed-id or --all")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        if sync_all:
            task = progress.add_task("Syncing all accounts...", total=None)
            result = sync_manager.sync_all_accounts(sync_type="manual")
            progress.update(task, completed=True)
            
            console.print(f"\n[bold green]✓[/bold green] Synced {result['total_accounts']} accounts")
            console.print(f"  • New articles: {result['total_new']}")
            console.print(f"  • Updated: {result['total_updated']}")
            console.print(f"  • Failed: {result['total_failed']}")
        else:
            task = progress.add_task(f"Syncing {feed_id}...", total=None)
            result = sync_manager.sync_account(
                feed_id=feed_id,
                sync_type="manual",
                full_sync=full
            )
            progress.update(task, completed=True)
            
            if result["success"]:
                stats = result["stats"]
                console.print(f"\n[bold green]✓[/bold green] Sync completed: {result['account']}")
                console.print(f"  • Fetched: {stats['fetched']}")
                console.print(f"  • New: {stats['new']}")
                console.print(f"  • Updated: {stats['updated']}")
                console.print(f"  • Skipped: {stats['skipped']}")
                console.print(f"  • Failed: {stats['failed']}")
            else:
                console.print(f"\n[bold red]✗[/bold red] Sync failed: {result.get('error', 'Unknown error')}")


@cli.command()
def accounts():
    """List all tracked accounts"""
    all_accounts = db.get_all_accounts(active_only=False)
    
    if not all_accounts:
        console.print("\n[yellow]No accounts found[/yellow]")
        return
    
    table = Table(title="\nWeChat Accounts", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim")
    table.add_column("Feed ID")
    table.add_column("Name", style="green")
    table.add_column("Articles", justify="right")
    table.add_column("Status")
    table.add_column("Last Updated")
    
    for account in all_accounts:
        article_count = len(db.get_articles_by_account(account.id))
        status = "✓ Active" if account.is_active else "✗ Inactive"
        status_style = "green" if account.is_active else "red"
        
        table.add_row(
            str(account.id),
            account.feed_id,
            account.name,
            str(article_count),
            f"[{status_style}]{status}[/{status_style}]",
            account.updated_at.strftime("%Y-%m-%d %H:%M")
        )
    
    console.print(table)


@cli.command()
@click.option('--limit', default=20, help='Number of articles to show')
@click.option('--feed-id', help='Filter by feed ID')
def articles(limit: int, feed_id: str):
    """List recent articles"""
    
    if feed_id:
        account = db.get_account_by_feed_id(feed_id)
        if not account:
            console.print(f"[bold red]Error:[/bold red] Account not found: {feed_id}")
            return
        article_list = db.get_articles_by_account(account.id, limit=limit)
        title = f"\nRecent Articles - {account.name}"
    else:
        article_list = db.get_recent_articles(limit=limit)
        title = "\nRecent Articles - All Accounts"
    
    if not article_list:
        console.print("\n[yellow]No articles found[/yellow]")
        return
    
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Title", style="green", width=50)
    table.add_column("Author", width=15)
    table.add_column("Published", width=16)
    table.add_column("Words", justify="right", width=8)
    
    for article in article_list:
        title_text = article.title[:47] + "..." if len(article.title) > 50 else article.title
        published = article.published_at.strftime("%Y-%m-%d %H:%M") if article.published_at else "N/A"
        
        table.add_row(
            str(article.id),
            title_text,
            article.author or "Unknown",
            published,
            str(article.word_count or 0)
        )
    
    console.print(table)


@cli.command()
def stats():
    """Show database statistics"""
    db_stats = db.get_stats()
    
    console.print("\n[bold cyan]Database Statistics[/bold cyan]")
    console.print(f"  • Total Accounts: {db_stats['total_accounts']}")
    console.print(f"  • Active Accounts: {db_stats['active_accounts']}")
    console.print(f"  • Total Articles: {db_stats['total_articles']}")
    
    # Get latest sync
    latest_sync = db.get_latest_sync()
    if latest_sync:
        console.print(f"\n[bold cyan]Latest Sync[/bold cyan]")
        console.print(f"  • Status: {latest_sync.status}")
        console.print(f"  • Started: {latest_sync.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"  • New Articles: {latest_sync.articles_new}")
        console.print(f"  • Duration: {latest_sync.duration_seconds}s" if latest_sync.duration_seconds else "  • Duration: N/A")


@cli.command()
def test():
    """Test connection to WeWe-RSS"""
    console.print("\n[bold cyan]Testing connection to WeWe-RSS...[/bold cyan]")
    console.print(f"URL: {settings.wewe_rss_url}")
    if wewe_client.test_connection():
        console.print("\n[bold green]✓[/bold green] Connection successful!")
    else:
        console.print("\n[bold red]✗[/bold red] Connection failed!")


@cli.command()
@click.option('--limit', default=10, help='Max articles to update')
def update_metrics(limit: int):
    """Update engagement metrics for articles"""
    from metrics_fetcher import metrics_fetcher
    from datetime import datetime
    
    console.print(f"\n[bold cyan]Updating metrics for {limit} articles...[/bold cyan]")
    
    if not metrics_fetcher.enabled:
        console.print("[yellow]Warning: Jizhile API Key not configured in .env[/yellow]")
        return

    # Get articles (prefer ones not updated recently)
    # Since we need to join logic or simple query, for now just get recent ones
    articles = db.get_recent_articles(limit=limit)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Updating metrics...", total=len(articles))
        
        updated_count = 0
        for article in articles:
            progress.update(task, description=f"Checking: {article.title[:20]}...")
            
            metrics = metrics_fetcher.fetch_article_metrics(article.url)
            if metrics:
                db.update_article(
                    article.id,
                    read_count=metrics.get('read_count', article.read_count),
                    like_count=metrics.get('like_count', article.like_count),
                    wow_count=metrics.get('wow_count', article.wow_count),
                    comment_count=metrics.get('comment_count', article.comment_count),
                    share_count=metrics.get('share_count', article.share_count),
                    favorite_count=metrics.get('favorite_count', article.favorite_count),
                    metrics_updated_at=datetime.utcnow()
                )
                # Re-fetch and calculate scores
                art = db.get_article_by_url(article.url)
                art.calculate_scores()
                db.update_article(
                    art.id,
                    engagement_rate=art.engagement_rate,
                    virality_index=art.virality_index,
                    content_value_index=art.content_value_index,
                    heat_score=art.heat_score
                )
                updated_count += 1
            
            progress.advance(task)
            
    console.print(f"\n[bold green]✓[/bold green] Updated metrics for {updated_count} articles")


@cli.command()
@click.option('--format', 'export_format', default='json', type=click.Choice(['json', 'csv']), help='Export format')
@click.option('--feed-id', help='Export specific feed')
@click.option('--output', help='Output file path')
def export(export_format: str, feed_id: str, output: str):
    """Export articles to file"""
    import json
    import csv
    from datetime import datetime
    
    # Get articles
    if feed_id:
        account = db.get_account_by_feed_id(feed_id)
        if not account:
            console.print(f"[bold red]Error:[/bold red] Account not found: {feed_id}")
            return
        article_list = db.get_articles_by_account(account.id)
        filename = f"{feed_id}_{datetime.now().strftime('%Y%m%d')}"
    else:
        article_list = db.get_recent_articles(limit=1000)
        filename = f"all_articles_{datetime.now().strftime('%Y%m%d')}"
    
    if not article_list:
        console.print("[yellow]No articles to export[/yellow]")
        return
    
    # Determine output path
    if output:
        output_path = Path(output)
    else:
        output_path = settings.exports_dir / f"{filename}.{export_format}"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export
    console.print(f"\n[bold cyan]Exporting {len(article_list)} articles...[/bold cyan]")
    
    if export_format == 'json':
        data = []
        for article in article_list:
            data.append({
                "id": article.id,
                "title": article.title,
                "author": article.author,
                "url": article.url,
                "content": article.content,
                "summary": article.summary,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "word_count": article.word_count,
                "created_at": article.created_at.isoformat()
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    elif export_format == 'csv':
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Title', 'Author', 'URL', 'Published', 'Word Count'])
            
            for article in article_list:
                writer.writerow([
                    article.id,
                    article.title,
                    article.author or '',
                    article.url,
                    article.published_at.isoformat() if article.published_at else '',
                    article.word_count or 0
                ])
    
    console.print(f"[bold green]✓[/bold green] Exported to: {output_path}")


if __name__ == '__main__':
    cli()
