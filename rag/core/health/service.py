"""
Services Health Service - Application layer service for checking external service health.

This service checks the health of external services (Docling, Embedding) used for
document processing. It follows hexagonal architecture by depending on ports (interfaces)
rather than concrete implementations.

Usage:
    from bootstrap.app_container import remote_services_health
    
    service = remote_services_health()
    result = service.check_all()
    
    if result.upload_enabled:
        # Safe to allow document uploads
        pass
"""

import logging
from typing import Optional

from core.connector.domain.document_converter import DocumentConverterPort
from core.vector.domain.embedder import EmbeddingPort
from core.health.domain.model import ServiceHealthStatus, ServicesHealthResult


logger = logging.getLogger(__name__)


class ServicesHealthService:
    """
    Application service for checking health of external document processing services.
    
    This service receives ports (interfaces) via dependency injection and uses their
    test_connection() methods to check availability. It doesn't know about concrete
    adapter implementations (RemoteDoclingAdapter, LocalDoclingAdapter, etc.).
    
    Attributes:
        _docling_port: Port for document conversion (optional, None if local mode)
        _embedding_port: Port for embedding generation (optional, None if local mode)
        _use_remote_docling: Whether remote docling is configured
        _use_remote_embedding: Whether remote embedding is configured
    """
    
    def __init__(
        self,
        docling_port: Optional[DocumentConverterPort],
        embedding_port: Optional[EmbeddingPort],
        use_remote_docling: bool,
        use_remote_embedding: bool,
    ):
        """
        Initialize the health service with dependency-injected ports.
        
        Args:
            docling_port: Document converter port (None if using local mode)
            embedding_port: Embedding port (None if using local mode)
            use_remote_docling: Whether remote docling service is configured
            use_remote_embedding: Whether remote embedding service is configured
        """
        self._docling_port = docling_port
        self._embedding_port = embedding_port
        self._use_remote_docling = use_remote_docling
        self._use_remote_embedding = use_remote_embedding
        
        logger.info(
            f"ServicesHealthService initialized: "
            f"docling={'remote' if use_remote_docling else 'local'}, "
            f"embedding={'remote' if use_remote_embedding else 'local'}"
        )
    
    def check_docling_health(self) -> ServiceHealthStatus:
        """
        Check health of the Docling service.
        
        Returns:
            ServiceHealthStatus with status 'local' if using local mode,
            'healthy' if remote service is available, 'unhealthy' otherwise.
        """
        if not self._use_remote_docling:
            return ServiceHealthStatus(
                service_name="docling",
                status="local",
                mode="local",
                message="Using local docling library",
            )
        
        try:
            if self._docling_port is None:
                return ServiceHealthStatus(
                    service_name="docling",
                    status="unhealthy",
                    mode="remote",
                    message="Docling port not configured",
                )
            
            is_healthy = self._docling_port.test_connection()
            return ServiceHealthStatus(
                service_name="docling",
                status="healthy" if is_healthy else "unhealthy",
                mode="remote",
                message="Service is available" if is_healthy else "Service is unavailable",
            )
        except Exception as e:
            logger.error(f"Error checking docling health: {e}")
            return ServiceHealthStatus(
                service_name="docling",
                status="unhealthy",
                mode="remote",
                message=str(e),
            )
    
    def check_embedding_health(self) -> ServiceHealthStatus:
        """
        Check health of the Embedding service.
        
        Returns:
            ServiceHealthStatus with status 'local' if using local mode,
            'healthy' if remote service is available, 'unhealthy' otherwise.
        """
        if not self._use_remote_embedding:
            return ServiceHealthStatus(
                service_name="embedding",
                status="local",
                mode="local",
                message="Using local embedding model",
            )
        
        try:
            if self._embedding_port is None:
                return ServiceHealthStatus(
                    service_name="embedding",
                    status="unhealthy",
                    mode="remote",
                    message="Embedding port not configured",
                )
            
            is_healthy = self._embedding_port.test_connection()
            return ServiceHealthStatus(
                service_name="embedding",
                status="healthy" if is_healthy else "unhealthy",
                mode="remote",
                message="Service is available" if is_healthy else "Service is unavailable",
            )
        except Exception as e:
            logger.error(f"Error checking embedding health: {e}")
            return ServiceHealthStatus(
                service_name="embedding",
                status="unhealthy",
                mode="remote",
                message=str(e),
            )
    
    def check_all(self) -> ServicesHealthResult:
        """
        Check health of all external services.
        
        Returns:
            ServicesHealthResult with status for each service and upload_enabled flag.
        """
        docling_status = self.check_docling_health()
        embedding_status = self.check_embedding_health()
        
        result = ServicesHealthResult(
            docling=docling_status,
            embedding=embedding_status,
        )
        
        logger.debug(
            f"Health check result: docling={docling_status.status}, "
            f"embedding={embedding_status.status}, upload_enabled={result.upload_enabled}"
        )
        
        return result
