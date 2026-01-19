"""
Simplified agent action executor for direct tool execution.

This module provides direct execution of agent actions using ToolExecutorManager
without unnecessary conversion layers. Supports both single and parallel execution.

Design Principles:
- Direct Execution: Uses ToolExecutorManager directly without conversion
- Parallel Support: Can execute multiple actions simultaneously
- Clean Error Handling: Simple, robust error handling
- No Special Tools: Removes unnecessary complexity
"""

import time
import asyncio
from typing import Dict, List, Optional, Tuple, Union
from elements.tools.common.base_tool import BaseTool
from elements.tools.common.execution import ToolExecutorManager, ExecutionMode
from elements.tools.common.execution.models import (
    ToolExecutionRequest, ToolExecutionResponse, BatchToolExecutionResponse
)
from ..primitives import AgentAction, AgentObservation, ActionStatus
from ..constants import ToolExecutionDefaults
from global_utils.utils.async_bridge import get_async_bridge
from core.stop_signal_context import should_stop, StoppedExecutionError


class AgentActionExecutor:
    """
    Simplified executor for agent actions using ToolExecutorManager.
    
    Provides direct execution of agent actions without conversion layers.
    Supports both single action execution and parallel batch execution.
    
    Features:
    - Direct ToolExecutorManager usage
    - Parallel action execution support
    - Clean error handling without special tools
    - Async and sync interfaces
    
    Example:
        executor = AgentActionExecutor(
            tool_executor_manager=tool_manager,
            validate_args=True
        )
        
        # Single action
        observation = executor.execute(action)
        
        # Multiple actions in parallel
        observations = executor.execute_batch([action1, action2])
    """
    
    def __init__(
        self,
        *,
        tool_executor_manager: ToolExecutorManager,
        validate_args: bool = ToolExecutionDefaults.VALIDATE_ARGS
    ):
        """
        Initialize agent action executor.
        
        Args:
            tool_executor_manager: ToolExecutorManager instance for tool execution
            validate_args: Whether to validate tool arguments before execution
        """
        self.tool_executor_manager = tool_executor_manager
        self.validate_args = validate_args
    
    def execute(self, action: AgentAction) -> AgentObservation:
        """
        Execute a single agent action and return observation.
        
        Args:
            action: Agent action to execute
            
        Returns:
            AgentObservation with execution results
        """
        result = self.execute_batch([action])[0]
        return result
    
    def execute_batch(self, actions: List[AgentAction]) -> List[AgentObservation]:
        """
        Execute multiple agent actions in parallel.
        
        Args:
            actions: List of agent actions to execute
            
        Returns:
            List of AgentObservations in same order as input actions
            
        Raises:
            StoppedExecutionError: If stop signal is detected before execution
        """
        if not actions:
            return []
        
        # Check for stop signal before starting batch execution
        if should_stop():
            raise StoppedExecutionError("Tool batch execution stopped by user")
        
        with get_async_bridge() as bridge:
            result = bridge.run(self._execute_batch_async(actions))
            return result
    
    async def _execute_batch_async(self, actions: List[AgentAction]) -> List[AgentObservation]:
        """
        Internal async method for batch execution.
        
        Includes periodic stop signal checking during long-running tool execution.
        If a stop signal is detected, returns immediately with stopped observations
        for tools that haven't completed yet.
        
        Args:
            actions: List of actions to execute
            
        Returns:
            List of observations in same order as actions
        """
        start_time = time.time()
        
        try:
            # Create ToolExecutionRequests and track missing tools
            requests = []
            missing_tools = []
            
            for action in actions:
                # Check if tool exists
                if not self.tool_executor_manager.has_tool(action.tool):
                    missing_tools.append(action)
                    continue
                
                request = ToolExecutionRequest(
                    tool_name=action.tool,
                    tool_call_id=action.id,
                    args=action.tool_input,
                    context={
                        "agent_action": True,
                        "action_id": action.id,
                        "validate_args": self.validate_args
                    }
                )
                requests.append(request)
            
            # Create observations for missing tools
            observations = []
            for action in missing_tools:
                observations.append(AgentObservation(
                    action_id=action.id,
                    tool=action.tool,
                    output=None,
                    success=False,
                    error=Exception(f"Tool '{action.tool}' not found"),
                    execution_time=time.time() - start_time
                ))
            
            if requests:
                # Execute via ToolExecutorManager with stop signal checking
                batch_response = await self._execute_with_stop_check(requests, start_time)
                
                # Convert responses to observations for successful tools
                for action in actions:
                    if action in missing_tools:
                        continue  # Already handled above
                        
                    response = batch_response.get_response(action.id)
                    
                    if response:
                        observation = self._response_to_observation(action, response, start_time)
                    else:
                        # Missing response - shouldn't happen but handle gracefully
                        observation = AgentObservation(
                            action_id=action.id,
                            tool=action.tool,
                            output=None,
                            success=False,
                            error=Exception(f"No response received for tool '{action.tool}'"),
                            execution_time=time.time() - start_time
                        )
                    
                    observations.append(observation)
            
            
            return observations
            
        except Exception as e:
            # Handle unexpected execution errors
            return [
                AgentObservation(
                    action_id=action.id,
                    tool=action.tool,
                    output=None,
                    success=False,
                    error=e,
                    execution_time=time.time() - start_time,
                    metadata={"error_type": "execution_error"}
                )
                for action in actions
            ]
    
    async def _execute_with_stop_check(
        self, 
        requests: List[ToolExecutionRequest],
        start_time: float,
        check_interval: float = 1.0
    ) -> BatchToolExecutionResponse:
        """
        Execute tool requests with periodic stop signal checking.
        
        Wraps the tool execution in a way that allows checking for stop signals
        every `check_interval` seconds. If a stop signal is detected during
        execution, raises StoppedExecutionError immediately.
        
        Note: The actual tool execution continues in the background but its
        result is discarded. This is the only way to handle non-cooperative
        tools in Python without using process-level isolation.
        
        Args:
            requests: Tool execution requests
            start_time: When execution started (for timing)
            check_interval: How often to check for stop signal (seconds)
            
        Returns:
            BatchToolExecutionResponse with tool results
            
        Raises:
            StoppedExecutionError: If stop signal is detected during execution
        """
        # Create the execution task
        execution_task = asyncio.create_task(
            self.tool_executor_manager.execute_requests_async(requests=requests)
        )
        
        try:
            while not execution_task.done():
                # Wait for either completion or timeout
                try:
                    # Wait with timeout for periodic stop checks
                    await asyncio.wait_for(
                        asyncio.shield(execution_task),
                        timeout=check_interval
                    )
                    # Task completed - break out of loop
                    break
                except asyncio.TimeoutError:
                    # Timeout - check for stop signal
                    if should_stop():
                        # Cancel the task (may not actually stop the underlying work)
                        execution_task.cancel()
                        raise StoppedExecutionError("Tool execution interrupted by stop signal")
            
            # Get the result
            return await execution_task
            
        except asyncio.CancelledError:
            # Re-raise as StoppedExecutionError
            raise StoppedExecutionError("Tool execution cancelled")
    
    def _response_to_observation(
        self, 
        action: AgentAction, 
        response: ToolExecutionResponse,
        start_time: float
    ) -> AgentObservation:
        """
        Convert ToolExecutionResponse to AgentObservation.
        
        Args:
            action: Original agent action
            response: Tool execution response
            start_time: Execution start time
            
        Returns:
            AgentObservation with converted data
        """
        return AgentObservation(
            action_id=action.id,
            tool=action.tool,
            output=response.result if response.success else None,
            success=response.success,
            error=Exception(str(response.error)) if response.error else None,
            execution_time=time.time() - start_time,
            metadata={
                "tool_execution_time": getattr(response, 'execution_time', None),
                "tool_call_id": response.tool_call_id
            }
        )

