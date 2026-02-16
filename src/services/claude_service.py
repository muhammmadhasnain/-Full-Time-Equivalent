"""
Claude Service - Gold Tier
Real Claude API integration for plan generation and action processing
"""
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import yaml

# Add the src directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.action_file import ActionFile
from models.plan_file import PlanFile
from lib.event_bus import EventType, publish_event, get_event_bus
from lib.utils import get_current_iso_timestamp, ensure_directory_exists
from lib.constants import ENV_CLAUDE_API_KEY
from lib.exceptions import ClaudeServiceError


class ClaudeService:
    """
    Gold Tier Claude Service with real API integration.
    
    Responsibilities:
    - Process action files and generate plans using Claude API
    - Event-driven plan generation triggered by action.generated events
    - Automatic plan file creation in Plans/ folder
    - Approval requirement detection
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.api_key: Optional[str] = None
        self.vault_path: Optional[str] = None
        self.logger = logging.getLogger("ClaudeService")
        self.event_bus = get_event_bus()
        
        # Processing state
        self._running = False
        self._processing_task: Optional[asyncio.Task] = None
        self._subscription_id: Optional[str] = None
        
        # Metrics
        self._plans_generated = 0
        self._errors = 0
        self._last_processed: Optional[str] = None
        
        # Load configuration
        self._load_config()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        self.logger.info("ClaudeService initialized")
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            self.api_key = os.getenv(ENV_CLAUDE_API_KEY) or self.config.get('claude', {}).get('api_key')
            self.vault_path = self.config.get('app', {}).get('vault_path', './AI_Employee_Vault')
            
            if not self.api_key:
                self.logger.warning("Claude API key not configured. Plan generation will use templates.")
            
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
            self.config = {}
            self.vault_path = './AI_Employee_Vault'
    
    def _setup_event_handlers(self):
        """Setup event-driven handlers."""
        # Listen for action generation events
        self._subscription_id = self.event_bus.subscribe(
            EventType.ACTION_GENERATED,
            self._on_action_generated,
            async_callback=True
        )
        
        self.logger.info("Event handlers registered")
    
    def _on_action_generated(self, event):
        """Handle action.generated events - trigger plan generation."""
        action_id = event.payload.get('action_id')
        action_path = event.payload.get('action_path')
        
        if action_path:
            self.logger.info(f"Processing action: {action_id}")
            asyncio.create_task(self.process_action_by_path(action_path))
    
    async def start(self):
        """Start the Claude service."""
        self._running = True
        self.logger.info("ClaudeService started")
        
        publish_event(
            EventType.SERVICE_STARTED,
            {"service": "claude_service"},
            source="claude_service"
        )
    
    async def stop(self):
        """Stop the Claude service."""
        self._running = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        if self._subscription_id:
            self.event_bus.unsubscribe(self._subscription_id)
        
        self.logger.info("ClaudeService stopped")
        
        publish_event(
            EventType.SERVICE_STOPPED,
            {"service": "claude_service"},
            source="claude_service"
        )
    
    def health_check(self) -> bool:
        """Check service health."""
        # Service is healthy if it's running and vault path exists
        return self._running and Path(self.vault_path).exists()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return {
            "plans_generated": self._plans_generated,
            "errors": self._errors,
            "last_processed": self._last_processed,
            "api_configured": bool(self.api_key),
            "vault_path": self.vault_path
        }
    
    async def process_action_by_path(self, action_path: str) -> Optional[PlanFile]:
        """
        Process an action file by its path.
        
        Args:
            action_path: Path to the action file
            
        Returns:
            Generated PlanFile or None if failed
        """
        try:
            if not Path(action_path).exists():
                self.logger.error(f"Action file not found: {action_path}")
                return None
            
            # Load action file
            action = ActionFile.from_file(action_path)
            return await self.process_action(action)
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Error processing action file {action_path}: {e}")
            publish_event(
                EventType.ACTION_FAILED,
                {"action_path": action_path, "error": str(e)},
                source="claude_service"
            )
            return None
    
    async def process_action(self, action: ActionFile) -> Optional[PlanFile]:
        """
        Process an action and generate a plan.
        
        Args:
            action: ActionFile to process
            
        Returns:
            Generated PlanFile
        """
        try:
            self.logger.info(f"Processing action: {action.id} (type: {action.type})")
            
            # Generate plan using Claude API or template
            if self.api_key:
                plan = await self._generate_plan_with_claude(action)
            else:
                plan = self._generate_plan_template(action)
            
            # Save plan file
            plan_path = self._save_plan_file(plan)
            self.logger.info(f"Plan saved: {plan_path}")
            
            # Update metrics
            self._plans_generated += 1
            self._last_processed = get_current_iso_timestamp()
            
            # Publish plan created event
            publish_event(
                EventType.PLAN_CREATED,
                {
                    "plan_id": plan.id,
                    "action_id": action.id,
                    "plan_path": str(plan_path),
                    "requires_approval": self.requires_approval(plan, action)
                },
                source="claude_service"
            )
            
            # If approval required, publish event
            if self.requires_approval(plan, action):
                publish_event(
                    EventType.APPROVAL_REQUIRED,
                    {
                        "plan_id": plan.id,
                        "action_id": action.id,
                        "reason": self._get_approval_reason(plan, action)
                    },
                    source="claude_service"
                )
            
            return plan
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Error processing action {action.id}: {e}")
            publish_event(
                EventType.ACTION_FAILED,
                {"action_id": action.id, "error": str(e)},
                source="claude_service"
            )
            return None
    
    async def _generate_plan_with_claude(self, action: ActionFile) -> PlanFile:
        """
        Generate plan using Claude API.
        
        Args:
            action: ActionFile to generate plan for
            
        Returns:
            Generated PlanFile
        """
        try:
            # Build prompt for Claude
            prompt = self._build_claude_prompt(action)
            
            # Call Claude API
            response = await self._call_claude_api(prompt)
            
            # Parse response and create plan
            plan_data = self._parse_claude_response(response, action)
            
            return PlanFile(
                action_id=action.id,
                objectives=plan_data['objectives'],
                steps=plan_data['steps'],
                resources=plan_data['resources'],
                success_criteria=plan_data['success_criteria'],
                estimated_duration=plan_data.get('estimated_duration', 30)
            )
            
        except Exception as e:
            self.logger.error(f"Claude API error, falling back to template: {e}")
            return self._generate_plan_template(action)
    
    def _build_claude_prompt(self, action: ActionFile) -> str:
        """Build prompt for Claude API."""
        context = action.context
        
        prompt = f"""You are an AI planning assistant. Generate a detailed execution plan for the following action:

