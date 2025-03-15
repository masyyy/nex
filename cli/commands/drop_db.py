"""
Command to drop and recreate the database tables.
"""
import sys
from typing import Dict, Any

from rich.console import Console
from rich.prompt import Confirm

from kgraphlib.database.database import init_db

# Initialize rich console
console = Console()

def drop_database() -> Dict[str, Any]:
    """
    Drop and recreate all database tables.

    Returns:
        Dictionary with operation results.
    """
    # Prompt for confirmation
    confirmed = Confirm.ask(
        "[bold red]WARNING:[/bold red] This will delete all data in the database. Are you sure?",
        default=False
    )

    if not confirmed:
        return {
            "message": "Database drop operation cancelled."
        }

    try:
        # Initialize the database with force_reset=True to drop and recreate tables
        with console.status("[bold yellow]Dropping and recreating database tables...[/bold yellow]"):
            init_db(force_reset=True)

        return {
            "message": "Database tables have been successfully dropped and recreated."
        }
    except Exception as e:
        return {
            "error": f"Failed to drop database: {str(e)}"
        }

if __name__ == "__main__":
    # This allows the script to be run directly for testing
    result = drop_database()

    if "error" in result:
        console.print(f"[bold red]Error:[/bold red] {result['error']}")
        sys.exit(1)
    else:
        console.print(f"[bold green]{result['message']}[/bold green]")