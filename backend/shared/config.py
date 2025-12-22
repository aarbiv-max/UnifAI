from dataclasses import dataclass

@dataclass(frozen=True)
class ChunkerConfig:
    max_tokens_per_chunk: int = 500
    overlap_tokens: int       = 50
    time_window_seconds: int  = 300
    chunk_size: int           = 800
    chunk_overlap: int        = 100

@dataclass(frozen=True)
class EmbeddingConfig:
    """Configuration for remote embedding service."""
    model_name: str  = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int  = 32
    service_url: str = ""  # Optional: overrides AppConfig.embedding_service_url
    timeout: int     = 0   # Optional: overrides AppConfig.embedding_service_timeout (0 = use default)
    embedding_dim: int = 384  # Dimension for remote service (default for all-MiniLM-L6-v2)

@dataclass(frozen=True)
class StorageConfig:
    type: str            = "qdrant"
    collection_name: str = "data_source" 