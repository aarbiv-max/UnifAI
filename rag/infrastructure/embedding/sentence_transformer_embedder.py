import time
from typing import Dict, List, Any, Optional
from domain.vector.embedder import EmbeddingGenerator
from shared.logger import logger
import numpy as np
from sentence_transformers import SentenceTransformer

class SentenceTransformerEmbedding(EmbeddingGenerator):
    """
    Singleton embedding generator using the SentenceTransformers library.
    
    Implements efficient, high-quality embeddings for text chunks
    using state-of-the-art transformer models.
    """

    _instance = None

    def __new__(cls, model_name: str = "all-MiniLM-L6-v2", batch_size: int = 32, device: Optional[str] = None):
        """
        Ensure a single shared instance of SentenceTransformerEmbedding is returned (singleton constructor).
        
        Parameters:
            model_name (str): Model identifier to be used when the singleton is first initialized.
            batch_size (int): Default batch size to be used when the singleton is first initialized.
            device (Optional[str]): Device spec (e.g., "cpu", "cuda") to be used when the singleton is first initialized.
        
        Returns:
            SentenceTransformerEmbedding: The single shared instance of the embedding generator. Subsequent calls return the existing instance; provided parameters apply only on the first initialization.
        """
        if cls._instance is None:
            cls._instance = super(SentenceTransformerEmbedding, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self, 
        model_name: str = "all-MiniLM-L6-v2", 
        batch_size: int = 32,
        device: Optional[str] = None
    ):
        """
        Create and initialize the singleton SentenceTransformer embedding generator.
        
        Parameters:
            model_name (str): Pretrained SentenceTransformer model identifier to load (e.g., "all-MiniLM-L6-v2").
            batch_size (int): Number of text chunks processed per batch when generating embeddings.
            device (Optional[str]): Device for model execution ("cpu", "cuda", or None to let the library choose).
        """
        if self._initialized:
            return

        self.model_name = model_name
        self.device = device
        
        # Initialize the model
        logger.info(f"Loading SentenceTransformer model: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        
        # Set embedding dimension based on the loaded model
        embedding_dim = self.model.get_sentence_embedding_dimension()
        super().__init__(batch_size, embedding_dim)

        logger.info(f"Initialized embedding generator with dimension: {embedding_dim}")
        self._initialized = True

    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for each chunk and attach the resulting embedding to the chunk.
        
        Parameters:
            chunks (List[Dict[str, Any]]): Sequence of chunk dictionaries. Each chunk must contain a "text" key with the text to encode; other metadata keys are preserved.
        
        Returns:
            List[Dict[str, Any]]: A list of shallow copies of the input chunks where each chunk includes an "embedding" key holding the embedding vector. Returns an empty list if `chunks` is empty.
        """
        if not chunks:
            logger.warning("No chunks provided for embedding generation")
            return []
        
        start_time = time.time()
        logger.info(f"Starting embedding generation for {len(chunks)} chunks")
        
        result_chunks = []
        batch_index = 0
        
        for batch in self._batch_generator(chunks):
            batch_index += 1
            logger.debug(f"Processing batch {batch_index} with {len(batch)} chunks")
            
            # Extract text from chunks
            texts = [chunk["text"] for chunk in batch]
            
            # Generate embeddings for the batch
            embeddings = self.model.encode(texts, show_progress_bar=False)
            
            # Add embeddings to chunks
            for i, chunk in enumerate(batch):
                enriched_chunk = chunk.copy()
                enriched_chunk["embedding"] = embeddings[i]
                result_chunks.append(enriched_chunk)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Embedding generation completed in {elapsed_time:.2f} seconds")
        
        return result_chunks
    
    def generate_query_embedding(self, query: str) -> np.ndarray:
        """
        Compute an embedding vector for the given query text.
        
        Returns:
            NumPy ndarray containing the query's embedding vector.
        
        Raises:
            ValueError: If `query` is empty.
        """
        if not query:
            raise ValueError("Query text is empty")
        
        embedding = self.model.encode(query)
        return embedding
