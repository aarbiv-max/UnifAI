from typing import Dict, Any
from .remote_embedding_generator import RemoteEmbeddingGenerator
from .embedding_generator import EmbeddingGenerator

# Factory class for creating embedding generators
class EmbeddingGeneratorFactory:
    """Factory for creating remote embedding generator instances."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> EmbeddingGenerator:
        """
        Create a remote embedding generator instance.
        
        Args:
            config: Configuration for the embedding generator
            
        Returns:
            Initialized remote embedding generator
        """
        return RemoteEmbeddingGenerator(
            service_url=config.get("service_url"),
            timeout=config.get("timeout") if config.get("timeout", 0) > 0 else None,
            model_name=config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
            batch_size=config.get("batch_size", 32),
            embedding_dim=config.get("embedding_dim", 384)
        )