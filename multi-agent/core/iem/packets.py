"""
IEM Packet Models

Base packet for transport layer and specific packet implementations.
Clean separation between transport concerns and payload.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import uuid
from .models import ElementAddress, PacketType


class BaseIEMPacket(BaseModel):
    """
    Base packet for all IEM communications.
    
    Handles transport layer concerns: routing, acknowledgment, lifecycle.
    Domain-agnostic - doesn't know about specific payload content.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    protocol: str = "iem/2.0"
    type: str  # Defined by subclasses (task, system, debug)
    ts: datetime = Field(default_factory=datetime.utcnow)
    ttl: Optional[timedelta] = None
    src: ElementAddress
    dst: ElementAddress

    ack_by: set[str] = Field(default_factory=set)
    
    @property
    def is_expired(self) -> bool:
        """Check if packet has expired based on TTL."""
        return self.ttl is not None and (datetime.utcnow() - self.ts) > self.ttl
    
    def acknowledge(self, uid: str) -> None:
        """Mark packet as acknowledged by given uid."""
        self.ack_by.add(uid)
    
    def is_acknowledged_by(self, uid: str) -> bool:
        """Check if packet is acknowledged by given uid."""
        return uid in self.ack_by


class TaskPacket(BaseIEMPacket):
    """
    Task packet that carries task payload.
    
    Transport layer handles routing, acknowledgment, lifecycle.
    Task payload handles agentic business logic and coordination.
    """
    type: PacketType = PacketType.TASK
    payload: Dict[str, Any]  # Task as dictionary
    
    @classmethod
    def create(cls, src: ElementAddress, dst: ElementAddress, 
               task: 'Task', **kwargs) -> 'TaskPacket':
        """
        Create task packet with task payload.
        
        Args:
            src: Source element address
            dst: Destination element address  
            task: Task to carry as payload
            **kwargs: Additional packet parameters
            
        Returns:
            TaskPacket instance
        """
        return cls(
            src=src,
            dst=dst,
            payload=task.model_dump(),
            **kwargs
        )
    
    def extract_task(self) -> 'Task':
        """
        Extract task from payload.
        
        Returns:
            Task instance from payload
            
        Raises:
            ValueError: If payload is not a valid task
        """
        from elements.nodes.common.workload import Task
        return Task.model_validate(self.payload)


# Additional packet types for future use
class SystemPacket(BaseIEMPacket):
    """System packet for system-level communication."""
    type: PacketType = PacketType.SYSTEM
    system_event: str
    data: Dict[str, Any] = Field(default_factory=dict)


class DebugPacket(BaseIEMPacket):
    """Debug packet for development and debugging."""
    type: PacketType = PacketType.DEBUG
    debug_info: Dict[str, Any] = Field(default_factory=dict)