ACTION TYPE: {action.type}
PRIORITY: {action.priority}
SOURCE: {action.source}

CONTEXT:
- Sender: {context.get('sender', 'Unknown')}
- Subject: {context.get('subject', 'No subject')}
- Body Preview: {context.get('body_preview', 'No preview available')}

Generate a plan with the following sections:

1. OBJECTIVES: Clear statement of what needs to be accomplished
2. STEPS: Numbered list of specific actions to take
3. RESOURCES: Tools, access, or information needed
4. SUCCESS CRITERIA: How to verify the action is complete
5. ESTIMATED_DURATION: Time in minutes (just the number)

Be specific and actionable. Format your response clearly with section headers."""

        return prompt
    
    async def _call_claude_api(self, prompt: str) -> Dict[str, Any]:
        """
        Call Claude API with the prompt.
        
        Args:
            prompt: Prompt to send to Claude
            
        Returns:
            API response as dictionary
        """
        # Import anthropic for Claude API
        try:
            from anthropic import AsyncAnthropic
            
            client = AsyncAnthropic(api_key=self.api_key)
            
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            return {
                "content": response.content[0].text,
                "model": response.model,
                "usage": response.usage.to_dict() if hasattr(response.usage, 'to_dict') else vars(response.usage)
            }
            
        except ImportError:
            self.logger.warning("Anthropic package not installed. Using mock response.")
            return self._get_mock_claude_response()
        except Exception as e:
            self.logger.error(f"Claude API call failed: {e}")
            return self._get_mock_claude_response()
    
    def _get_mock_claude_response(self) -> Dict[str, Any]:
        """Return a mock Claude response for testing/fallback."""
        return {
            "content": """OBJECTIVES: Process the requested action efficiently and accurately.

STEPS:
1. Review the action requirements
2. Gather necessary information
3. Execute the action according to best practices
4. Verify completion
5. Document results

RESOURCES: Standard office tools and system access

SUCCESS CRITERIA: Action completed as specified with proper documentation

