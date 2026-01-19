"""Factory classes for creating adapter instances."""

import os
import torch
from typing import Dict, Any, Optional

from infrastructure.embedding.sentence_transformer_embedder import SentenceTransformerEmbedding
from infrastructure.qdrant.qdrant_vector_repository import QdrantVectorRepository
from domain.vector.embedder import EmbeddingGenerator
from domain.vector.repository import VectorRepository

device = "cuda" if torch.cuda.is_available() else "cpu"


class EmbeddingGeneratorFactory:
    """Factory for creating embedding generator instances based on configuration."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> EmbeddingGenerator:
        """
        Create an EmbeddingGenerator based on the provided configuration.
        
        Parameters:
            config (Dict[str, Any]): Configuration dictionary. Recognized keys:
                - type: Embedding generator type (default: "sentence_transformer").
                - model_name: Model identifier for sentence transformer (default: "all-MiniLM-L6-v2").
                - batch_size: Inference batch size (default: 32).
                - device: Computation device (e.g., "cpu", "cuda"); defaults to module-detected device.
        
        Returns:
            EmbeddingGenerator: An initialized embedding generator instance configured per `config`.
        
        Raises:
            ValueError: If `type` specifies an unknown embedding generator.
        """
        generator_type = config.get("type", "sentence_transformer")
        
        if generator_type == "sentence_transformer":
            return SentenceTransformerEmbedding(
                model_name=config.get("model_name", "all-MiniLM-L6-v2"),
                batch_size=config.get("batch_size", 32),
                device=config.get("device", device)
            )
        else:
            raise ValueError(f"Unknown embedding generator type: {generator_type}")


class VectorRepositoryFactory:
    """Factory for creating vector repository instances based on configuration."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> VectorRepository:
        """
        Create a VectorRepository based on the provided configuration.
        
        Parameters:
            config (Dict[str, Any]): Configuration mapping that may include:
                - type: Storage type identifier (default: "qdrant").
                - collection_name: Name of the collection (default: "default_collection").
                - embedding_dim: Embedding dimensionality (default: 384).
                - url: Qdrant server URL (default: value of QDRANT_URL environment variable).
                - port: Qdrant server port (default: value of QDRANT_PORT env var or "6333").
                - grpc_port: Qdrant gRPC port (optional).
                - api_key: API key for Qdrant (optional; can be provided via QDRANT_API_KEY).
                - on_disk: Whether to persist data on disk (default: True).
                - replication_factor: Replication factor for the collection (default: 1).
                - write_consistency_factor: Write consistency factor for the collection (default: 1).
        
        Returns:
            VectorRepository: An initialized vector repository instance configured per `config`.
        
        Raises:
            ValueError: If `type` in config is not a recognized vector storage type.
        """
        storage_type = config.get("type", "qdrant")
        
        if storage_type == "qdrant":
            return QdrantVectorRepository(
                collection_name=config.get("collection_name", "default_collection"),
                embedding_dim=config.get("embedding_dim", 384),
                url=config.get("url", os.getenv("QDRANT_URL")),
                port=config.get("port", int(os.getenv("QDRANT_PORT", "6333"))),
                grpc_port=config.get("grpc_port"),
                api_key=config.get("api_key"),
                on_disk=config.get("on_disk", True),
                replication_factor=config.get("replication_factor", 1),
                write_consistency_factor=config.get("write_consistency_factor", 1),
            )
        else:
            raise ValueError(f"Unknown vector storage type: {storage_type}")
