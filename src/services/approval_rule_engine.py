"""
Approval Rule Engine - Gold Tier
Conditional approval rules based on action type, risk level, and estimated time
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import yaml
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.utils import get_current_iso_timestamp
from lib.event_bus import EventType, publish_event, get_event_bus


class RiskLevel(Enum):
    """Risk level for actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalDecision(Enum):
    """Approval decision types."""
    AUTO_APPROVE = "auto_approve"
    REQUIRE_APPROVAL = "require_approval"
    AUTO_REJECT = "auto_reject"
    ESCALATE = "escalate"


@dataclass
class ApprovalRule:
    """
    Defines a rule for approval determination.
    """
    rule_id: str
    name: str
    description: str = ""
    priority: int = 100  # Lower = higher priority
    
    # Conditions
    action_types: List[str] = field(default_factory=list)  # Empty = all types
    min_risk_level: RiskLevel = RiskLevel.LOW
    max_estimated_duration: int = -1  # -1 = no limit
    custom_condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    # Decision
    decision: ApprovalDecision = ApprovalDecision.REQUIRE_APPROVAL
    approvers: List[str] = field(default_factory=list)  # Required approvers
    escalation_target: str = ""  # Target for escalation
    
    # Metadata
    enabled: bool = True
    created_at: str = field(default_factory=lambda: get_current_iso_timestamp())
    
    def matches(self, context: Dict[str, Any]) -> bool:
        """
        Check if this rule matches the given context.
        
        Args:
            context: Approval context with action_type, risk_level, estimated_duration, etc.
            
        Returns:
            True if rule matches
        """
        if not self.enabled:
            return False
        
        # Check action type
        if self.action_types:
            action_type = context.get("action_type", "")
            if action_type not in self.action_types:
                return False
        
        # Check risk level
        context_risk = RiskLevel(context.get("risk_level", "low"))
        if context_risk.value < self.min_risk_level.value:
            return False
        
        # Check estimated duration
        if self.max_estimated_duration > 0:
            duration = context.get("estimated_duration", 0)
            if duration > self.max_estimated_duration:
                return False
        
        # Check custom condition
        if self.custom_condition:
            try:
                if not self.custom_condition(context):
                    return False
            except Exception as e:
                logging.getLogger("ApprovalRule").error(f"Custom condition error: {e}")
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "action_types": self.action_types,
            "min_risk_level": self.min_risk_level.value,
            "max_estimated_duration": self.max_estimated_duration,
            "decision": self.decision.value,
            "approvers": self.approvers,
            "escalation_target": self.escalation_target,
            "enabled": self.enabled
        }


@dataclass
class ApprovalContext:
    """
    Context for approval evaluation.
    """
    action_id: str
    plan_id: str
    approval_id: str
    action_type: str
    risk_level: RiskLevel
    estimated_duration: int
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_id": self.action_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "action_type": self.action_type,
            "risk_level": self.risk_level.value,
            "estimated_duration": self.estimated_duration,
            "description": self.description,
            "metadata": self.metadata
        }


@dataclass
class ApprovalResult:
    """
    Result of approval evaluation.
    """
    approval_id: str
    decision: ApprovalDecision
    matched_rule: Optional[ApprovalRule] = None
    reason: str = ""
    required_approvers: List[str] = field(default_factory=list)
    escalation_target: str = ""
    timestamp: str = field(default_factory=lambda: get_current_iso_timestamp())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "approval_id": self.approval_id,
            "decision": self.decision.value,
            "matched_rule": self.matched_rule.to_dict() if self.matched_rule else None,
            "reason": self.reason,
            "required_approvers": self.required_approvers,
            "escalation_target": self.escalation_target,
            "timestamp": self.timestamp
        }


