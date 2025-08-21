from typing import List, ClassVar, Dict, Any
from elements.nodes.common.base_node import BaseNode
from elements.nodes.common.capabilities.iem_capable import IEMCapableMixin
from graph.state.graph_state import Channel
from graph.state.state_view import StateView
from elements.nodes.common.workload import AgentResult


class FinalAnswerNode(IEMCapableMixin, BaseNode):
    """
    Enhanced final node that collects task results and creates final output.
    
    Behavior:
    - Processes TaskPackets and extracts task results
    - Collects all AgentResults from tasks
    - Merges them into one final message
    - Promotes to messages and sets Channel.OUTPUT
    """
    
    READS: ClassVar[set[str]] = {Channel.MESSAGES}
    WRITES: ClassVar[set[str]] = {Channel.MESSAGES, Channel.OUTPUT}

    def __init__(self, *, name: str = "final_answer", **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self._collected_results: List[AgentResult] = []

    def run(self, state: StateView) -> StateView:
        """Process all incoming TaskPackets and create final answer."""
        # Process all incoming task packets
        self.process_packets(state)
        
        # Create final answer if we have collected results
        if self._collected_results:
            final_answer = self._merge_results()
            self.promote_to_messages(final_answer)
            state[Channel.OUTPUT] = final_answer
            
            # Clear collected results
            self._collected_results.clear()
        
        return state

    def handle_task_packet(self, packet) -> None:
        """
        Collect task results from TaskPackets.
        
        Extracts task from packet and collects AgentResult if present.
        """
        try:
            task = packet.extract_task()

            # Extract AgentResult from task if present
            if task.result and isinstance(task.result, AgentResult):
                self._collected_results.append(task.result)
                print(f"FinalAnswerNode {self.uid}: Collected result from {task.result.agent_name}")
                
        except Exception as e:
            print(f"FinalAnswerNode {self.uid}: Error collecting task result: {e}")

    def _merge_results(self) -> str:
        """Merge all collected AgentResult objects into one final message."""
        if not self._collected_results:
            return "I apologize, but I don't have any information to provide."
        
        if len(self._collected_results) == 1:
            return self._collected_results[0].content
        
        # Remove duplicates while preserving order
        unique_contents = []
        seen = set()
        for result in self._collected_results:
            content = result.content.strip()
            if content and content not in seen:
                unique_contents.append(content)
                seen.add(content)
        
        if len(unique_contents) == 1:
            return unique_contents[0]
        
        # Join multiple unique results
        return "\n\n".join(unique_contents)