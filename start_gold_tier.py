#!/usr/bin/env python3
"""
Gold Tier Quickstart Script
Bootstrap and start the AI Employee Foundation Gold Tier system
"""
import os
import sys
from pathlib import Path

# Add the src directory to the path
src_dir = Path(__file__).parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


def check_prerequisites():
    """Check if all prerequisites are met."""
    print("Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 13):
        print(f"[ERROR] Python 3.13+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        return False
    print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check required packages
    required_packages = ['yaml', 'watchdog', 'asyncio']
    for package in required_packages:
        try:
            __import__(package)
            print(f"[OK] {package}")
        except ImportError:
            print(f"[ERROR] {package} not installed. Run: pip install -r requirements.txt")
            return False
    
    # Check optional packages
    try:
        import anthropic
        print("[OK] anthropic (Claude API)")
    except ImportError:
        print("[WARN] anthropic not installed. Claude API features will use templates.")
    
    # Check config file
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        print(f"[OK] Configuration file found")
    else:
        print("[WARN] Configuration file not found. Using defaults.")
    
    # Check environment variables
    claude_key = os.getenv('CLAUDE_API_KEY')
    if claude_key:
        print("[OK] CLAUDE_API_KEY configured")
    else:
        print("[WARN] CLAUDE_API_KEY not set. Claude API will use templates.")
    
    return True


def initialize_vault():
    """Initialize the vault if it doesn't exist."""
    from models.vault import Vault
    
    vault_path = Path(__file__).parent / "AI_Employee_Vault"
    vault = Vault(str(vault_path))
    
    if not vault.exists():
        print(f"Initializing vault at {vault_path}...")
        vault.initialize()
        print("[OK] Vault initialized")
    else:
        print("[OK] Vault already exists")
    
    return vault_path


def start_orchestrator(config_path: str = "./config.yaml", log_level: str = "INFO"):
    """Start the Gold Tier Orchestrator."""
    import asyncio
    from lib.utils import setup_logging
    from orchestrator import create_orchestrator
    
    # Setup logging
    setup_logging(log_level=log_level)
    
    print("\n" + "=" * 60)
    print("AI Employee Foundation - Gold Tier")
    print("=" * 60)
    print(f"Configuration: {config_path}")
    print(f"Log Level: {log_level}")
    print("=" * 60 + "\n")
    
    # Create orchestrator
    orchestrator = create_orchestrator(config_path)
    
    print("Services registered:")
    for name in orchestrator._services.keys():
        print(f"  - {name}")
    print()
    
    try:
        # Run the orchestrator
        print("Starting orchestrator... Press Ctrl+C to stop")
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        print("\n\nOrchestrator stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    print("=" * 60)
    print("AI Employee Foundation - Gold Tier Quickstart")
    print("=" * 60 + "\n")
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n[ERROR] Prerequisites check failed. Please fix the issues above.")
        sys.exit(1)
    
    print()
    
    # Initialize vault
    vault_path = initialize_vault()
    
    print()
    
    # Get configuration from environment or use defaults
    config_path = os.getenv("CONFIG_PATH", "./config.yaml")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Start orchestrator
    start_orchestrator(config_path, log_level)


if __name__ == "__main__":
    main()