class ApprovalRuleEngine:
    """
    Evaluates approval requests against configurable rules.
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.logger = logging.getLogger("ApprovalRuleEngine")
        self.event_bus = get_event_bus()
        
        # Rules (sorted by priority)
        self._rules: List[ApprovalRule] = []
        
        # Load default rules
        self._load_default_rules()
        
        # Load config
        self._load_config()
        
        self.logger.info(f"ApprovalRuleEngine initialized ({len(self._rules)} rules)")
    
    def _load_config(self):
        """Load configuration and custom rules."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            # Load custom rules from config
            approval_config = self.config.get('approval', {})
            custom_rules = approval_config.get('rules', [])
            
            for rule_config in custom_rules:
                rule = self._create_rule_from_config(rule_config)
                if rule:
                    self._rules.append(rule)
            
            # Sort by priority
            self._rules.sort(key=lambda r: r.priority)
            
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
    
    def _load_default_rules(self):
        """Load default approval rules."""
        # Rule 1: High duration actions require approval
        self._rules.append(ApprovalRule(
            rule_id="rule_high_duration",
            name="High Duration Actions",
            description="Actions with estimated duration > 120 minutes require approval",
            priority=10,
            max_estimated_duration=120,
            decision=ApprovalDecision.REQUIRE_APPROVAL
        ))
        
        # Rule 2: High risk actions require approval
        self._rules.append(ApprovalRule(
            rule_id="rule_high_risk",
            name="High Risk Actions",
            description="High and critical risk actions require approval",
            priority=5,
            min_risk_level=RiskLevel.HIGH,
            decision=ApprovalDecision.REQUIRE_APPROVAL
        ))
        
        # Rule 3: Data analysis requires approval
        self._rules.append(ApprovalRule(
            rule_id="rule_data_analysis",
            name="Data Analysis Actions",
            description="Data analysis actions require approval",
            priority=20,
            action_types=["data_analysis"],
            decision=ApprovalDecision.REQUIRE_APPROVAL
        ))
        
        # Rule 4: Report generation requires approval
        self._rules.append(ApprovalRule(
            rule_id="rule_report_generation",
            name="Report Generation",
            description="Report generation actions require approval",
            priority=20,
            action_types=["report_generation"],
            decision=ApprovalDecision.REQUIRE_APPROVAL
        ))
        
        # Rule 5: Email responses under 30 mins auto-approve
        self._rules.append(ApprovalRule(
            rule_id="rule_email_auto_approve",
            name="Quick Email Responses",
            description="Email responses under 30 minutes are auto-approved",
            priority=50,
            action_types=["email_response"],
            max_estimated_duration=30,
            decision=ApprovalDecision.AUTO_APPROVE
        ))
        
        # Rule 6: Critical risk requires escalation
        self._rules.append(ApprovalRule(
            rule_id="rule_critical_escalate",
            name="Critical Risk Escalation",
            description="Critical risk actions require escalation to admin",
            priority=1,
            min_risk_level=RiskLevel.CRITICAL,
            decision=ApprovalDecision.ESCALATE,
            escalation_target="admin"
        ))
        
        # Rule 7: Follow-up actions auto-approve
        self._rules.append(ApprovalRule(
            rule_id="rule_followup_auto",
            name="Follow-up Auto-Approve",
            description="Low risk follow-up actions are auto-approved",
            priority=60,
            action_types=["follow_up"],
            min_risk_level=RiskLevel.LOW,
            max_estimated_duration=30,
            decision=ApprovalDecision.AUTO_APPROVE
        ))
    
    def _create_rule_from_config(self, config: Dict[str, Any]) -> Optional[ApprovalRule]:
        """Create a rule from configuration."""
        try:
            return ApprovalRule(
                rule_id=config.get('rule_id', f"rule_{len(self._rules)}"),
                name=config.get('name', 'Unnamed Rule'),
                description=config.get('description', ''),
                priority=config.get('priority', 100),
                action_types=config.get('action_types', []),
                min_risk_level=RiskLevel(config.get('min_risk_level', 'low')),
                max_estimated_duration=config.get('max_estimated_duration', -1),
                decision=ApprovalDecision(config.get('decision', 'require_approval')),
                approvers=config.get('approvers', []),
                escalation_target=config.get('escalation_target', ''),
                enabled=config.get('enabled', True)
            )
        except Exception as e:
            self.logger.error(f"Failed to create rule from config: {e}")
            return None
    
    def evaluate(self, context: ApprovalContext) -> ApprovalResult:
        """
        Evaluate an approval request against all rules.
        
        Args:
            context: Approval context
            
        Returns:
            Approval result
        """
        self.logger.debug(f"Evaluating approval for {context.action_id}")
        
        # Convert context to dict for rule matching
        context_dict = context.to_dict()
        
        # Find first matching rule
        for rule in self._rules:
            if rule.matches(context_dict):
                result = ApprovalResult(
                    approval_id=context.approval_id,
                    decision=rule.decision,
                    matched_rule=rule,
                    reason=f"Matched rule: {rule.name}",
                    required_approvers=rule.approvers,
                    escalation_target=rule.escalation_target
                )
                
                self.logger.info(
                    f"Approval decision for {context.action_id}: "
                    f"{rule.decision.value} (rule: {rule.name})"
                )
                
                # Publish evaluation event
                publish_event(
                    EventType.APPROVAL_REQUIRED if rule.decision == ApprovalDecision.REQUIRE_APPROVAL else EventType.ACTION_APPROVED,
                    result.to_dict(),
                    source="approval_rule_engine"
                )
                
                return result
        
        # Default: require approval
        result = ApprovalResult(
            approval_id=context.approval_id,
            decision=ApprovalDecision.REQUIRE_APPROVAL,
            reason="No matching rules - default to approval required"
        )
        
        self.logger.info(f"Approval decision for {context.action_id}: require_approval (default)")
        
        return result
    
    def add_rule(self, rule: ApprovalRule):
        """Add a new rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)
        self.logger.info(f"Rule added: {rule.name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        for i, rule in enumerate(self._rules):
            if rule.rule_id == rule_id:
                removed = self._rules.pop(i)
                self.logger.info(f"Rule removed: {removed.name}")
                return True
        return False
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all rules as dictionaries."""
        return [rule.to_dict() for rule in self._rules]
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        for rule in self._rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                self.logger.info(f"Rule enabled: {rule.name}")
                return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        for rule in self._rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                self.logger.info(f"Rule disabled: {rule.name}")
                return True
        return False


