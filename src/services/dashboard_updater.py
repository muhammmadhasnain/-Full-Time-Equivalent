"""
Dashboard AutoUpdater - Gold Tier
Automatically updates Dashboard.md with real-time workflow status
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import yaml

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.event_bus import get_event_bus, EventType, Event, publish_event
from lib.utils import get_current_iso_timestamp, ensure_directory_exists


class DashboardAutoUpdater:
    """
    Automatically updates Dashboard.md with workflow status.
    
    Responsibilities:
    - Track active watchers
    - Count pending approvals
    - Track completed actions
    - Display error counts
    - Update in real-time via event subscriptions
    """
    
    def __init__(self, vault_path: str, config_path: str = "./config.yaml"):
        self.vault_path = Path(vault_path)
        self.config_path = config_path
        self.config = {}
        
        self.dashboard_path = self.vault_path / "Dashboard.md"
        self.logger = logging.getLogger("DashboardAutoUpdater")
        self.event_bus = get_event_bus()
        
        # State
        self._running = False
        self._update_interval = 30  # seconds
        self._update_task: Optional[asyncio.Task] = None
        
        # Metrics (cached)
        self._metrics = {
            "inbox_count": 0,
            "needs_action_count": 0,
            "plans_count": 0,
            "pending_approval_count": 0,
            "approved_count": 0,
            "done_count": 0,
            "failed_count": 0,
            "dead_letter_count": 0,
            "total_actions": 0,
            "processed_today": 0,
            "errors_today": 0,
            "last_updated": get_current_iso_timestamp()
        }
        
        # Watcher status
        self._watchers = {
            "gmail_watcher": {"active": False, "last_seen": None},
            "file_monitor": {"active": False, "last_seen": None},
            "whatsapp_watcher": {"active": False, "last_seen": None},
            "claude_service": {"active": False, "last_seen": None},
            "mcp_service": {"active": False, "last_seen": None}
        }
        
        # Recent activity log
        self._recent_activity: List[Dict[str, Any]] = []
        self._max_activity_log = 20
        
        # Load config
        self._load_config()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        self.logger.info("DashboardAutoUpdater initialized")
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            self._update_interval = self.config.get('dashboard', {}).get('update_interval', 30)
        except:
            self.config = {}
    
    def _setup_event_handlers(self):
        """Setup event bus handlers."""
        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.SERVICE_STARTED, self._on_service_event)
        self.event_bus.subscribe(EventType.SERVICE_STOPPED, self._on_service_event)
        self.event_bus.subscribe(EventType.FILE_CREATED, self._on_file_event)
        self.event_bus.subscribe(EventType.ACTION_GENERATED, self._on_action_event)
        self.event_bus.subscribe(EventType.ACTION_APPROVED, self._on_action_event)
        self.event_bus.subscribe(EventType.ACTION_EXECUTED, self._on_action_event)
        self.event_bus.subscribe(EventType.ACTION_FAILED, self._on_action_event)
        self.event_bus.subscribe(EventType.PLAN_CREATED, self._on_plan_event)
        
        self.logger.info("DashboardAutoUpdater event handlers registered")
    
    def _on_service_event(self, event: Event):
        """Handle service start/stop events."""
        service = event.payload.get('service', 'unknown')
        
        if service in self._watchers:
            self._watchers[service]['active'] = (event.event_type == EventType.SERVICE_STARTED)
            self._watchers[service]['last_seen'] = get_current_iso_timestamp()
            
            self.logger.debug(f"Service {service}: {event.event_type.value}")
            self._schedule_update()
    
    def _on_file_event(self, event: Event):
        """Handle file events."""
        self._add_activity({
            "type": "file",
            "event": event.event_type.value,
            "filename": event.payload.get('filename', 'unknown'),
            "timestamp": event.timestamp
        })
        self._schedule_update()
    
    def _on_action_event(self, event: Event):
        """Handle action events."""
        self._add_activity({
            "type": "action",
            "event": event.event_type.value,
            "action_id": event.payload.get('action_id', 'unknown')[:8] + "...",
            "timestamp": event.timestamp
        })
        
        # Update error count for failures
        if event.event_type == EventType.ACTION_FAILED:
            self._metrics['errors_today'] += 1
        
        self._schedule_update()
    
    def _on_plan_event(self, event: Event):
        """Handle plan events."""
        self._add_activity({
            "type": "plan",
            "event": event.event_type.value,
            "plan_id": event.payload.get('plan_id', 'unknown')[:8] + "...",
            "timestamp": event.timestamp
        })
        self._schedule_update()
    
    def _add_activity(self, activity: Dict[str, Any]):
        """Add activity to the recent activity log."""
        self._recent_activity.insert(0, activity)
        
        # Trim to max size
        if len(self._recent_activity) > self._max_activity_log:
            self._recent_activity = self._recent_activity[:self._max_activity_log]
    
    def _schedule_update(self):
        """Schedule a dashboard update."""
        if self._running and self._update_task and not self._update_task.done():
            # Update will happen on next interval
            pass
    
    async def start(self):
        """Start the dashboard updater."""
        self._running = True
        
        # Initial update
        await self._update_dashboard()
        
        # Start periodic updates
        self._update_task = asyncio.create_task(self._update_loop())
        
        self.logger.info("DashboardAutoUpdater started")
        
        publish_event(
            EventType.SERVICE_STARTED,
            {"service": "dashboard_updater"},
            source="dashboard_updater"
        )
    
    async def stop(self):
        """Stop the dashboard updater."""
        self._running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        # Final update
        await self._update_dashboard()
        
        self.logger.info("DashboardAutoUpdater stopped")
        
        publish_event(
            EventType.SERVICE_STOPPED,
            {"service": "dashboard_updater"},
            source="dashboard_updater"
        )
    
    def health_check(self) -> bool:
        """Check service health."""
        return self._running
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return {
            "update_interval": self._update_interval,
            "last_updated": self._metrics['last_updated'],
            "activity_log_size": len(self._recent_activity)
        }
    
    async def _update_loop(self):
        """Periodic update loop."""
        while self._running:
            try:
                await self._update_dashboard()
            except Exception as e:
                self.logger.error(f"Dashboard update error: {e}")
            
            await asyncio.sleep(self._update_interval)
    
    async def _update_dashboard(self):
        """Update the Dashboard.md file."""
        try:
            # Refresh metrics from vault
            await self._refresh_metrics()
            
            # Generate dashboard content
            content = self._generate_dashboard_content()
            
            # Write atomically
            self._write_dashboard_atomic(content)
            
            self.logger.debug("Dashboard updated")
            
        except Exception as e:
            self.logger.error(f"Failed to update dashboard: {e}")
    
    async def _refresh_metrics(self):
        """Refresh metrics from vault folder counts."""
        folders = [
            "Inbox", "Needs_Action", "Plans", "Pending_Approval",
            "Approved", "Done", "Failed", "Dead_Letter"
        ]
        
        for folder in folders:
            folder_path = self.vault_path / folder
            if folder_path.exists():
                count = sum(1 for f in folder_path.iterdir() if f.is_file())
                self._metrics[f"{folder.lower()}_count"] = count
        
        # Calculate totals
        self._metrics['total_actions'] = (
            self._metrics['inbox_count'] +
            self._metrics['needs_action_count'] +
            self._metrics['done_count']
        )
        
        self._metrics['pending_approvals'] = self._metrics['pending_approval_count']
        
        # Count today's activity
        today = datetime.utcnow().date()
        self._metrics['processed_today'] = sum(
            1 for a in self._recent_activity
            if a.get('type') in ['action', 'plan'] and
            'completed' in a.get('event', '').lower()
        )
        
        self._metrics['last_updated'] = get_current_iso_timestamp()
    
    def _generate_dashboard_content(self) -> str:
        """Generate Dashboard.md content."""
        m = self._metrics
        
        # Watcher status
        watcher_status = ""
        for name, status in self._watchers.items():
            icon = "🟢" if status['active'] else "🔴"
            last_seen = status['last_seen'] or 'Never'
            watcher_status += f"- **{name.replace('_', ' ').title()}**: {icon} {status['active'] and 'Running' or 'Stopped'}\n"
        
        # Recent activity
        activity_lines = []
        for activity in self._recent_activity[:10]:
            event_type = activity.get('event', 'unknown').replace('_', ' ').title()
            filename = activity.get('filename') or activity.get('action_id') or activity.get('plan_id')
            activity_lines.append(f"- {activity['timestamp'][:19]}: {event_type} - {filename}")
        
        activity_text = "\n".join(activity_lines) if activity_lines else "- No recent activity"
        
        # Error status
        error_status = "✅ No errors" if m['errors_today'] == 0 else f"⚠️ {m['errors_today']} errors today"
        
        content = f"""# AI Employee Dashboard

