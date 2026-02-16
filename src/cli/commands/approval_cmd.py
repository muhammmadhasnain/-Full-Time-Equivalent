"""
CLI Approval Commands - Gold Tier
CLI interface for human-in-the-loop approval workflow
"""
import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add the src directory to the path
src_dir = Path(__file__).parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from lib.utils import get_current_iso_timestamp
from lib.event_bus import EventType, publish_event, get_event_bus


class ApprovalCLI:
    """
    CLI interface for approval management.
    """
    
    def __init__(self):
        self.vault_path = Path("./AI_Employee_Vault")
        self.pending_approval_path = self.vault_path / "Pending_Approval"
        self.approved_path = self.vault_path / "Approved"
        self.rejected_path = self.vault_path / "Rejected"
        self.system_log_path = self.vault_path / "System_Log"
        self.event_bus = get_event_bus()
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        for path in [self.pending_approval_path, self.approved_path, self.rejected_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def register_commands(self, subparsers):
        """Register approval commands with argparse."""
        # List pending approvals
        list_parser = subparsers.add_parser("list", help="List pending approvals")
        list_parser.add_argument("--json", action="store_true", help="Output as JSON")
        list_parser.set_defaults(func=self.list_pending)
        
        # Approve an action
        approve_parser = subparsers.add_parser("approve", help="Approve a pending action")
        approve_parser.add_argument("id", help="Approval ID or Plan ID")
        approve_parser.add_argument("--reason", "-r", type=str, default="", help="Approval reason")
        approve_parser.add_argument("--approver", "-a", type=str, default="cli_user", help="Approver name")
        approve_parser.set_defaults(func=self.approve)
        
        # Reject an action
        reject_parser = subparsers.add_parser("reject", help="Reject a pending action")
        reject_parser.add_argument("id", help="Approval ID or Plan ID")
        reject_parser.add_argument("--reason", "-r", type=str, required=True, help="Rejection reason")
        reject_parser.add_argument("--approver", "-a", type=str, default="cli_user", help="Rejector name")
        reject_parser.set_defaults(func=self.reject)
        
        # Show approval details
        show_parser = subparsers.add_parser("show", help="Show approval details")
        show_parser.add_argument("id", help="Approval ID or Plan ID")
        show_parser.set_defaults(func=self.show)
        
        # Auto-approve all (for testing)
        auto_approve_parser = subparsers.add_parser("auto-approve-all", help="Auto-approve all pending (testing)")
        auto_approve_parser.add_argument("--approver", "-a", type=str, default="cli_auto", help="Approver name")
        auto_approve_parser.set_defaults(func=self.auto_approve_all)
        
        # Show approval history
        history_parser = subparsers.add_parser("history", help="Show approval history")
        history_parser.add_argument("--limit", "-l", type=int, default=20, help="Number of entries")
        history_parser.add_argument("--json", action="store_true", help="Output as JSON")
        history_parser.set_defaults(func=self.history)
    
    def list_pending(self, args):
        """List pending approvals."""
        pending = self._get_pending_approvals()
        
        if args.json:
            print(json.dumps(pending, indent=2))
        else:
            if not pending:
                print("No pending approvals")
                return
            
            print("\n" + "=" * 70)
            print("PENDING APPROVALS")
            print("=" * 70)
            
            for item in pending:
                print(f"\n📋 {item['approval_id'][:8]}...")
                print(f"   Action ID: {item['action_id'][:8]}...")
                print(f"   Plan ID:   {item['plan_id'][:8]}...")
                print(f"   Type:      {item.get('action_type', 'unknown')}")
                print(f"   Duration:  {item.get('estimated_duration', 'N/A')} minutes")
                print(f"   Risk:      {item.get('risk_level', 'unknown')}")
                print(f"   Created:   {item.get('created_at', 'N/A')}")
                print(f"   Reason:    {item.get('approval_reason', 'Standard approval required')}")
            
            print("\n" + "=" * 70)
            print(f"Total: {len(pending)} pending approval(s)")
            print("\nUse 'ai-employee approve <ID>' to approve")
            print("Use 'ai-employee reject <ID> --reason <reason>' to reject")
    
    def approve(self, args):
        """Approve a pending action."""
        approval_id = args.id
        approver = args.approver
        reason = args.reason or "Approved via CLI"
        
        # Find the approval file
        approval_file = self._find_approval_file(approval_id)
        
        if not approval_file:
            print(f"❌ Approval not found: {approval_id}")
            return False
        
        try:
            # Read the approval file
            content = approval_file.read_text(encoding='utf-8')
            
            # Extract plan ID for event
            import re
            plan_match = re.search(r'Plan ID[:\s]+([a-f0-9-]+)', content, re.IGNORECASE)
            plan_id = plan_match.group(1) if plan_match else ""
            
            action_match = re.search(r'Action ID[:\s]+([a-f0-9-]+)', content, re.IGNORECASE)
            action_id = action_match.group(1) if action_match else ""
            
            # Move to Approved folder
            dest_path = self.approved_path / approval_file.name
            approval_file.rename(dest_path)
            
            # Log approval
            self._log_approval(approval_file.name, action_id, plan_id, approver, reason, "approved")
            
            # Publish approval event
            publish_event(
                EventType.ACTION_APPROVED,
                {
                    "approval_id": approval_id,
                    "action_id": action_id,
                    "plan_id": plan_id,
                    "approver": approver,
                    "reason": reason,
                    "path": str(dest_path)
                },
                source="cli_approval"
            )
            
            print(f"✅ Approved: {approval_file.name}")
            print(f"   Approver: {approver}")
            print(f"   Reason:   {reason}")
            print(f"   Status:   Moved to Approved/")
            
            return True
            
        except Exception as e:
            print(f"❌ Error approving: {e}")
            return False
    
    def reject(self, args):
        """Reject a pending action."""
        approval_id = args.id
        approver = args.approver
        reason = args.reason
        
        # Find the approval file
        approval_file = self._find_approval_file(approval_id)
        
        if not approval_file:
            print(f"❌ Approval not found: {approval_id}")
            return False
        
        try:
            # Read the approval file
            content = approval_file.read_text(encoding='utf-8')
            
            # Extract IDs
            import re
            plan_match = re.search(r'Plan ID[:\s]+([a-f0-9-]+)', content, re.IGNORECASE)
            plan_id = plan_match.group(1) if plan_match else ""
            
            action_match = re.search(r'Action ID[:\s]+([a-f0-9-]+)', content, re.IGNORECASE)
            action_id = action_match.group(1) if action_match else ""
            
            # Move to Rejected folder
            dest_path = self.rejected_path / approval_file.name
            approval_file.rename(dest_path)
            
            # Log rejection
            self._log_approval(approval_file.name, action_id, plan_id, approver, reason, "rejected")
            
            # Publish rejection event
            publish_event(
                EventType.ACTION_REJECTED,
                {
                    "approval_id": approval_id,
                    "action_id": action_id,
                    "plan_id": plan_id,
                    "approver": approver,
                    "reason": reason,
                    "path": str(dest_path)
                },
                source="cli_approval"
            )
            
            print(f"❌ Rejected: {approval_file.name}")
            print(f"   Approver: {approver}")
            print(f"   Reason:   {reason}")
            print(f"   Status:   Moved to Rejected/")
            
            return True
            
        except Exception as e:
            print(f"❌ Error rejecting: {e}")
            return False
    
    def show(self, args):
        """Show approval details."""
        approval_id = args.id
        
        # Find the approval file
        approval_file = self._find_approval_file(approval_id)
        
        if not approval_file:
            print(f"❌ Approval not found: {approval_id}")
            return
        
        # Read and display content
        content = approval_file.read_text(encoding='utf-8')
        
        print("\n" + "=" * 70)
        print(f"APPROVAL DETAILS: {approval_file.name}")
        print("=" * 70)
        print(content)
        print("=" * 70)
    
    def auto_approve_all(self, args):
        """Auto-approve all pending approvals (for testing)."""
        pending = self._get_pending_approvals()
        
        if not pending:
            print("No pending approvals to auto-approve")
            return
        
        approver = args.approver
        approved_count = 0
        
        print(f"Auto-approving {len(pending)} pending approval(s)...")
        
        for item in pending:
            # Create a mock args object
            class MockArgs:
                pass
            
            mock_args = MockArgs()
            mock_args.id = item['approval_id']
            mock_args.approver = approver
            mock_args.reason = "Auto-approved via CLI (testing)"
            
            if self.approve(mock_args):
                approved_count += 1
        
        print(f"\n✅ Auto-approved {approved_count}/{len(pending)} approval(s)")
    
    def history(self, args):
        """Show approval history."""
        limit = args.limit
        
        # Read approval history from audit log
        audit_path = self.system_log_path / "Audit" / "approval_history.jsonl"
        
        if not audit_path.exists():
            print("No approval history found")
            return
        
        history = []
        try:
            with open(audit_path, 'r', encoding='utf-8') as f:
                for line in reversed(f.readlines()):
                    if len(history) >= limit:
                        break
                    try:
                        entry = json.loads(line.strip())
                        history.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading history: {e}")
            return
        
        if args.json:
            print(json.dumps(history, indent=2))
        else:
            print("\n" + "=" * 70)
            print("APPROVAL HISTORY")
            print("=" * 70)
            
            for entry in history:
                event_type = entry.get('event_type', 'unknown')
                icon = "✅" if "granted" in event_type or "approved" in event_type else "❌" if "rejected" in event_type else "⏳"
                
                print(f"\n{icon} {entry.get('timestamp', 'N/A')[:19]}")
                print(f"   Type: {entry.get('event_type', 'unknown')}")
                print(f"   Action: {entry.get('action_id', 'N/A')[:8]}...")
                print(f"   Plan:   {entry.get('plan_id', 'N/A')[:8]}...")
                if entry.get('approver'):
                    print(f"   Approver: {entry.get('approver')}")
                if entry.get('reason'):
                    print(f"   Reason: {entry.get('reason')[:50]}")
            
            print("\n" + "=" * 70)
    
    def _get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get list of pending approvals."""
        pending = []
        
        if not self.pending_approval_path.exists():
            return pending
        
        for file in self.pending_approval_path.glob("*.md"):
            try:
                content = file.read_text(encoding='utf-8')
                
                # Parse content
                import re
                
                action_match = re.search(r'Action ID[:\s]+([a-f0-9-]+)', content, re.IGNORECASE)
                plan_match = re.search(r'Plan ID[:\s]+([a-f0-9-]+)', content, re.IGNORECASE)
                desc_match = re.search(r'Description[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
                created_match = re.search(r'Created[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
                
                pending.append({
                    "approval_id": file.stem,
                    "filename": file.name,
                    "action_id": action_match.group(1) if action_match else "",
                    "plan_id": plan_match.group(1) if plan_match else "",
                    "description": desc_match.group(1).strip() if desc_match else "",
                    "created_at": created_match.group(1).strip() if created_match else "",
                    "path": str(file)
                })
            except Exception as e:
                continue
        
        return pending
    
    def _find_approval_file(self, approval_id: str) -> Optional[Path]:
        """Find approval file by ID."""
        # Try direct filename match
        direct_path = self.pending_approval_path / f"{approval_id}.md"
        if direct_path.exists():
            return direct_path
        
        # Search for partial match in filename
        for file in self.pending_approval_path.glob("*.md"):
            if approval_id in file.stem or file.stem.startswith(approval_id[:8]):
                return file
        
        return None
    
    def _log_approval(
        self,
        filename: str,
        action_id: str,
        plan_id: str,
        approver: str,
        reason: str,
        decision: str
    ):
        """Log approval/rejection to audit log."""
        audit_dir = self.system_log_path / "Audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "timestamp": get_current_iso_timestamp(),
            "filename": filename,
            "action_id": action_id,
            "plan_id": plan_id,
            "approver": approver,
            "reason": reason,
            "decision": decision
        }
        
        # Append to approval log
        log_path = audit_dir / "approval_log.jsonl"
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + "\n")


def create_approval_cli() -> ApprovalCLI:
    """Factory function to create ApprovalCLI."""
    return ApprovalCLI()