ESTIMATED_DURATION: 30""",
            "model": "mock",
            "usage": {}
        }
    
    def _parse_claude_response(self, response: Dict[str, Any], action: ActionFile) -> Dict[str, Any]:
        """Parse Claude API response into plan components."""
        content = response.get('content', '')
        
        # Simple parsing - in production, use more robust parsing
        sections = {
            'objectives': '',
            'steps': '',
            'resources': '',
            'success_criteria': '',
            'estimated_duration': 30
        }
        
        current_section = None
        for line in content.split('\n'):
            line_lower = line.lower().strip()
            
            if 'objectives' in line_lower:
                current_section = 'objectives'
            elif 'steps' in line_lower:
                current_section = 'steps'
            elif 'resources' in line_lower:
                current_section = 'resources'
            elif 'success criteria' in line_lower or 'success_criteria' in line_lower:
                current_section = 'success_criteria'
            elif 'estimated_duration' in line_lower or 'estimated duration' in line_lower:
                # Extract number
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    sections['estimated_duration'] = int(numbers[0])
            elif current_section and line.strip():
                if sections[current_section]:
                    sections[current_section] += '\n' + line.strip()
                else:
                    sections[current_section] = line.strip()
        
        return sections
    
    def _generate_plan_template(self, action: ActionFile) -> PlanFile:
        """
        Generate plan from template (fallback when API not available).
        
        Args:
            action: ActionFile to generate plan for
            
        Returns:
            Generated PlanFile
        """
        action_type = action.type
        context = action.context
        
        # Template-based plan generation
        templates = self._get_plan_templates()
        template = templates.get(action_type, templates['default'])
        
        # Customize template with context
        objectives = template['objectives'].format(
            sender=context.get('sender', 'unknown'),
            subject=context.get('subject', 'no subject')
        )
        steps = template['steps']
        resources = template['resources']
        success_criteria = template['success_criteria']
        duration = template.get('estimated_duration', 30)
        
        return PlanFile(
            action_id=action.id,
            objectives=objectives,
            steps=steps,
            resources=resources,
            success_criteria=success_criteria,
            estimated_duration=duration
        )
    
    def _get_plan_templates(self) -> Dict[str, Dict[str, str]]:
        """Get plan templates for different action types."""
        return {
            'email_response': {
                'objectives': "Draft and send a response to the email from {sender}. Subject: {subject}. Address all points raised appropriately.",
                'steps': (
                    "1. Analyze the content and tone of the incoming email\n"
                    "2. Draft an appropriate response addressing all points\n"
                    "3. Review the response for accuracy and tone\n"
                    "4. Send the response to the sender\n"
                    "5. Log the response in the system"
                ),
                'resources': "- Email client access\n- Contact information",
                'success_criteria': (
                    "- Response sent to sender\n"
                    "- All points from original email addressed\n"
                    "- Appropriate tone maintained"
                ),
                'estimated_duration': 15
            },
            'meeting_request': {
                'objectives': "Schedule a meeting based on the request from {sender}. Subject: {subject}. Consider availability and preferences.",
                'steps': (
                    "1. Check calendar for available time slots\n"
                    "2. Identify appropriate time based on participants' schedules\n"
                    "3. Prepare meeting invitation with agenda\n"
                    "4. Send meeting invitation to all participants\n"
                    "5. Add meeting to calendar\n"
                    "6. Send confirmation to requester"
                ),
                'resources': "- Calendar access\n- Email integration\n- Contact information",
                'success_criteria': (
                    "- Meeting scheduled at mutually convenient time\n"
                    "- All required participants invited\n"
                    "- Calendar updated with meeting information"
                ),
                'estimated_duration': 30
            },
            'document_creation': {
                'objectives': "Create a document as requested by {sender}. Subject: {subject}. Include all required information.",
                'steps': (
                    "1. Gather all required information from the request\n"
                    "2. Choose appropriate document template\n"
                    "3. Populate the document with requested information\n"
                    "4. Review and proofread the document\n"
                    "5. Save the document in the appropriate location\n"
                    "6. Notify the requester that the document is ready"
                ),
                'resources': "- Document templates\n- Content guidelines\n- Access to relevant data/files",
                'success_criteria': (
                    "- Document created according to specifications\n"
                    "- Document saved in correct location\n"
                    "- Requester notified of completion"
                ),
                'estimated_duration': 60
            },
            'data_analysis': {
                'objectives': "Perform data analysis as requested by {sender}. Subject: {subject}. Provide insights and findings.",
                'steps': (
                    "1. Collect the required data from specified sources\n"
                    "2. Clean and preprocess the data\n"
                    "3. Perform the requested analysis\n"
                    "4. Generate visualizations if needed\n"
                    "5. Summarize findings and insights\n"
                    "6. Prepare a report with conclusions"
                ),
                'resources': "- Data sources\n- Analysis tools\n- Visualization tools",
                'success_criteria': (
                    "- Analysis completed as requested\n"
                    "- Insights and findings documented\n"
                    "- Report delivered to requester"
                ),
                'estimated_duration': 120
            },
            'report_generation': {
                'objectives': "Generate a report as requested by {sender}. Subject: {subject}. Include all relevant information.",
                'steps': (
                    "1. Gather all relevant information and data\n"
                    "2. Organize information according to report structure\n"
                    "3. Write the report following the required format\n"
                    "4. Include necessary charts, tables, and visuals\n"
                    "5. Review and edit for accuracy and clarity\n"
                    "6. Distribute the report to recipients"
                ),
                'resources': "- Data sources\n- Report templates\n- Visualization tools",
                'success_criteria': (
                    "- Report completed with all required sections\n"
                    "- Accurate information included\n"
                    "- Report distributed to recipients"
                ),
                'estimated_duration': 180
            },
            'follow_up': {
                'objectives': "Perform follow-up action as requested by {sender}. Subject: {subject}. Address the requirements.",
                'steps': (
                    "1. Identify the specific follow-up action required\n"
                    "2. Gather any additional information needed\n"
                    "3. Perform the follow-up action\n"
                    "4. Document the results\n"
                    "5. Notify relevant parties of completion"
                ),
                'resources': "- Email/calendar integration\n- Contact information\n- Related records",
                'success_criteria': (
                    "- Follow-up action completed successfully\n"
                    "- Relevant parties notified\n"
                    "- Records updated"
                ),
                'estimated_duration': 20
            },
            'default': {
                'objectives': "Process the action from {sender}. Subject: {subject}. Execute appropriately.",
                'steps': (
                    "1. Analyze the action requirements\n"
                    "2. Gather necessary resources and information\n"
                    "3. Execute the action according to best practices\n"
                    "4. Monitor for successful completion\n"
                    "5. Document the results"
                ),
                'resources': "- Standard office tools\n- Access to company systems",
                'success_criteria': (
                    "- Action completed as specified\n"
                    "- Quality standards met\n"
                    "- Proper documentation maintained"
                ),
                'estimated_duration': 45
            }
        }
    
    def _save_plan_file(self, plan: PlanFile) -> Path:
        """
        Save plan file to the Plans folder.
        
        Args:
            plan: PlanFile to save
            
        Returns:
            Path to saved file
        """
        plans_path = Path(self.vault_path) / "Plans"
        ensure_directory_exists(str(plans_path))
        
        plan_filename = f"{plan.action_id}.plan.md"
        plan_path = plans_path / plan_filename
        
        plan.save_to_file(str(plan_path))
        
        return plan_path
    
    def requires_approval(self, plan: PlanFile, action: ActionFile) -> bool:
        """
        Determine if a plan requires human approval.
        
        Args:
            plan: PlanFile
            action: Original ActionFile
            
        Returns:
            True if approval required
        """
        # High duration plans require approval
        if plan.estimated_duration and plan.estimated_duration > 120:
            return True
        
        # Certain action types require approval
        high_risk_types = ['data_analysis', 'report_generation', 'document_creation']
        if action.type in high_risk_types:
            return True
        
        # High priority actions might require approval
        if action.priority == 'high':
            return True
        
        return False
    
    def _get_approval_reason(self, plan: PlanFile, action: ActionFile) -> str:
        """Get the reason approval is required."""
        reasons = []
        
        if plan.estimated_duration and plan.estimated_duration > 120:
            reasons.append(f"High estimated duration ({plan.estimated_duration} minutes)")
        
        if action.type in ['data_analysis', 'report_generation']:
            reasons.append(f"Complex action type: {action.type}")
        
        if action.priority == 'high':
            reasons.append("High priority action")
        
        return "; ".join(reasons) if reasons else "Standard approval required"


# Export for orchestrator
def create_claude_service(config_path: str = "./config.yaml") -> ClaudeService:
    """Factory function to create ClaudeService."""
    return ClaudeService(config_path)
