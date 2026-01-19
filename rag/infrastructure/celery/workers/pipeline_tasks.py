"""
Pipeline execution Celery task - driving adapter.

This is a thin adapter that:
1. Receives Celery message (source_type, source_data)
2. Translates to domain types (PipelineContext)
3. Delegates to application layer (PipelineExecutor)

Logic is identical to backend/celery_app/tasks/pipeline_tasks.py,
but uses hexagonal architecture components.
"""
from global_utils.celery_app import CeleryApp
from bootstrap.app_container import pipeline_executor, get_pipeline_handler
from domain.pipeline.port import PipelineContext
from shared.logger import logger


def build_context(source_type: str, source_data: dict) -> PipelineContext:
    """
    Build a PipelineContext from a Celery message payload.
    
    Validates presence of pipeline_id and metadata, normalizes and augments metadata (injecting top-level type_data if present), and extracts source-specific identifiers for supported source types ("SLACK", "DOCUMENT").
    
    Parameters:
        source_type (str): Source type string (e.g., "SLACK", "DOCUMENT"); case-insensitive.
        source_data (dict): Incoming message payload expected to contain at least "pipeline_id" and "metadata".
    
    Returns:
        PipelineContext: Domain context with pipeline_id, uppercased source_type, source_id, source_name, and cleaned metadata.
    
    Raises:
        ValueError: If pipeline_id or metadata are missing, or if source_type is unsupported.
    """
    # Extract (same as backend lines 25-26)
    pipeline_id = source_data.get("pipeline_id")
    metadata_dict = source_data.get("metadata")
    
    # Validate (same as backend lines 27-28)
    if not pipeline_id or not metadata_dict:
        raise ValueError("Pipeline ID or metadata not found in source_data")
    
    # Clean metadata copy (same as backend lines 30-33)
    metadata = metadata_dict.copy()
    metadata.pop("pipeline_id", None)
    metadata.pop("type_data", None)
    
    # Get type_data from source_data top level (same as backend line 34)
    payload_type_data = source_data.get("type_data")
    if payload_type_data:
        metadata["type_data"] = payload_type_data
    
    # Extract source identifiers (same as backend lines 36-47)
    if source_type.upper() == "SLACK":
        source_id = metadata.get("channel_id", "")
        source_name = metadata.get("channel_name", "")
    elif source_type.upper() == "DOCUMENT":
        source_id = metadata.get("doc_id", "")
        source_name = metadata.get("doc_name", "")
    else:
        raise ValueError(f"Unsupported source type: {source_type}")
    
    return PipelineContext(
        pipeline_id=pipeline_id,
        source_type=source_type.upper(),
        source_id=source_id,
        source_name=source_name,
        metadata=metadata,
    )


@CeleryApp().app.task(bind=True)
def execute_pipeline_task(self, source_type: str, source_data: dict):
    """
    Execute a pipeline for the given source by building a domain context and delegating to the application executor.
    
    Parameters:
        source_type (str): Source type identifier (e.g., "SLACK", "DOCUMENT").
        source_data (dict): Registered source payload containing:
            - pipeline_id (str): Identifier of the pipeline to run.
            - metadata (dict): Source-specific metadata.
            - type_data (dict, optional): Additional source settings (may also appear at top level).
    
    Returns:
        dict: Execution outcome with keys:
            - pipeline_id (str): The pipeline identifier.
            - source_type (str): The provided source type.
            - status (str): `"success"` on successful execution.
            - result: The value returned by the pipeline executor.
    """
    try:
        logger.info(f"Starting pipeline execution for {source_type} source: {source_data}")
        
        # Translate (adapter's job - same logic as backend)
        context = build_context(source_type, source_data)
        
        # Delegate to application (hexagonal equivalent of backend's executor.run())
        handler = get_pipeline_handler(source_type)
        result = pipeline_executor().execute(handler, context)
        
        logger.info(f"Pipeline execution completed successfully for {source_type}: {context.pipeline_id}")
        
        # Return result (same structure as backend's PipelineExecutionResult)
        return {
            "pipeline_id": context.pipeline_id,
            "source_type": source_type,
            "status": "success",
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"Pipeline execution failed for {source_type}: {str(e)}", exc_info=True)
        raise
