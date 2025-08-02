"""Main entry point for SpotSync."""

import sys
import typer
from .cli import app as cli_app
from .tui import main as tui_main


def main():
    """Main entry point that routes to CLI or TUI."""
    if len(sys.argv) == 1:
        # No arguments provided, launch TUI
        tui_main()
    else:
        # Arguments provided, use CLI
        cli_app()


if __name__ == "__main__":
    main()