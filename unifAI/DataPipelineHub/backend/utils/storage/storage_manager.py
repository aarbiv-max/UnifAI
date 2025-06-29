# storage_manager.py

from typing import List, Dict, Any, Optional
from .qdrant_storage import QdrantStorage
from utils.storage.mongo.mongo_storage import MongoStorage 

class StorageManager:
    def __init__(self, qstore: QdrantStorage, mstore: MongoStorage):
        self.qstore = qstore
        self.mstore = mstore

    def persist(
        self,
        source_id: str,
        source_name: str,
        source_type: str,
        enriched_chunks: List[Dict[str, Any]],
        summary: Dict[str, Any],
        type_data: Optional[Dict[str, Any]] = None
    ):
        # write embeddings
        self.qstore.store_embeddings(enriched_chunks)

        self.mstore.upsert_source_summary(
            source_id=source_id,
            source_name=source_name,
            source_type=source_type,
            summary=summary,
            type_data=type_data
        )
