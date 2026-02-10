"""
Claude service for AI Employee Foundation
Integrates with Claude Code to process action files and generate plan files
"""
import os
import time
from typing import Dict, Any, List
from pathlib import Path
import yaml
from datetime import datetime

from ..models.action_file import ActionFile
from ..models.plan_file import PlanFile
from ..lib.utils import get_current_iso_timestamp
from ..lib.exceptions import ClaudeServiceError
from ..lib.constants import ENV_CLAUDE_API_KEY


class ClaudeService:
    """
    Service that integrates with Claude Code to process action files and generate plan files.
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        """
        Initialize the Claude service with configuration.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.api_key = None
        self.vault_path = None
        
        # Load configuration
        self.load_config()
    
    def load_config(self):
        """Load configuration from the config file."""
        # In a real implementation, we would load the config file and extract the necessary values
        # For now, we'll use environment variables
        self.api_key = os.getenv(ENV_CLAUDE_API_KEY)
        self.vault_path = os.getenv("VAULT_PATH", "./AI_Employee_Vault")
    
    def process_action_file(self, action_file_path: str) -> PlanFile:
        """
        Process an action file and generate a plan file using Claude.
        
        Args:
            action_file_path: Path to the action file to process
            
        Returns:
            PlanFile instance
        """
        try:
            # Load the action file
            action = ActionFile.from_file(action_file_path)
            
            # Generate a plan based on the action
            plan = self.generate_plan(action)
            
            # Validate the plan
            plan.validate()
            
            return plan
            
        except Exception as e:
            raise ClaudeServiceError(f"Error processing action file {action_file_path}: {str(e)}")
    
    def generate_plan(self, action: ActionFile) -> PlanFile:
        """
        Generate a plan for the given action using Claude.
        
        Args:
            action: ActionFile instance to generate a plan for
            
        Returns:
            PlanFile instance
        """
        # In a real implementation, we would call the Claude API here
        # For this implementation, we'll simulate the Claude response
        
        # Create a plan based on the action
        plan = PlanFile(
            action_id=action.id,
            status="planned",  # Initially planned, waiting for approval
            objectives=self.generate_objectives(action),
            steps=self.generate_steps(action),
            resources=self.generate_resources(action),
            success_criteria=self.generate_success_criteria(action),
            estimated_duration=self.estimate_duration(action)
        )
        
        return plan
    
    def generate_objectives(self, action: ActionFile) -> str:
        """
        Generate objectives for the plan based on the action.
        
        Args:
            action: ActionFile instance
            
        Returns:
            Objectives as a string
        """
        action_type = action.type
        context = action.context
        
        if action_type == "meeting_request":
            return f"Schedule a meeting based on the request from {context.get('sender', 'unknown sender')}. " \
                   f"Subject: {context.get('subject', 'no subject')}. " \
                   f"Consider the sender's availability and preferences."
        elif action_type == "email_response":
            return f"Draft and send a response to the email from {context.get('sender', 'unknown sender')}. " \
                   f"Subject: {context.get('subject', 'no subject')}. " \
                   f"Address the points raised in the email appropriately."
        elif action_type == "document_creation":
            return f"Create a document as requested in the email from {context.get('sender', 'unknown sender')}. " \
                   f"Subject: {context.get('subject', 'no subject')}. " \
                   f"Include the information specified in the request."
        elif action_type == "data_analysis":
            return f"Perform data analysis as requested in the email from {context.get('sender', 'unknown sender')}. " \
                   f"Subject: {context.get('subject', 'no subject')}. " \
                   f"Analyze the data and provide insights."
        elif action_type == "report_generation":
            return f"Generate a report as requested in the email from {context.get('sender', 'unknown sender')}. " \
                   f"Subject: {context.get('subject', 'no subject')}. " \
                   f"Include all relevant information and findings."
        elif action_type == "follow_up":
            return f"Perform a follow-up action as requested in the email from {context.get('sender', 'unknown sender')}. " \
                   f"Subject: {context.get('subject', 'no subject')}. " \
                   f"Address the follow-up requirements."
        else:
            return f"Process the action of type '{action_type}' from {context.get('sender', 'unknown sender')}. " \
                   f"Subject: {context.get('subject', 'no subject')}. " \
                   f"Perform the requested action appropriately."
    
    def generate_steps(self, action: ActionFile) -> str:
        """
        Generate steps for the plan based on the action.
        
        Args:
            action: ActionFile instance
            
        Returns:
            Steps as a string
        """
        action_type = action.type
        context = action.context
        
        if action_type == "meeting_request":
            return (
                "1. Check calendar for available time slots\n"
                "2. Identify the most appropriate time based on participants' schedules\n"
                "3. Prepare meeting invitation with agenda\n"
                "4. Send meeting invitation to all participants\n"
                "5. Add meeting to calendar\n"
                "6. Send confirmation to requester"
            )
        elif action_type == "email_response":
            return (
                "1. Analyze the content and tone of the incoming email\n"
                "2. Draft an appropriate response addressing all points\n"
                "3. Review the response for accuracy and tone\n"
                "4. Send the response to the sender\n"
                "5. Log the response in the system"
            )
        elif action_type == "document_creation":
            return (
                "1. Gather all required information from the request\n"
                "2. Choose appropriate document template\n"
                "3. Populate the document with requested information\n"
                "4. Review and proofread the document\n"
                "5. Save the document in the appropriate location\n"
                "6. Notify the requester that the document is ready"
            )
        elif action_type == "data_analysis":
            return (
                "1. Collect the required data from specified sources\n"
                "2. Clean and preprocess the data\n"
                "3. Perform the requested analysis\n"
                "4. Generate visualizations if needed\n"
                "5. Summarize findings and insights\n"
                "6. Prepare a report with conclusions"
            )
        elif action_type == "report_generation":
            return (
                "1. Gather all relevant information and data\n"
                "2. Organize information according to report structure\n"
                "3. Write the report following the required format\n"
                "4. Include all necessary charts, tables, and visuals\n"
                "5. Review and edit the report for accuracy and clarity\n"
                "6. Distribute the report to the specified recipients"
            )
        elif action_type == "follow_up":
            return (
                "1. Identify the specific follow-up action required\n"
                "2. Gather any additional information needed\n"
                "3. Perform the follow-up action\n"
                "4. Document the results of the action\n"
                "5. Notify relevant parties of completion\n"
                "6. Update any related records or tasks"
            )
        else:
            return (
                "1. Analyze the action requirements\n"
                "2. Gather necessary resources and information\n"
                "3. Execute the action according to best practices\n"
                "4. Monitor the action for successful completion\n"
                "5. Document the results\n"
                "6. Notify relevant parties of completion"
            )
    
    def generate_resources(self, action: ActionFile) -> str:
        """
        Generate resources needed for the plan based on the action.
        
        Args:
            action: ActionFile instance
            
        Returns:
            Resources as a string
        """
        action_type = action.type
        context = action.context
        
        resources = []
        
        if action_type in ["meeting_request", "email_response", "follow_up"]:
            resources.append("- Email/calendar integration")
            resources.append("- Contact information")
        
        if action_type in ["document_creation", "report_generation"]:
            resources.append("- Document templates")
            resources.append("- Content guidelines")
            resources.append("- Access to relevant data/files")
        
        if action_type in ["data_analysis", "report_generation"]:
            resources.append("- Data sources")
            resources.append("- Analysis tools")
            resources.append("- Visualization tools")
        
        # Add any specific resources mentioned in the context
        if 'resources' in context:
            resources.extend(context['resources'])
        
        return "\n".join(resources) if resources else "Standard office tools and access to company systems"
    
    def generate_success_criteria(self, action: ActionFile) -> str:
        """
        Generate success criteria for the plan based on the action.
        
        Args:
            action: ActionFile instance
            
        Returns:
            Success criteria as a string
        """
        action_type = action.type
        context = action.context
        
        if action_type == "meeting_request":
            return (
                "- Meeting scheduled at mutually convenient time\n"
                "- All required participants invited\n"
                "- Meeting details confirmed with requester\n"
                "- Calendar updated with meeting information"
            )
        elif action_type == "email_response":
            return (
                "- Response sent to sender\n"
                "- All points from original email addressed\n"
                "- Appropriate tone maintained\n"
                "- Follow-up actions, if any, initiated"
            )
        elif action_type == "document_creation":
            return (
                "- Document created according to specifications\n"
                "- Document saved in correct location\n"
                "- Requester notified of completion\n"
                "- Document meets quality standards"
            )
        elif action_type == "data_analysis":
            return (
                "- Analysis completed as requested\n"
                "- Insights and findings documented\n"
                "- Visualizations created if required\n"
                "- Report delivered to requester"
            )
        elif action_type == "report_generation":
            return (
                "- Report completed with all required sections\n"
                "- Accurate and relevant information included\n"
                "- Report distributed to specified recipients\n"
                "- Quality standards met"
            )
        elif action_type == "follow_up":
            return (
                "- Follow-up action completed successfully\n"
                "- Relevant parties notified\n"
                "- Related records updated\n"
                "- Any required documentation completed"
            )
        else:
            return (
                "- Action completed as specified\n"
                "- Quality standards met\n"
                "- Relevant parties notified\n"
                "- Proper documentation maintained"
            )
    
    def estimate_duration(self, action: ActionFile) -> int:
        """
        Estimate the duration for the plan based on the action.
        
        Args:
            action: ActionFile instance
            
        Returns:
            Estimated duration in minutes
        """
        action_type = action.type
        
        # Default durations based on action type
        duration_map = {
            "email_response": 15,
            "meeting_request": 30,
            "follow_up": 20,
            "document_creation": 60,
            "data_analysis": 120,
            "report_generation": 180
        }
        
        return duration_map.get(action_type, 45)  # Default to 45 minutes
    
    def save_plan_file(self, plan: PlanFile, vault_path: str) -> str:
        """
        Save the plan file to the vault.
        
        Args:
            plan: PlanFile instance to save
            vault_path: Path to the vault where the plan should be saved
            
        Returns:
            Path to the saved plan file
        """
        # Create the Plans folder if it doesn't exist
        plans_path = Path(vault_path) / "Plans"
        plans_path.mkdir(parents=True, exist_ok=True)
        
        # Create the plan file name using the action ID
        plan_filename = f"{plan.action_id}.plan.md"
        plan_path = plans_path / plan_filename
        
        # Save the plan file
        plan.save_to_file(str(plan_path))
        
        return str(plan_path)
    
    def requires_approval(self, plan: PlanFile) -> bool:
        """
        Determine if a plan requires human approval.
        
        Args:
            plan: PlanFile instance
            
        Returns:
            True if the plan requires approval, False otherwise
        """
        # In a real implementation, we would have more sophisticated logic to determine
        # if a plan requires approval based on complexity, risk, cost, etc.
        # For this implementation, we'll say plans with high estimated duration or
        # certain action types require approval
        
        # Actions that typically require approval
        approval_required_types = ["data_analysis", "report_generation", "document_creation"]
        
        # High duration plans might require approval
        high_duration_threshold = 120  # minutes
        
        return (
            plan.action_id in approval_required_types or
            (plan.estimated_duration and plan.estimated_duration > high_duration_threshold)
        )
    
    def start_processing(self, vault_path: str, poll_interval: int = 30):
        """
        Start processing action files in the vault.
        
        Args:
            vault_path: Path to the vault where action files are located
            poll_interval: Interval in seconds between checking for new action files
        """
        print(f"Starting Claude processing. Checking for new action files every {poll_interval} seconds...")
        
        try:
            while True:
                # Find action files in the Needs_Action folder
                needs_action_path = Path(vault_path) / "Needs_Action"
                
                if needs_action_path.exists():
                    action_files = [f for f in needs_action_path.iterdir() if f.suffix == ".yaml"]
                    
                    if action_files:
                        print(f"Found {len(action_files)} action files to process")
                        
                        for action_file in action_files:
                            try:
                                print(f"Processing action file: {action_file.name}")
                                
                                # Process the action file
                                plan = self.process_action_file(str(action_file))
                                
                                # Save the plan file
                                plan_path = self.save_plan_file(plan, vault_path)
                                print(f"Plan file created: {plan_path}")
                                
                                # Determine if the plan requires approval
                                if self.requires_approval(plan):
                                    print(f"Plan {plan.id} requires approval, creating approval request...")
                                    # In a real implementation, we would create an approval file here
                                    # For now, we'll just print a message
                                else:
                                    print(f"Plan {plan.id} does not require approval, marking as approved...")
                                    # In a real implementation, we would move the plan to approved status
                                    # For now, we'll just print a message
                                
                                # Optionally, move the processed action file to a different folder
                                # For this implementation, we'll just leave it for now
                                
                            except Exception as e:
                                print(f"Error processing action file {action_file.name}: {str(e)}")
                                continue
                    else:
                        print("No action files to process")
                else:
                    print(f"Needs_Action folder does not exist: {needs_action_path}")
                
                # Wait before checking again
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            print("Claude processing stopped by user")
        except Exception as e:
            raise ClaudeServiceError(f"Error in Claude processing: {str(e)}")
    
    def stop_processing(self):
        """Stop processing action files."""
        print("Stopping Claude processing...")
        # In a real implementation, we would have a mechanism to stop the processing loop
        # For now, we'll just print a message