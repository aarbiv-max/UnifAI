"""Document Pipeline Handler - Source-specific pipeline operations for Documents."""
from typing import List, Dict, Any

from domain.pipeline.port import SourcePipelinePort, PipelineContext
from domain.vector.embedder import EmbeddingGenerator
from domain.vector.model import VectorChunk
from domain.processor.document_processor import DocumentProcessor
from infrastructure.connector.document_connector import DocumentConnector
from infrastructure.chunking.pdf_chunker import PDFChunkerStrategy
from shared.logger import logger

from global_utils.utils import cleanup_file


class DocumentPipelineHandler(SourcePipelinePort):
    """
    Handler for Document pipeline operations.
    
    Coordinates document-specific data flow through collection,
    processing, and embedding stages.
    
    This handler:
    - Collects document content (PDF, markdown, etc.)
    - Processes document text (cleans, normalizes)
    - Chunks content and generates embeddings
    - Cleans up temporary files after execution
    """
    
    def __init__(
        self,
        connector: DocumentConnector,
        processor: DocumentProcessor,
        chunker: PDFChunkerStrategy,
        embedder: EmbeddingGenerator,
    ):
        """
        DocumentPipelineHandler initializer.
        
        Store the provided connector, processor, chunker, and embedder on the instance and initialize the internal collected-data cache.
        """
        self._connector = connector
        self._processor = processor
        self._chunker = chunker
        self._embedder = embedder
        self._cached_collected = None
    
    @property
    def source_type(self) -> str:
        """
        Identify the pipeline's source type.
        
        Returns:
            The source type string "DOCUMENT".
        """
        return "DOCUMENT"
    
    def collect(self, context: PipelineContext) -> Dict:
        """
        Collect the document specified in the pipeline context and cache the result.
        
        Parameters:
        	context (PipelineContext): Pipeline context whose metadata must include `doc_path` (path to the document) and may include `upload_by`.
        
        Returns:
        	collected (Dict): Document data dictionary containing the document content and associated metadata; also stored in the handler's internal cache.
        """
        logger.info(f"Collecting document: {context.metadata.get('doc_path')}")
        
        self._cached_collected = self._connector.process_document(
            document_path=context.metadata.get("doc_path"),
            upload_by=context.metadata.get("upload_by"),
        )
        return self._cached_collected
    
    def process(self, context: PipelineContext, raw_data: Dict) -> Dict:
        """
        Process raw document data into a normalized document dictionary suitable for downstream pipeline steps.
        
        Parameters:
            context (PipelineContext): Pipeline execution context with metadata about the document.
            raw_data (dict): Raw document data produced by the collection step.
        
        Returns:
            dict: Processed document dictionary with normalized fields and the original content preserved.
        """
        return self._processor.process(
            raw_data,
            clean_markdown=False,
            clean_text=False,
            remove_references=False,
            preserve_original=True,
        )
    
    def chunk_and_embed(self, context: PipelineContext, processed: Dict) -> List[VectorChunk]:
        """
        Prepare a processed document for vector storage by chunking its content, attaching source metadata, and generating embeddings for each chunk.
        
        Parameters:
            context (PipelineContext): Pipeline context; its `source_id` is added to each chunk's metadata.
            processed (Dict): Processed document data ready for chunking and embedding.
        
        Returns:
            List[VectorChunk]: A list of VectorChunk objects, each containing the chunk text, its embedding (numeric sequence), and metadata that includes `source_id` and `source_type`.
        """
        # Prepare document for embedding
        embedding_ready = self._processor.prepare_for_single_doc_embedding(processed)
        
        # Chunk the content
        chunks = self._chunker.chunk_content([embedding_ready])
        
        # Enrich with source metadata
        for idx, chunk in enumerate(chunks):
            chunk.setdefault("metadata", {}).update({
                "source_id": context.source_id,
                "source_type": self.source_type,
            })
        
        # Generate embeddings and convert to domain objects
        enriched_dicts = self._embedder.generate_embeddings(chunks)
        
        return [
            VectorChunk(
                text=d["text"],
                embedding=d["embedding"].tolist() if hasattr(d["embedding"], 'tolist') else d["embedding"],
                metadata=d.get("metadata", {})
            )
            for d in enriched_dicts
        ]
    
    def get_summary(self, context: PipelineContext, collected: Any) -> Dict:
        """
        Return a document summary containing page count, full text, and file size.
        
        Returns:
            dict: {
                "page_count": int — number of pages (0 if unavailable),
                "full_text": str — full document text (empty string if unavailable),
                "file_size": int — file size in bytes (0 if unavailable)
            }
        """
        if self._cached_collected:
            return {
                "page_count": self._cached_collected.get("metadata", {}).get("page_count", 0),
                "full_text": self._cached_collected.get("text", ""),
                "file_size": self._cached_collected.get("metadata", {}).get("file_size", 0),
            }
        return {
            "page_count": 0,
            "full_text": "",
            "file_size": 0,
        }
    
    def cleanup(self, context: PipelineContext) -> bool:
        """
        Remove the uploaded document file referenced by the pipeline context.
        
        Parameters:
            context (PipelineContext): Pipeline context whose metadata should contain `"doc_path"` specifying the file path to remove.
        
        Returns:
            bool: `True` if the file was removed, `False` otherwise.
        """
        doc_path = context.metadata.get("doc_path")
        if doc_path:
            return cleanup_file(doc_path, "after pipeline completion")
        return False