"""Factory classes for creating adapter instances."""

import os
import torch
from typing import Dict, Any, Optional

from config.app_config import AppConfig
from infrastructure.embedding.sentence_transformer_embedder import SentenceTransformerEmbedding
from infrastructure.qdrant.qdrant_vector_repository import QdrantVectorRepository
from infrastructure.connector.document_connector import DocumentConnector
from infrastructure.config.doc_config_manager import DocConfigManager
from core.vector.domain.embedder import EmbeddingGenerator
from core.vector.domain.repository import VectorRepository
from domain.connector.data_connector import DataConnector

device = "cuda" if torch.cuda.is_available() else "cpu"
app_config = AppConfig.get_instance()


class EmbeddingGeneratorFactory:
    """Factory for creating embedding generator instances based on configuration."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> EmbeddingGenerator:
        """
        Create an embedding generator instance.
        
        Args:
            config: Configuration for the embedding generator
                - type: Generator type ("local" or "remote")
                - model_name: Model name for embedding generation
                - batch_size: Number of items to process in a batch
                - device: Device to use (for local mode)
                - service_url: URL of remote service (for remote mode)
                - timeout: Request timeout in seconds (for remote mode)
                - embedding_dim: Dimension of embeddings (for remote mode)
            
        Returns:
            Initialized embedding generator
        """
        generator_type = config.get("type", "local")
        
        if generator_type == "local":
            # Local mode: use SentenceTransformer model directly
            return SentenceTransformerEmbedding(
                model_name=config.get("model_name", "all-MiniLM-L6-v2"),
                batch_size=config.get("batch_size", 32),
                device=config.get("device", device)
            )
        elif generator_type == "remote":
            # Remote mode: create client and inject into embedder
            from global_utils.clients import EmbeddingServiceClient
            
            client = EmbeddingServiceClient(
                base_url=config.get("service_url"),
                timeout=config.get("timeout"),
                model_name=config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
            )
            return SentenceTransformerEmbedding(
                service_client=client,
                batch_size=config.get("batch_size", 32),
                embedding_dim=config.get("embedding_dim", 384),
            )
        else:
            raise ValueError(f"Unknown embedding generator type: {generator_type}")


class DocumentConnectorFactory:
    """Factory for creating document connector instances based on configuration."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> DataConnector:
        """
        Create a document connector instance.
        
        Args:
            config: Configuration for the document connector
                - type: Connector type ("local" or "remote")
                - config_manager: Optional DocConfigManager instance
                - service_url: URL of remote service (for remote mode)
                - timeout: Request timeout in seconds (for remote mode)
            
        Returns:
            Initialized document connector
        """
        connector_type = config.get("type", "local")
        config_manager = config.get("config_manager") or DocConfigManager()
        
        if connector_type == "local":
            # Local mode: use docling library directly
            return DocumentConnector(config_manager=config_manager)
        elif connector_type == "remote":
            # Remote mode: create client and inject into connector
            from global_utils.clients import DoclingServiceClient
            
            client = DoclingServiceClient(
                base_url=config.get("service_url"),
                timeout=config.get("timeout"),
                image_export_mode="placeholder",
                pdf_backend="pypdfium2",
            )
            return DocumentConnector(
                config_manager=config_manager,
                service_client=client,
            )
        else:
            raise ValueError(f"Unknown document connector type: {connector_type}")


class VectorRepositoryFactory:
    """Factory for creating vector repository instances based on configuration."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> VectorRepository:
        """
        Create a vector repository instance.
        
        Args:
            config: Configuration for the vector repository
                - type: Storage type ("qdrant")
                - collection_name: Name of the collection
                - embedding_dim: Dimension of embeddings
                - url: Server URL (optional, uses AppConfig.qdrant_ip)
                - port: Server port (optional, uses AppConfig.qdrant_port)
                - grpc_port: gRPC port (optional)
                - api_key: API key (optional, uses env var QDRANT_API_KEY)
                - on_disk: Store on disk vs memory (default: True)
                
        Returns:
            Initialized vector repository
        """
        storage_type = config.get("type", "qdrant")
        
        if storage_type == "qdrant":
            return QdrantVectorRepository(
                collection_name=config.get("collection_name", "default_collection"),
                embedding_dim=config.get("embedding_dim", 384),
                url=app_config.qdrant_ip or config.get("url"),
                port=int(app_config.qdrant_port) or config.get("port"),
                grpc_port=config.get("grpc_port"),
                api_key=config.get("api_key"),
                on_disk=config.get("on_disk", True),
                replication_factor=config.get("replication_factor", 1),
                write_consistency_factor=config.get("write_consistency_factor", 1),
            )
        else:
            raise ValueError(f"Unknown vector storage type: {storage_type}")

