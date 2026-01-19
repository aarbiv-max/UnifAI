"""Outbound HTTP service clients for external microservices."""
from infrastructure.clients.docling_service_client import DoclingServiceClient
from infrastructure.clients.embedding_service_client import EmbeddingServiceClient

__all__ = [
    "DoclingServiceClient",
    "EmbeddingServiceClient",
]
