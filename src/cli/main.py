"""
Main CLI entry point for AI Employee Foundation - Gold Tier
"""
import argparse
import sys
import asyncio
from pathlib import Path

# Add the src directory to the path so we can import modules
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cli.commands.vault_cmd import VaultCommand
from cli.commands.watch_cmd import WatchCommand
from cli.commands.orchestrator_cmd import OrchestratorCommand
from cli.commands.approval_cmd import ApprovalCLI


def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(
        prog="ai-employee",
        description="AI Employee Foundation - Gold Tier Automation System"
    )

    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add vault command
    vault_cmd = VaultCommand(subparsers)

    # Add watch command
    watch_cmd = WatchCommand(subparsers)

    # Add orchestrator command
    orchestrator_cmd = OrchestratorCommand(subparsers)

    # Add approval commands
    approval_subparsers = subparsers.add_parser("approval", help="Approval management commands").add_subparsers()
    approval_cli = ApprovalCLI()
    approval_cli.register_commands(approval_subparsers)

    # Parse arguments
    args = parser.parse_args()

    # Execute the appropriate command
    if args.command == "vault":
        vault_cmd.execute(args)
    elif args.command == "watch":
        watch_cmd.execute(args)
    elif args.command == "start":
        orchestrator_cmd.execute(args)
    elif args.command == "stop":
        orchestrator_cmd.execute(args)
    elif args.command == "status":
        orchestrator_cmd.execute(args)
    elif args.command == "restart":
        orchestrator_cmd.execute(args)
    elif args.command == "approval":
        if hasattr(args, 'func'):
            args.func(args)
        else:
            approval_subparsers.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
