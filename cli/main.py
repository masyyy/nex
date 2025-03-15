"""
Main entry point for the application.
"""
import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from cli.agent import Agent
from kgraphlib.database.database import init_db
from common.config import config


console = Console()


def process_prompt(prompt: str) -> None:
    """
    Process a free-form prompt using the agent.

    Args:
        prompt: The user prompt.
    """
    console.print(Panel(f"[bold blue]Query:[/bold blue] {prompt}", expand=False))

    with console.status("[bold green]Thinking...[/bold green]"):
        agent = Agent()
        response = agent.process(prompt)

    console.print(Panel(Markdown(response), title="[bold green]Response[/bold green]", expand=False))


def process_command(command: str, args: list) -> None:
    """
    Process a specific command with arguments.

    Args:
        command: The command to execute.
        args: List of command arguments.
    """
    if command == "ingest":
        if len(args) != 1:
            console.print("[bold red]Usage:[/bold red] nex ingest <path_to_pdf_file>")
            sys.exit(1)

        pdf_path = args[0]

        with console.status(f"[bold green]Ingesting {os.path.basename(pdf_path)}...[/bold green]"):
            from cli.commands.ingest import ingest_pdf

            result = ingest_pdf(pdf_path)

            if "error" in result:
                console.print(f"[bold red]Error:[/bold red] {result['error']}")
                sys.exit(1)
            else:
                console.print(f"[bold green]Successfully ingested:[/bold green] {os.path.basename(pdf_path)}")

    elif command == "drop-db":
        # Check for --confirm flag
        confirm = "--confirm" in args

        from cli.commands.drop_db import drop_database
        result = drop_database()

        if "error" in result:
            console.print(f"[bold red]Error:[/bold red] {result['error']}")
            sys.exit(1)
        else:
            console.print(f"[bold green]{result['message']}[/bold green]")

    else:
        console.print(f"[bold red]Unknown command:[/bold red] {command}")
        console.print("Available commands: ingest, drop-db")
        sys.exit(1)


def initialize_database() -> None:
    """Initialize the database connection."""
    try:
        # Initialize the database without dropping tables
        init_db(force_reset=False)
    except Exception as e:
        console.print(f"[bold red]Database initialization error:[/bold red] {str(e)}")
        sys.exit(1)

def print_welcome() -> None:
    """Print welcome message."""
    console.print(Panel.fit(
        "[bold blue]Nexus[/bold blue]: Knowledge Graph Agent\n\n"
        "Use [bold]nex \"<prompt>\"[/bold] for free-form queries\n"
        "Use [bold]nex ingest <path_to_pdf_file>[/bold] to ingest documents\n"
        "Use [bold]nex drop-db --confirm[/bold] to reset the database",
        title="Welcome"
    ))


def main() -> None:
    """Main entry point for the application."""
    # Load environment variables
    load_dotenv()

    # Initialize components
    initialize_database()

    # Check if any arguments were provided
    if len(sys.argv) < 2:
        print_welcome()
        console.print("[bold yellow]Usage:[/bold yellow] nex \"<prompt>\" or nex <command> [parameters]")
        sys.exit(1)

    # Process the input
    if len(sys.argv) == 2 and not sys.argv[1] in ["ingest", "drop-db"]:
        # Free prompt mode
        prompt = sys.argv[1]
        process_prompt(prompt)
    else:
        # Command mode
        command = sys.argv[1]
        args = sys.argv[2:]
        process_command(command, args)


if __name__ == "__main__":
    main()