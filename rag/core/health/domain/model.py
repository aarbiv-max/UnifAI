"""Health check domain models (DTOs)."""

from dataclasses import dataclass, field
from typing import Dict, Literal


# "local" means no remote dependency - always considered ready (no health check needed)
ServiceStatus = Literal["healthy", "unhealthy", "local"]
ServiceMode = Literal["remote", "local"]


@dataclass
class ServiceHealthStatus:
    """Health status for a single service."""
    
    service_name: str
    status: ServiceStatus
    mode: ServiceMode
    message: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "mode": self.mode,
            "message": self.message,
        }


@dataclass
class ServicesHealthResult:
    """Aggregated health status for all services."""
    
    docling: ServiceHealthStatus
    embedding: ServiceHealthStatus
    
    @property
    def upload_enabled(self) -> bool:
        """
        Check if document upload should be enabled.
        
        Upload is enabled only when both services are either healthy or running locally.
        """
        docling_ok = self.docling.status in ("healthy", "local")
        embedding_ok = self.embedding.status in ("healthy", "local")
        return docling_ok and embedding_ok
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "docling": self.docling.to_dict(),
            "embedding": self.embedding.to_dict(),
            "upload_enabled": self.upload_enabled,
        }
