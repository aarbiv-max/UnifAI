"""Pipeline task dispatcher port (interface)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List


@dataclass
class TaskResult:
    """Result of dispatching an async pipeline task."""
    task_id: str
    queue: str
    source_type: str
    pipeline_id: str
    dispatched_at: datetime = None

    def __post_init__(self):
        """
        Set the dispatched_at timestamp to the current UTC time when it was not provided.
        
        If `dispatched_at` is None, assigns the current UTC datetime (naive `datetime` in UTC) to the field.
        """
        if self.dispatched_at is None:
            self.dispatched_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the TaskResult to a plain dictionary.
        
        The `dispatched_at` field is converted to an ISO 8601 string if present, otherwise `None`.
        
        Returns:
            dict: Mapping with keys `"task_id"`, `"queue"`, `"source_type"`, `"pipeline_id"`, and `"dispatched_at"`.
        """
        return {
            "task_id": self.task_id,
            "queue": self.queue,
            "source_type": self.source_type,
            "pipeline_id": self.pipeline_id,
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
        }


class PipelineTaskDispatcher(ABC):
    """
    Port for dispatching pipeline execution tasks to async workers.
    
    This is a Driven Port (secondary/output) - the application drives
    external task queues through this interface without knowing the
    implementation details (Celery, SQS, Redis Queue, etc.).
    """

    @abstractmethod
    def dispatch(
        self,
        source_type: str,
        source_data: Dict[str, Any],
    ) -> TaskResult:
        """
        Dispatch a pipeline execution task for a single source and return its dispatch metadata.
        
        Parameters:
            source_type (str): The source category (e.g., "DOCUMENT", "SLACK").
            source_data (Dict[str, Any]): Registered source data; must include a `pipeline_id` and may include additional metadata used for dispatching.
        
        Returns:
            TaskResult: Object containing dispatch details (`task_id`, `queue`, `source_type`, `pipeline_id`, `dispatched_at`).
        """
        ...

    @abstractmethod
    def dispatch_batch(
        self,
        source_type: str,
        sources: List[Dict[str, Any]],
    ) -> List[TaskResult]:
        """
        Dispatch multiple pipeline execution tasks to asynchronous workers.
        
        Parameters:
            source_type (str): Source category identifier (e.g., "DOCUMENT", "SLACK").
            sources (List[Dict[str, Any]]): List of registered source data entries; each entry should include the pipeline identifier and any metadata required for dispatch.
        
        Returns:
            List[TaskResult]: A list of TaskResult objects, one per dispatched task.
        """
        ...
