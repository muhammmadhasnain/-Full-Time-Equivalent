"""
MCP stub service for AI Employee Foundation
Provides dry-run execution with "would send" logging for approved actions
"""
import time
from typing import Dict, Any
from pathlib import Path

from ..models.plan_file import PlanFile
from ..lib.exceptions import MCPStubError
from ..lib.utils import get_current_iso_timestamp


class MCPStub:
    """
    Service that provides dry-run execution for approved actions.
    Logs "would send" actions instead of performing actual operations.
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        """
        Initialize the MCP stub with configuration.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.dry_run_enabled = True  # Default to dry-run mode
        self.execution_log = []
        
        # Load configuration
        self.load_config()
    
    def load_config(self):
        """Load configuration from the config file."""
        # In a real implementation, we would load the config file and extract the necessary values
        # For now, we'll check for a dry_run setting in environment variables or config
        import os
        self.dry_run_enabled = os.getenv("APPROVAL_DRY_RUN", "true").lower() == "true"
    
    def execute_plan(self, plan: PlanFile, action_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a plan in dry-run mode.
        
        Args:
            plan: PlanFile instance to execute
            action_context: Additional context from the original action
            
        Returns:
            Dictionary with execution results
        """
        try:
            execution_result = {
                'plan_id': plan.id,
                'action_id': plan.action_id,
                'status': 'executed' if not self.dry_run_enabled else 'dry_run_executed',
                'timestamp': get_current_iso_timestamp(),
                'steps_executed': [],
                'dry_run': self.dry_run_enabled
            }
            
            # Execute each step in the plan
            steps = self.parse_steps(plan.steps)
            
            for i, step in enumerate(steps):
                step_result = self.execute_step(step, i + 1, plan, action_context)
                execution_result['steps_executed'].append(step_result)
            
            # Log the execution
            self.log_execution(execution_result)
            
            return execution_result
            
        except Exception as e:
            raise MCPStubError(f"Error executing plan {plan.id}: {str(e)}")
    
    def parse_steps(self, steps_text: str) -> list:
        """
        Parse the steps text into individual steps.
        
        Args:
            steps_text: Text containing the steps
            
        Returns:
            List of individual steps
        """
        # Split the steps by line and filter out empty lines
        lines = steps_text.strip().split('\n')
        steps = []
        
        for line in lines:
            # Look for numbered steps (e.g., "1. ", "2. ", etc.)
            line = line.strip()
            if line.startswith(tuple(f"{i}." for i in range(1, 20))):  # Up to 19 steps
                # Remove the number prefix and add to steps
                step = line.split('.', 1)[1].strip()
                steps.append(step)
        
        return steps
    
    def execute_step(self, step: str, step_number: int, plan: PlanFile, action_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a single step of the plan.
        
        Args:
            step: The step to execute
            step_number: The number of this step
            plan: The plan containing this step
            action_context: Additional context from the original action
            
        Returns:
            Dictionary with step execution results
        """
        step_result = {
            'step_number': step_number,
            'step_description': step,
            'status': 'completed',
            'timestamp': get_current_iso_timestamp(),
            'dry_run': self.dry_run_enabled
        }
        
        # In dry-run mode, log what would happen instead of actually doing it
        if self.dry_run_enabled:
            self.log_dry_run_action(plan.action_id, plan.action_file.type if hasattr(plan, 'action_file') else 'unknown', step)
        else:
            # In real mode, perform the actual action
            # For this implementation, we'll just simulate the action
            self.perform_actual_action(step, plan, action_context)
        
        return step_result
    
    def log_dry_run_action(self, action_id: str, action_type: str, description: str):
        """
        Log a dry-run action (WOULD SEND pattern).
        
        Args:
            action_id: Unique identifier of the action
            action_type: Type of action that would be performed
            description: Description of what would happen
        """
        log_entry = f"WOULD SEND: ACTION_ID={action_id}, TYPE={action_type}, DESCRIPTION={description}"
        print(log_entry)  # In a real implementation, this would go to a proper logger
        
        # Add to execution log
        self.execution_log.append({
            'type': 'dry_run',
            'action_id': action_id,
            'action_type': action_type,
            'description': description,
            'timestamp': get_current_iso_timestamp()
        })
    
    def perform_actual_action(self, step: str, plan: PlanFile, action_context: Dict[str, Any] = None):
        """
        Perform an actual action (when dry-run is disabled).
        
        Args:
            step: The step to execute
            plan: The plan containing this step
            action_context: Additional context from the original action
        """
        # In a real implementation, this would perform the actual action
        # For this implementation, we'll just log that the action would be performed
        print(f"PERFORMING ACTUAL ACTION: {step}")
        
        # Add to execution log
        self.execution_log.append({
            'type': 'actual',
            'plan_id': plan.id,
            'step': step,
            'timestamp': get_current_iso_timestamp()
        })
    
    def log_execution(self, execution_result: Dict[str, Any]):
        """
        Log the execution result.
        
        Args:
            execution_result: Dictionary with execution results
        """
        # Add to execution log
        self.execution_log.append(execution_result)
        
        # Print summary
        status = "DRY RUN" if execution_result['dry_run'] else "REAL EXECUTION"
        print(f"[{status}] Plan {execution_result['plan_id']} executed with {len(execution_result['steps_executed'])} steps")
    
    def execute_from_file(self, plan_path: str, action_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a plan from a file.
        
        Args:
            plan_path: Path to the plan file
            action_context: Additional context from the original action
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Load the plan from file
            from ..models.plan_file import PlanFile
            plan = PlanFile.from_file(plan_path)
            
            # Execute the plan
            return self.execute_plan(plan, action_context)
            
        except Exception as e:
            raise MCPStubError(f"Error executing plan from file {plan_path}: {str(e)}")
    
    def get_execution_history(self) -> list:
        """
        Get the history of all executions.
        
        Returns:
            List of execution records
        """
        return self.execution_log
    
    def clear_execution_history(self):
        """Clear the execution history."""
        self.execution_log = []
    
    def enable_real_execution(self):
        """Enable real execution mode (disable dry-run)."""
        self.dry_run_enabled = False
        print("Real execution mode enabled. Actions will now be performed instead of logged.")
    
    def enable_dry_run(self):
        """Enable dry-run mode."""
        self.dry_run_enabled = True
        print("Dry-run mode enabled. Actions will be logged as 'WOULD SEND' instead of performed.")
    
    def start_execution_monitor(self, vault_path: str, poll_interval: int = 30):
        """
        Start monitoring for approved plans and execute them.
        
        Args:
            vault_path: Path to the vault where approved plans are located
            poll_interval: Interval in seconds between checking for new approved plans
        """
        print(f"Starting execution monitor. Checking for approved plans every {poll_interval} seconds...")
        
        try:
            approved_path = Path(vault_path) / "Approved"
            
            while True:
                if approved_path.exists():
                    # Find plan files that were approved (could be moved from Pending_Approval)
                    # In this implementation, we'll look for any plan files in the Approved folder
                    plan_files = [f for f in approved_path.iterdir() if f.suffix == ".md" and ".plan." in f.name]
                    
                    if plan_files:
                        print(f"Found {len(plan_files)} approved plans to execute")
                        
                        for plan_file in plan_files:
                            try:
                                print(f"Executing approved plan: {plan_file.name}")
                                
                                # Execute the plan
                                result = self.execute_from_file(str(plan_file))
                                
                                # After execution, move the plan to Done folder
                                done_path = Path(vault_path) / "Done"
                                done_path.mkdir(parents=True, exist_ok=True)
                                
                                # Move the file to the Done folder
                                dest_path = done_path / plan_file.name
                                plan_file.rename(dest_path)
                                
                                print(f"Plan executed and moved to Done: {dest_path.name}")
                                
                            except Exception as e:
                                print(f"Error executing plan {plan_file.name}: {str(e)}")
                                continue
                    else:
                        print("No approved plans to execute")
                else:
                    print(f"Approved folder does not exist: {approved_path}")
                
                # Wait before checking again
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            print("Execution monitoring stopped by user")
        except Exception as e:
            raise MCPStubError(f"Error in execution monitoring: {str(e)}")
    
    def stop_execution_monitor(self):
        """Stop monitoring for approved plans."""
        print("Stopping execution monitor...")
        # In a real implementation, we would have a mechanism to stop the monitoring loop
        # For now, we'll just print a message