class RiskAssessor:
    """
    Assesses risk level for actions.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("RiskAssessor")
    
    def assess(
        self,
        action_type: str,
        estimated_duration: int,
        metadata: Dict[str, Any] = None
    ) -> RiskLevel:
        """
        Assess risk level for an action.
        
        Args:
            action_type: Type of action
            estimated_duration: Estimated duration in minutes
            metadata: Additional metadata
            
        Returns:
            Risk level
        """
        metadata = metadata or {}
        risk_score = 0
        
        # Base risk by action type
        type_risk = {
            "email_response": 1,
            "follow_up": 1,
            "meeting_request": 2,
            "document_creation": 3,
            "data_analysis": 4,
            "report_generation": 4
        }
        risk_score += type_risk.get(action_type, 2)
        
        # Duration risk
        if estimated_duration > 180:
            risk_score += 3
        elif estimated_duration > 120:
            risk_score += 2
        elif estimated_duration > 60:
            risk_score += 1
        
        # Priority risk
        priority = metadata.get("priority", "medium")
        if priority == "high":
            risk_score += 2
        elif priority == "critical":
            risk_score += 3
        
        # Source risk
        source = metadata.get("source", "unknown")
        if source == "external":
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 8:
            return RiskLevel.CRITICAL
        elif risk_score >= 6:
            return RiskLevel.HIGH
        elif risk_score >= 4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


# Factory functions
def create_approval_rule_engine(config_path: str = "./config.yaml") -> ApprovalRuleEngine:
    """Factory function to create ApprovalRuleEngine."""
    return ApprovalRuleEngine(config_path)


def create_risk_assessor() -> RiskAssessor:
    """Factory function to create RiskAssessor."""
    return RiskAssessor()
