"""
Demo script to test the WeChat Content Integration System
"""
from rich.console import Console
from config import settings
from database import db
from sync_manager import sync_manager
from wewe_client import wewe_client

console = Console()

def main():
    console.print("\n[bold cyan]WeChat Content Integration System - Demo[/bold cyan]\n")
    
    # Initialize database
    db.create_tables()
    console.print("[green]✓[/green] Database initialized")
    
    # Test connection
    console.print("\n[bold]Testing WeWe-RSS connection...[/bold]")
    if wewe_client.test_connection():
        console.print("[green]✓[/green] Connected to WeWe-RSS")
    else:
        console.print("[red]✗[/red] Failed to connect to WeWe-RSS")
        return
    
    # Try to fetch all feeds
    console.print("\n[bold]Fetching all feeds...[/bold]")
    all_feeds = wewe_client.fetch_all_feeds(format="json")
    
    if all_feeds:
        console.print(f"[green]✓[/green] Fetched feed data")
        console.print(f"  • Title: {all_feeds.get('title', 'N/A')}")
        console.print(f"  • Items: {len(all_feeds.get('items', []))}")
        
        # Show first few items
        items = all_feeds.get('items', [])
        if items:
            console.print("\n[bold]Recent articles:[/bold]")
            for i, item in enumerate(items[:5], 1):
                title = item.get('title', 'No title')
                console.print(f"  {i}. {title[:60]}...")
    else:
        console.print("[yellow]![/yellow] No feed data available")
    
    # Get database stats
    console.print("\n[bold]Database Statistics:[/bold]")
    stats = db.get_stats()
    console.print(f"  • Accounts: {stats['total_accounts']}")
    console.print(f"  • Articles: {stats['total_articles']}")
    
    console.print("\n[bold green]Demo completed![/bold green]")
    console.print("\n[dim]Next steps:[/dim]")
    console.print("  1. Check WeWe-RSS UI to get the correct feed ID")
    console.print("  2. Run: python cli.py add --feed-id \"<your-feed-id>\"")
    console.print("  3. Run: python cli.py sync --all")
    console.print("  4. Run: python cli.py articles")

if __name__ == "__main__":
    main()
