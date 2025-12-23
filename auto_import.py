"""
Auto-import all accounts from WeWe-RSS
This script fetches all available feeds from WeWe-RSS and adds them to the system
"""
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import requests
from bs4 import BeautifulSoup

from config import settings
from database import db
from sync_manager import sync_manager
from wewe_client import wewe_client
from logger import setup_logger

logger = setup_logger(__name__)
console = Console()


def get_all_feed_ids_from_wewe_rss():
    """
    Get all feed IDs from WeWe-RSS by parsing the all feeds
    
    Returns:
        List of unique feed IDs (account names)
    """
    try:
        # Fetch all feeds
        all_feeds = wewe_client.fetch_all_feeds(format="json")
        
        if not all_feeds or 'items' not in all_feeds:
            console.print("[red]Failed to fetch feeds from WeWe-RSS[/red]")
            return []
        
        # Extract unique feed IDs from items
        # Each item has metadata that can help identify the source account
        feed_ids = set()
        
        for item in all_feeds['items']:
            # Try to extract feed ID from item metadata
            # In WeWe-RSS, the feed ID is usually in the URL or metadata
            
            # Method 1: Try to get from URL
            url = item.get('url', '')
            if '/feeds/' in url:
                # Extract feed ID from URL like: /feeds/FEED_ID.rss
                parts = url.split('/feeds/')
                if len(parts) > 1:
                    feed_id = parts[1].split('.')[0]
                    if feed_id and feed_id != 'all':
                        feed_ids.add(feed_id)
            
            # Method 2: Try to get from author or other metadata
            author = item.get('author', '')
            if author:
                feed_ids.add(author)
        
        return list(feed_ids)
    
    except Exception as e:
        logger.error(f"Failed to get feed IDs: {e}")
        return []


def get_feed_ids_from_wewe_rss_ui():
    """
    Alternative method: Scrape feed IDs from WeWe-RSS web UI
    
    Returns:
        List of feed IDs
    """
    try:
        # Try to access WeWe-RSS feeds list page
        response = requests.get(f"{settings.wewe_rss_url}/feeds/all.json", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract unique authors/sources from items
            feed_ids = set()
            for item in data.get('items', []):
                # Get author as feed ID
                author = item.get('author', '')
                if author:
                    feed_ids.add(author)
                
                # Also try to extract from tags or categories
                tags = item.get('tags', [])
                if isinstance(tags, list):
                    feed_ids.update(tags)
            
            return list(feed_ids)
    
    except Exception as e:
        logger.error(f"Failed to scrape feed IDs: {e}")
        return []


def import_all_accounts():
    """
    Main function to import all accounts from WeWe-RSS
    """
    console.print("\n[bold cyan]🚀 Auto-Importing Accounts from WeWe-RSS[/bold cyan]\n")
    
    # Initialize database
    db.create_tables()
    
    # Test connection first
    console.print("[bold]Testing WeWe-RSS connection...[/bold]")
    if not wewe_client.test_connection():
        console.print("[red]✗ Cannot connect to WeWe-RSS. Please make sure it's running.[/red]")
        return
    
    console.print("[green]✓ Connected to WeWe-RSS[/green]\n")
    
    # Get all feeds
    console.print("[bold]Fetching all feeds...[/bold]")
    all_feeds = wewe_client.fetch_all_feeds(format="json")
    
    if not all_feeds or 'items' not in all_feeds:
        console.print("[red]✗ No feeds found[/red]")
        return
    
    items = all_feeds.get('items', [])
    console.print(f"[green]✓ Found {len(items)} articles in WeWe-RSS[/green]\n")
    
    # Extract unique feed sources
    # Since WeWe-RSS aggregates all feeds into one, we need to identify unique sources
    # We'll use the author field as the feed identifier
    
    feed_sources = {}
    for item in items:
        author = item.get('author', 'Unknown')
        
        # Handle author being a dict or string
        if isinstance(author, dict):
            author = author.get('name', 'Unknown')
        elif not isinstance(author, str):
            author = str(author) if author else 'Unknown'
        
        if author and author != 'Unknown':
            if author not in feed_sources:
                feed_sources[author] = {
                    'name': author,
                    'count': 0
                }
            feed_sources[author]['count'] += 1
    
    if not feed_sources:
        console.print("[yellow]⚠ Could not identify individual feed sources[/yellow]")
        console.print("[yellow]This might be because WeWe-RSS is aggregating all feeds[/yellow]")
        console.print("\n[bold]Suggestion:[/bold] Check WeWe-RSS UI at http://localhost:4000 to see individual feeds")
        return
    
    console.print(f"[bold cyan]Found {len(feed_sources)} unique feed sources:[/bold cyan]\n")
    
    for i, (feed_id, info) in enumerate(feed_sources.items(), 1):
        console.print(f"  {i}. {feed_id} ({info['count']} articles)")
    
    console.print()
    
    # Ask for confirmation
    if not console.input("\n[bold yellow]Import all these feeds? (y/n):[/bold yellow] ").lower().startswith('y'):
        console.print("[yellow]Import cancelled[/yellow]")
        return
    
    # Import accounts
    console.print("\n[bold cyan]Importing accounts...[/bold cyan]\n")
    
    success_count = 0
    failed_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Importing...", total=len(feed_sources))
        
        for feed_id, info in feed_sources.items():
            progress.update(task, description=f"Importing: {feed_id[:30]}...")
            
            try:
                # Check if already exists
                existing = db.get_account_by_feed_id(feed_id)
                if existing:
                    console.print(f"[yellow]⊘ Skipped: {feed_id} (already exists)[/yellow]")
                    progress.advance(task)
                    continue
                
                # Add account without initial sync (we'll sync all at once later)
                result = sync_manager.add_account(
                    feed_id=feed_id,
                    name=None,  # Will auto-fetch
                    initial_sync=False  # Don't sync yet
                )
                
                if result.get('success'):
                    console.print(f"[green]✓ Added: {feed_id}[/green]")
                    success_count += 1
                else:
                    console.print(f"[red]✗ Failed: {feed_id} - {result.get('error', 'Unknown error')}[/red]")
                    failed_count += 1
            
            except Exception as e:
                console.print(f"[red]✗ Error: {feed_id} - {str(e)}[/red]")
                failed_count += 1
            
            progress.advance(task)
    
    # Summary
    console.print(f"\n[bold cyan]Import Summary:[/bold cyan]")
    console.print(f"  • [green]Successfully imported: {success_count}[/green]")
    console.print(f"  • [red]Failed: {failed_count}[/red]")
    
    # Offer to sync all
    if success_count > 0:
        console.print(f"\n[bold yellow]Sync all {success_count} accounts now?[/bold yellow]")
        if console.input("[yellow](This may take a while) (y/n):[/yellow] ").lower().startswith('y'):
            console.print("\n[bold cyan]Syncing all accounts...[/bold cyan]")
            result = sync_manager.sync_all_accounts(sync_type='manual')
            
            if result.get('success'):
                console.print(f"\n[bold green]✓ Sync completed![/bold green]")
                console.print(f"  • New articles: {result.get('total_new', 0)}")
                console.print(f"  • Updated: {result.get('total_updated', 0)}")
            else:
                console.print(f"[red]✗ Sync failed: {result.get('error', 'Unknown error')}[/red]")
    
    console.print("\n[bold green]✨ Done! Check the web dashboard at http://localhost:5000[/bold green]")


if __name__ == "__main__":
    import_all_accounts()
