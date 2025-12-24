"""
Quick Import - Import all articles from WeWe-RSS aggregated feed
Since WeWe-RSS aggregates all feeds into /feeds/all, we'll create one "All Feeds" account
"""
from rich.console import Console
from config import settings
from database import db
from sync_manager import sync_manager
from wewe_client import wewe_client
from logger import setup_logger

logger = setup_logger(__name__)
console = Console()


def quick_import():
    """
    Quick import all articles from WeWe-RSS aggregated feed
    """
    console.print("\n[bold cyan]🚀 Quick Import from WeWe-RSS[/bold cyan]\n")
    
    # Initialize
    db.create_tables()
    
    # Test connection
    if not wewe_client.test_connection():
        console.print("[red]✗ Cannot connect to WeWe-RSS[/red]")
        return
    
    console.print("[green]✓ Connected to WeWe-RSS[/green]\n")
    
    # Fetch all feeds to see what we have
    all_feeds = wewe_client.fetch_all_feeds(format="json")
    
    if not all_feeds or 'items' not in all_feeds:
        console.print("[red]✗ No feeds found[/red]")
        return
    
    items = all_feeds.get('items', [])
    console.print(f"[cyan]Found {len(items)} articles in WeWe-RSS aggregated feed[/cyan]\n")
    
    # Show sample articles
    console.print("[bold]Sample articles:[/bold]")
    for i, item in enumerate(items[:5], 1):
        title = item.get('title', 'No title')[:60]
        author = item.get('author', 'Unknown')
        if isinstance(author, dict):
            author = author.get('name', 'Unknown')
        console.print(f"  {i}. {title}... (by {author})")
    
    console.print(f"\n[dim]...and {len(items) - 5} more[/dim]\n")
    
    # Strategy: Import all articles directly without creating separate accounts
    # We'll create one "WeWe-RSS All" account and import everything there
    
    console.print("[bold yellow]Strategy:[/bold yellow]")
    console.print("  • Create one account: 'WeWe-RSS All'")
    console.print(f"  • Import all {len(items)} articles")
    console.print("  • You can browse by author in the Articles page\n")
    
    if not console.input("[yellow]Proceed? (y/n):[/yellow] ").lower().startswith('y'):
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    # Create or get the "All" account
    console.print("\n[cyan]Creating account...[/cyan]")
    
    account = db.get_account_by_feed_id("all")
    if not account:
        account = db.create_account(
            feed_id="all",
            name="WeWe-RSS All Feeds",
            feed_url=settings.get_all_feeds_url(),
            description="Aggregated feed from all WeChat accounts in WeWe-RSS"
        )
        console.print(f"[green]✓ Created account: {account.name}[/green]")
    else:
        console.print(f"[yellow]⊘ Account already exists: {account.name}[/yellow]")
    
    # Sync the account
    console.print(f"\n[cyan]Syncing {len(items)} articles...[/cyan]")
    console.print("[dim]This may take a minute...[/dim]\n")
    
    result = sync_manager.sync_account(
        feed_id="all",
        sync_type="manual",
        full_sync=False
    )
    
    if result.get('success'):
        stats = result.get('stats', {})
        console.print(f"\n[bold green]✓ Import completed![/bold green]")
        console.print(f"  • Fetched: {stats.get('fetched', 0)}")
        console.print(f"  • New: {stats.get('new', 0)}")
        console.print(f"  • Updated: {stats.get('updated', 0)}")
        console.print(f"  • Skipped: {stats.get('skipped', 0)}")
        console.print(f"  • Failed: {stats.get('failed', 0)}")
    else:
        console.print(f"[red]✗ Import failed: {result.get('error', 'Unknown error')}[/red]")
        return
    
    # Show stats
    db_stats = db.get_stats()
    console.print(f"\n[bold cyan]Database Statistics:[/bold cyan]")
    console.print(f"  • Total Accounts: {db_stats['total_accounts']}")
    console.print(f"  • Total Articles: {db_stats['total_articles']}")
    
    console.print(f"\n[bold green]✨ Done! Open the dashboard:[/bold green]")
    console.print(f"[cyan]http://localhost:5000[/cyan]\n")


if __name__ == "__main__":
    quick_import()
