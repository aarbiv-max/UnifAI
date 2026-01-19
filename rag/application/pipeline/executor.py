"""Pipeline Executor - Application use case for orchestrating pipeline execution."""
from typing import Any, Callable

from domain.pipeline.port import SourcePipelinePort, PipelineContext
from domain.pipeline.model import PipelineStatus
from domain.vector.repository import VectorRepository
from application.pipeline_service import PipelineService
from application.monitoring_service import MonitoringService
from application.data_source_service import DataSourceService
from shared.logger import logger


class PipelineExecutor:
    """
    Application use case: orchestrates pipeline execution.
    
    This executor is source-agnostic and delegates source-specific behavior
    to the injected SourcePipelinePort handler.
    
    Responsibilities:
    - Pipeline registration and status tracking
    - Log monitoring (orchestration)
    - Error recording on failure
    - Source upsert on success/failure
    - Cleanup
    
    Usage:
        executor = pipeline_executor()  # from app_container
        handler = get_pipeline_handler("SLACK")
        context = PipelineContext(...)
        result = executor.execute(handler, context)
    """
    
    def __init__(
        self,
        pipeline_service: PipelineService,
        monitoring_service: MonitoringService,
        data_source_service: DataSourceService,
        vector_repository: Callable[[str], VectorRepository],
    ):
        """
        Create a PipelineExecutor with required service dependencies and a vector repository factory.
        
        Parameters:
            pipeline_service (PipelineService): Manages pipeline registration, status updates, and persistence.
            monitoring_service (MonitoringService): Manages log monitoring and error recording during execution.
            data_source_service (DataSourceService): Performs upsert operations for source metadata after a run.
            vector_repository (Callable[[str], VectorRepository]): Factory that returns a VectorRepository given a collection name.
        """
        self._pipeline_svc = pipeline_service
        self._monitoring_svc = monitoring_service
        self._data_source_svc = data_source_service
        self._vector_repository = vector_repository
    
    def execute(
        self, 
        handler: SourcePipelinePort, 
        context: PipelineContext
    ) -> Any:
        """
        Orchestrates a full pipeline run using the provided source handler and execution context.
        
        Executes collection, processing, chunking/embedding, and storing steps in sequence while updating pipeline status, managing log monitoring, and upserting source metadata on success or failure.
        
        Parameters:
            handler: Source-specific pipeline handler implementing the SourcePipelinePort interface.
            context: Pipeline execution context containing pipeline_id, source_id, source_name, and other metadata required for the run.
        
        Returns:
            The result of the storing step (typically the number of embeddings stored).
        """
        source_type = handler.source_type
        vector_repo = self._vector_repository(f"{source_type.lower()}_data")
        
        # Register pipeline
        self._pipeline_svc.register(context.pipeline_id, source_type)
        
        # Start log monitoring (orchestration)
        monitoring_pipeline_id = f"{source_type.lower()}_{context.source_id}"
        self._monitoring_svc.start_log_monitoring(
            pipeline_id=monitoring_pipeline_id,
            target_logger=logger,
        )
        
        collected = None
        current_step = None
        
        try:
            # Step 1: Collect
            current_step = PipelineStatus.COLLECTING
            self._pipeline_svc.update_status(context.pipeline_id, current_step)
            collected = handler.collect(context)
            
            # Step 2: Process
            current_step = PipelineStatus.PROCESSING
            self._pipeline_svc.update_status(context.pipeline_id, current_step)
            processed = handler.process(context, collected)
            
            # Step 3: Chunk & Embed
            current_step = PipelineStatus.CHUNKING_AND_EMBEDDING
            self._pipeline_svc.update_status(context.pipeline_id, current_step)
            embeddings = handler.chunk_and_embed(context, processed)
            
            # Step 4: Store
            current_step = PipelineStatus.STORING
            self._pipeline_svc.update_status(context.pipeline_id, current_step)
            result = vector_repo.store(embeddings)
            
            # Success - update status
            self._pipeline_svc.update_status(context.pipeline_id, PipelineStatus.DONE)
            
            # Upsert source with summary
            summary = handler.get_summary(context, collected)
            self._data_source_svc.upsert_after_pipeline(
                source_id=context.source_id,
                source_name=context.source_name,
                source_type=source_type,
                pipeline_id=context.pipeline_id,
                summary=summary,
            )
            
            return result
            
        except Exception as e:
            # Record error
            self._monitoring_svc.record_error(
                pipeline_id=context.pipeline_id,
                error_message=str(e),
                error_details={"failed_at": current_step.value if current_step else "UNKNOWN"},
            )
            
            # Update status to failed
            self._pipeline_svc.update_status(context.pipeline_id, PipelineStatus.FAILED)
            
            # Upsert source with error info
            self._data_source_svc.upsert_after_pipeline(
                source_id=context.source_id,
                source_name=context.source_name,
                source_type=source_type,
                pipeline_id=context.pipeline_id,
                summary={
                    "last_error": str(e),
                    "failed_at": current_step.value if current_step else "UNKNOWN",
                },
            )
            
            raise
            
        finally:
            # Always cleanup: stop monitoring and run handler cleanup
            self._monitoring_svc.finish_log_monitoring()
            handler.cleanup(context)