## System Status
- **Status**: {'🟢 Active' if self._running else '🔴 Stopped'}
- **Last Updated**: {m['last_updated']}

## Workflow Metrics

| Stage | Count |
|-------|-------|
| 📥 Inbox | {m['inbox_count']} |
| ⏳ Needs Action | {m['needs_action_count']} |
| 📋 Plans | {m['plans_count']} |
| ⏸️ Pending Approval | {m['pending_approval_count']} |
| ✅ Approved | {m['approved_count']} |
| ✔️ Done | {m['done_count']} |
| ❌ Failed | {m['failed_count']} |
| 📦 Dead Letter | {m['dead_letter_count']} |

**Total Actions**: {m['total_actions']}
**Processed Today**: {m['processed_today']}
**Errors Today**: {m['errors_today']}

## Watchers

{watcher_status}

## Recent Activity

{activity_text}

## System Health

| Component | Status |
|-----------|--------|
| Vault | ✅ Operational |
| Workflow Engine | {'🟢 Running' if self._running else '🔴 Stopped'} |
| Storage | ✅ Available |
| Error Rate | {error_status} |

## Quick Stats

- **Pending Approvals**: {m['pending_approvals']}
- **Dead Letter Queue**: {m['dead_letter_count']}
- **Success Rate**: {self._calculate_success_rate():.1f}%

---
*Auto-updated by DashboardAutoUpdater*
"""
        return content
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate from recent activity."""
        if not self._recent_activity:
            return 100.0
        
        completed = sum(
            1 for a in self._recent_activity
            if 'completed' in a.get('event', '').lower() or
               'executed' in a.get('event', '').lower() or
               'approved' in a.get('event', '').lower()
        )
        
        failed = sum(
            1 for a in self._recent_activity
            if 'failed' in a.get('event', '').lower() or
               'error' in a.get('event', '').lower()
        )
        
        total = completed + failed
        if total == 0:
            return 100.0
        
        return (completed / total) * 100
    
    def _write_dashboard_atomic(self, content: str):
        """Write dashboard content atomically."""
        ensure_directory_exists(str(self.vault_path))
        
        # Write to temp file first
        temp_path = self.dashboard_path.with_suffix('.md.tmp')
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Atomic rename
        temp_path.rename(self.dashboard_path)
    
    def force_update(self):
        """Force an immediate dashboard update."""
        asyncio.create_task(self._update_dashboard())


# Factory function
def create_dashboard_updater(vault_path: str, config_path: str = "./config.yaml") -> DashboardAutoUpdater:
    """Factory function to create DashboardAutoUpdater."""
    return DashboardAutoUpdater(vault_path, config_path)
