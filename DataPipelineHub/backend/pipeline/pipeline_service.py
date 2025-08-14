from typing import List, Dict, Any, Tuple
from flask import session
from shared.logger import logger
from global_utils.celery_app.helpers import send_task
from global_utils.celery_app import CeleryApp

class PipelineCeleryService:
    """
    Celery-based service class for managing pipeline worker tasks and distributed operations.
    Handles the orchestration of Celery workers for pipeline registration and execution workflows
    with proper separation of concerns between synchronous coordination and asynchronous task execution.
    """
    
    def __init__(self):
        self.celery_app = CeleryApp().app
    
    def execute_pipeline_workflow_with_registration(self, data: List[Dict[str, Any]], source_type: str) -> Tuple[Dict[str, Any], int]:
        """
        Execute a complete pipeline workflow using Celery workers with source registration.
        First dispatches registration tasks to workers, waits for completion, then submits 
        pipeline execution tasks to appropriate worker queues.
        
        Args:
            data: List of data sources to register and process via Celery workers
            source_type: Type of data source (SLACK, DOCUMENT, etc.) for worker queue routing
            
        Returns:
            Tuple of (response_data, status_code)
            
        Raises:
            Exception: If Celery task registration or worker task submission fails
        """
        try:
            current_user = session.get('user', {}).get('username', 'default')
            registered_sources = self._execute_registration_tasks_sync(data, source_type, current_user)
            pipeline_worker_tasks_submitted = self._dispatch_pipeline_worker_tasks(registered_sources, source_type)
            
            response_data = {
                "status": "pipeline_celery_workflow_started",
                "message": f"Registration completed via Celery workers and pipeline started for {len(registered_sources)} {source_type} sources",
                "registration_completed": True,
                "pipeline_worker_tasks_submitted": pipeline_worker_tasks_submitted,
                "source_count": len(registered_sources),
            }
            return response_data, 202
            
        except Exception as e:
            logger.error(f"Failed to execute Celery pipeline workflow with registration: {str(e)}")
            raise e
    
    def _execute_registration_tasks_sync(self, data: List[Dict[str, Any]], source_type: str, current_user: str) -> List[Dict[str, Any]]:
        """
        Execute source registration tasks synchronously via Celery workers and return registered sources.
        Waits for Celery worker completion before proceeding to next workflow step.
        
        Args:
            data: List of data sources to register via Celery workers
            source_type: Type of data source for worker queue routing
            current_user: Username of the current user for worker task context
            
        Returns:
            List of registered sources from Celery worker results
            
        Raises:
            Exception: If Celery registration task fails or worker timeout occurs
        """
        celery_registration_result = self.celery_app.send_task(
            "celery_app.tasks.pipeline_tasks.register_sources_task",
            kwargs={
                "data_list": data,
                "source_type": source_type.upper(),
                "upload_by": current_user
            },
            queue="registration_queue"  
        )
        
        # Wait for Celery worker registration completion with 5 minute timeout
        celery_registration_response = celery_registration_result.get(timeout=300)
        registered_sources = celery_registration_response.get("registered_sources", [])
        
        if not registered_sources:
            raise ValueError("No sources were registered successfully by Celery workers")
            
        return registered_sources
    
    def _dispatch_pipeline_worker_tasks(self, registered_sources: List[Dict[str, Any]], source_type: str) -> int:
        """
        Dispatch pipeline execution tasks to appropriate Celery worker queues for registered sources.
        Routes tasks to specialized worker queues based on source type for optimal processing.
        
        Args:
            registered_sources: List of registered source data from previous Celery worker results
            source_type: Type of data source for Celery worker queue routing
            
        Returns:
            Number of pipeline worker tasks successfully dispatched to Celery queues
        """
        pipeline_worker_tasks_submitted = 0
        
        for source_data in registered_sources:
            send_task(
                task_name="celery_app.tasks.pipeline_tasks.execute_pipeline_task",
                celery_queue=f"{source_type.lower()}_queue",
                source_type=source_type.upper(),
                source_data=source_data
            )
            pipeline_worker_tasks_submitted += 1
            
        return pipeline_worker_tasks_submitted 