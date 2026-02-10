"""
Main CLI entry point for AI Employee Foundation
"""
import argparse
import sys
from pathlib import Path

# Add the src directory to the path so we can import modules
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cli.commands.vault_cmd import VaultCommand
from cli.commands.watch_cmd import WatchCommand


def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(
        prog="ai-employee",
        description="AI Employee Foundation - Local-first automation system"
    )

    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add vault command
    vault_cmd = VaultCommand(subparsers)

    # Add watch command
    watch_cmd = WatchCommand(subparsers)

    # Parse arguments
    args = parser.parse_args()

    # Execute the appropriate command
    if args.command == "vault":
        vault_cmd.execute(args)
    elif args.command == "watch":
        watch_cmd.execute(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()