"""Source Pipeline Port - Interface for source-specific pipeline operations."""
from abc import ABC, abstractmethod
from typing import Any, List, Dict
from dataclasses import dataclass

from domain.vector.model import VectorChunk


@dataclass(frozen=True)
class PipelineContext:
    """
    Immutable context for pipeline execution.
    
    Contains all the information needed to execute a pipeline
    for a specific source.
    """
    pipeline_id: str
    source_type: str
    source_id: str
    source_name: str
    metadata: Dict[str, Any]


class SourcePipelinePort(ABC):
    """
    Port defining source-specific pipeline operations.
    
    Each source type (Slack, Document, etc.) implements this interface
    to handle its specific data collection, processing, and embedding flow.
    
    The pipeline executor uses this port to orchestrate the pipeline
    without knowing the source-specific implementation details.
    """
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """
        Expose the source type identifier for this pipeline implementation.
        
        Returns:
            str: Source type identifier (for example, 'SLACK' or 'DOCUMENT').
        """
        ...
    
    @abstractmethod
    def collect(self, context: PipelineContext) -> Any:
        """
        Collect raw data from the source using the provided pipeline context.
        
        Parameters:
            context (PipelineContext): Execution metadata (pipeline and source identifiers and metadata) that scopes and informs collection.
        
        Returns:
            Any: Raw data retrieved from the source; the structure and type depend on the source implementation.
        """
        ...
    
    @abstractmethod
    def process(self, context: PipelineContext, raw_data: Any) -> Any:
        """
        Normalize raw collected data into a format suitable for chunking and embedding.
        
        Parameters:
            context (PipelineContext): Execution metadata for the current pipeline run.
            raw_data (Any): Source-specific data returned by the collect step.
        
        Returns:
            Any: Processed data ready for the chunk_and_embed step (structure is source-dependent).
        """
        ...
    
    @abstractmethod
    def chunk_and_embed(self, context: PipelineContext, processed: Any) -> List[VectorChunk]:
        """
        Split processed source data into chunks and produce embeddings for each chunk.
        
        Parameters:
            context (PipelineContext): Execution metadata that implementations may use to influence chunking or embedding (e.g., pipeline or source identifiers).
            processed (Any): Normalized data produced by the `process` step; its format depends on the source implementation.
        
        Returns:
            List[VectorChunk]: A list of VectorChunk instances containing chunked content and their corresponding embeddings.
        """
        ...
    
    @abstractmethod
    def get_summary(self, context: PipelineContext, collected: Any) -> Dict:
        """
        Produce a source-specific execution summary for reporting.
        
        Parameters:
            context (PipelineContext): Execution context for the pipeline run.
            collected (Any): Raw data returned by `collect`, used to derive summary metrics.
        
        Returns:
            Dict: A dictionary containing source-specific summary information (for example counts, processing stats, and error indicators).
        """
        ...
    
    def cleanup(self, context: PipelineContext) -> bool:
        """
        Perform optional source-specific cleanup tasks for the given pipeline context.
        
        Parameters:
            context (PipelineContext): Execution context for the pipeline.
        
        Returns:
            `True` if cleanup was performed, `False` otherwise.
        """
        return False
