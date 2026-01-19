"""PDF chunking strategy implementation."""
from typing import Dict, List, Any
from domain.vector.chunker import ContentChunker
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter
from shared.logger import logger

class DoclingProcessingError(Exception):
    """Raised when docling fails to extract meaningful content from documents"""
    pass

class PDFChunkerStrategy(ContentChunker):
    """
    Implementation of ContentChunker for PDFs using langchain's RecursiveCharacterTextSplitter.
    
    This strategy intelligently chunks PDF content while preserving natural text boundaries
    and maintaining relationships between adjacent chunks.
    """
    
    def __init__(self, max_tokens_per_chunk: int = 500, overlap_tokens: int = 50):
        """
        Initialize the PDF chunker strategy and configure tokenization and character-based chunk sizing.
        
        Attempts to initialize a tiktoken encoder using the "cl100k_base" encoding; if initialization fails, the instance falls back to a token-estimation mode by leaving the tokenizer unset. Calls the base class initializer with the provided token limits and computes character-based chunk_size and chunk_overlap by assuming 4 characters per token.
        
        Parameters:
            max_tokens_per_chunk (int): Maximum number of tokens allowed in a single chunk.
            overlap_tokens (int): Number of tokens to overlap between adjacent chunks.
        """
        super().__init__(max_tokens_per_chunk, overlap_tokens)
        try:
            # Initialize tokenizer for token counting
            self.tokenizer = tiktoken.get_encoding("cl100k_base")  # Using OpenAI's tokenizer
            logger.info("Initialized tiktoken tokenizer with cl100k_base encoding")
        except Exception as e:
            logger.warning(f"Failed to initialize tiktoken: {e}. Using fallback token estimation.")
            self.tokenizer = None
            
        # Convert token sizes to approximate character counts (rough estimate)
        # Assuming average of 4 characters per token for English text
        chars_per_token = 4
        self.chunk_size = max_tokens_per_chunk * chars_per_token
        self.chunk_overlap = overlap_tokens * chars_per_token
        
        logger.info(f"Initialized PDFChunkerStrategy with chunk_size={self.chunk_size} chars and "
                   f"chunk_overlap={self.chunk_overlap} chars")
    
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string using the initialized tokenizer or a character-based fallback.
        
        Parameters:
            text (str): Input text to estimate token count for.
        
        Returns:
            int: Estimated number of tokens in the input text.
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback estimation: approximately 4 characters per token for English
            return len(text) // 4
    
    def chunk_content(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Produce content chunks from PDF documents while preserving natural text boundaries.
        
        Splits each document's 'content' into chunks using paragraph- and sentence-aware boundaries, estimates token counts (using the configured tokenizer or a fallback), and returns chunks enriched with metadata including chunk_index, total_chunks, token_count, document_id, filename, and adjacent chunk references (`prev_chunk_id`, `next_chunk_id`). Documents with empty or missing content are skipped.
        
        Parameters:
            documents (List[Dict[str, Any]]): List of document objects. Each document is expected to include:
                - 'content' (str): Raw text to split.
                - 'id' (str, optional): Document identifier (used to build chunk ids).
                - 'filename' (str, optional): Human-readable filename for logging/metadata.
                - 'metadata' (dict, optional): Additional metadata to merge into each chunk's metadata.
        
        Returns:
            List[Dict[str, Any]]: List of chunk dictionaries, each with keys:
                - 'id' (str): Unique chunk id of the form "<document_id>_chunk_<index>".
                - 'text' (str): Chunk text.
                - 'metadata' (dict): Chunk metadata as described above.
        """
        logger.info(f"Starting to chunk {len(documents)} PDF documents")
        self._chunks = []
        
        for doc in documents:
            logger.info(f"Starting chunking procedure for: {doc.get('filename', 'Unknown')}")
            
            content = doc.get('content', '')
            if not content:
                logger.warning(f"Empty content for document {doc.get('filename', 'Unknown')}")
                continue
                
            # Create a text splitter that respects natural boundaries
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]  # Order matters: prefer splitting at paragraphs, then sentences
            )
            
            logger.info(f"Created RecursiveCharacterTextSplitter with chunk_size={self.chunk_size}, "
                       f"chunk_overlap={self.chunk_overlap}")
            
            # Split the text
            logger.info(f"Splitting content of {doc.get('filename', 'Unknown')}")
            
            raw_chunks = text_splitter.split_text(content)
            
            # Process chunks and add metadata
            doc_chunks = []
            for i, chunk_text in enumerate(raw_chunks):
                # Estimate token count for this chunk
                token_count = self.estimate_token_count(chunk_text)
                
                # Create chunk with metadata
                chunk = {
                    "id": f"{doc.get('id', 'unknown')}_chunk_{i}",
                    "text": chunk_text,
                    "metadata": {
                        **doc.get('metadata', {}),  # Include original document metadata
                        "chunk_index": i,
                        "total_chunks": len(raw_chunks),
                        "token_count": token_count,
                        "document_id": doc.get('id', 'unknown'),
                        "filename": doc.get('filename', 'unknown'),
                        # Add adjacent chunk references
                        "prev_chunk_id": f"{doc.get('id', 'unknown')}_chunk_{i-1}" if i > 0 else None,
                        "next_chunk_id": f"{doc.get('id', 'unknown')}_chunk_{i+1}" if i < len(raw_chunks) - 1 else None
                    }
                }
                
                doc_chunks.append(chunk)
            
            self._chunks.extend(doc_chunks)
        
        logger.info(f"Completed chunking with {len(self._chunks)} total chunks generated")

        return self._chunks