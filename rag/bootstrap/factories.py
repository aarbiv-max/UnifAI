"""Factory classes for creating adapter instances."""

import logging
from typing import Dict, Any

import torch

from config.app_config import AppConfig
from core.vector.domain.embedder import EmbeddingGenerator
from core.vector.domain.repository import VectorRepository
from core.connector.domain.base import DataConnector
from core.connector.domain.document_converter import DocumentConverterPort

logger = logging.getLogger(__name__)

device = "cuda" if torch.cuda.is_available() else "cpu"
app_config = AppConfig.get_instance()


class DocumentConverterFactory:
    """Factory for creating document converter port instances."""
    
    @staticmethod
    def create_local() -> DocumentConverterPort:
        """Create a local docling adapter."""
        from infrastructure.sources.document.adapters import LocalDoclingAdapter
        return LocalDoclingAdapter()
    
    @staticmethod
    def create_remote(
        base_url: str,
        timeout: int = 300,
        image_export_mode: str = "placeholder",
        pdf_backend: str = "pypdfium2",
    ) -> DocumentConverterPort:
        """Create a remote docling adapter."""
        from global_utils.docling import DoclingClient, DoclingService
        from infrastructure.sources.document.adapters import RemoteDoclingAdapter
        
        client = DoclingClient(base_url=base_url, timeout=timeout)
        service = DoclingService(
            client=client,
            image_export_mode=image_export_mode,
            pdf_backend=pdf_backend,
        )
        return RemoteDoclingAdapter(docling_service=service)


class DocumentConnectorFactory:
    """Factory for creating document connector instances."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> DataConnector:
        """
        Create a document connector instance.
        
        Args:
            config: Configuration dict with keys:
                - type: "local" or "remote"
                - service_url: URL (for remote)
                - timeout: Timeout in seconds (for remote)
                - config_manager: Optional DocConfigManager
        """
        from infrastructure.sources.document.connector import DocumentConnector
        from infrastructure.sources.document.config import DocConfigManager
        
        connector_type = config.get("type", "local")
        config_manager = config.get("config_manager") or DocConfigManager()
        
        if connector_type == "local":
            converter = DocumentConverterFactory.create_local()
        elif connector_type == "remote":
            converter = DocumentConverterFactory.create_remote(
                base_url=config.get("service_url"),
                timeout=config.get("timeout", 300),
            )
        else:
            raise ValueError(f"Unknown connector type: {connector_type}")
        
        return DocumentConnector(
            converter=converter,
            config_manager=config_manager,
        )


class EmbeddingPortFactory:
    """Factory for creating embedding port instances."""
    
    @staticmethod
    def create_local(
        model_name: str = "all-MiniLM-L6-v2",
        device_name: str = None,
    ):
        """Create a local embedding adapter."""
        from infrastructure.embedding.adapters import LocalEmbeddingAdapter
        return LocalEmbeddingAdapter(
            model_name=model_name,
            device=device_name or device,
        )
    
    @staticmethod
    def create_remote(
        base_url: str,
        timeout: int = 60,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim: int = 384,
    ):
        """Create a remote embedding adapter."""
        from global_utils.embedding import EmbeddingClient, EmbeddingService
        from infrastructure.embedding.adapters import RemoteEmbeddingAdapter
        
        client = EmbeddingClient(base_url=base_url, timeout=timeout)
        service = EmbeddingService(client=client, model_name=model_name)
        return RemoteEmbeddingAdapter(
            embedding_service=service,
            embedding_dim=embedding_dim,
        )


class EmbeddingGeneratorFactory:
    """Factory for creating embedding generator instances."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> EmbeddingGenerator:
        """
        Create an embedding generator instance.
        
        Args:
            config: Configuration dict with keys:
                - type: "local" or "remote"
                - model_name: Model name
                - batch_size: Batch size
                - device: Device (for local)
                - service_url: URL (for remote)
                - timeout: Timeout (for remote)
                - embedding_dim: Dimension (for remote)
        """
        from infrastructure.embedding.embedding_generator import DefaultEmbeddingGenerator
        
        generator_type = config.get("type", "local")
        batch_size = config.get("batch_size", 32)
        
        if generator_type == "local":
            port = EmbeddingPortFactory.create_local(
                model_name=config.get("model_name", "all-MiniLM-L6-v2"),
                device_name=config.get("device"),
            )
        elif generator_type == "remote":
            port = EmbeddingPortFactory.create_remote(
                base_url=config.get("service_url"),
                timeout=config.get("timeout", 60),
                model_name=config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
                embedding_dim=config.get("embedding_dim", 384),
            )
        else:
            raise ValueError(f"Unknown generator type: {generator_type}")
        
        return DefaultEmbeddingGenerator(port=port, batch_size=batch_size)


class VectorRepositoryFactory:
    """Factory for creating vector repository instances."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> VectorRepository:
        """Create a vector repository instance."""
        from infrastructure.qdrant.qdrant_vector_repository import QdrantVectorRepository
        
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
            raise ValueError(f"Unknown storage type: {storage_type}")
