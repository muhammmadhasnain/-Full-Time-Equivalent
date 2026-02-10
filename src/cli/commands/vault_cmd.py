"""
Vault management commands for AI Employee Foundation CLI
"""
import argparse
from pathlib import Path
import sys

# Add the src directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.vault import Vault
from services.logging_service import LoggingService


class VaultCommand:
    """Handles vault-related CLI commands."""
    
    def __init__(self, subparsers):
        """Initialize the vault command parser."""
        self.parser = subparsers.add_parser("vault", help="Vault management commands")
        self.subparsers = self.parser.add_subparsers(dest="vault_action", help="Vault actions")
        
        # Add init command
        init_parser = self.subparsers.add_parser("init", help="Initialize the vault structure")
        init_parser.add_argument("--path", "-p", type=str, help="Path to the vault directory", 
                                 default="./AI_Employee_Vault")
        
        # Add check command
        check_parser = self.subparsers.add_parser("check", help="Check vault integrity")
        check_parser.add_argument("--path", "-p", type=str, help="Path to the vault directory", 
                                  default="./AI_Employee_Vault")
        
        # Add stats command
        stats_parser = self.subparsers.add_parser("stats", help="Show vault statistics")
        stats_parser.add_argument("--path", "-p", type=str, help="Path to the vault directory", 
                                  default="./AI_Employee_Vault")
        
        # Add pending-actions command
        pending_parser = self.subparsers.add_parser("pending-actions", help="Show pending actions")
        pending_parser.add_argument("--path", "-p", type=str, help="Path to the vault directory", 
                                    default="./AI_Employee_Vault")
    
    def execute(self, args):
        """Execute the vault command based on parsed arguments."""
        if args.vault_action == "init":
            self.init_vault(args.path)
        elif args.vault_action == "check":
            self.check_vault(args.path)
        elif args.vault_action == "stats":
            self.show_stats(args.path)
        elif args.vault_action == "pending-actions":
            self.show_pending_actions(args.path)
        else:
            self.parser.print_help()
    
    def init_vault(self, vault_path):
        """Initialize the vault structure."""
        # Convert to absolute path
        vault_path = str(Path(vault_path).resolve())
        print(f"Initializing vault at: {vault_path}")

        # Set up logging
        log_file = f"logs/vault_init_{vault_path.replace('/', '_').replace('\\', '_')}.log"
        logging_service = LoggingService(log_file=log_file)

        try:
            vault = Vault(vault_path)
            success = vault.initialize()

            if success:
                print(f"[SUCCESS] Vault successfully initialized at: {vault_path}")
                logging_service.log_system_event("VAULT_INITIALIZED", f"Vault created at {vault_path}", {
                    "vault_path": vault_path
                })
            else:
                print(f"[FAILED] Failed to initialize vault at: {vault_path}")
                logging_service.log_error("VAULT_INIT_FAILED", f"Failed to initialize vault at {vault_path}")

        except Exception as e:
            print(f"[ERROR] Error initializing vault: {str(e)}")
            logging_service.log_error("VAULT_INIT_ERROR", str(e), {
                "vault_path": vault_path
            })
    
    def check_vault(self, vault_path):
        """Check vault integrity."""
        # Convert to absolute path
        vault_path = str(Path(vault_path).resolve())
        print(f"Checking vault integrity at: {vault_path}")

        try:
            vault = Vault(vault_path)
            exists = vault.exists()

            if exists:
                print(f"[SUCCESS] Vault exists and is properly structured: {vault_path}")
            else:
                print(f"[FAILED] Vault is missing or improperly structured: {vault_path}")

        except Exception as e:
            print(f"[ERROR] Error checking vault: {str(e)}")
    
    def show_stats(self, vault_path):
        """Show vault statistics."""
        # Convert to absolute path
        vault_path = str(Path(vault_path).resolve())
        print(f"Getting vault statistics for: {vault_path}")

        try:
            vault = Vault(vault_path)
            if not vault.exists():
                print(f"[ERROR] Vault does not exist: {vault_path}")
                return

            stats = vault.get_stats()

            print("\n[Vault Statistics]:")
            print(f"  Total Actions: {stats.get('total_actions', 0)}")
            print(f"  Pending Approvals: {stats.get('pending_approvals', 0)}")
            print(f"  Inbox Count: {stats.get('inbox_count', 0)}")
            print(f"  Needs Action Count: {stats.get('needs_action_count', 0)}")
            print(f"  Plans Count: {stats.get('plans_count', 0)}")
            print(f"  Pending Approval Count: {stats.get('pending_approval_count', 0)}")
            print(f"  Approved Count: {stats.get('approved_count', 0)}")
            print(f"  Done Count: {stats.get('done_count', 0)}")

        except Exception as e:
            print(f"[ERROR] Error getting vault stats: {str(e)}")
    
    def show_pending_actions(self, vault_path):
        """Show pending actions in the vault."""
        # Convert to absolute path
        vault_path = str(Path(vault_path).resolve())
        print(f"Getting pending actions for: {vault_path}")

        try:
            vault = Vault(vault_path)
            if not vault.exists():
                print(f"[ERROR] Vault does not exist: {vault_path}")
                return

            # Get files in the Needs_Action folder
            needs_action_path = vault.get_folder_path("Needs_Action")
            if not needs_action_path:
                print("[ERROR] Needs_Action folder not found in vault")
                return

            action_files = [f for f in needs_action_path.iterdir() if f.suffix == ".yaml"]

            if action_files:
                print(f"\n[Pending Actions ({len(action_files)}):]")
                for file_path in action_files:
                    print(f"  - {file_path.name}")
            else:
                print("[SUCCESS] No pending actions found")

        except Exception as e:
            print(f"[ERROR] Error getting pending actions: {str(e)}")