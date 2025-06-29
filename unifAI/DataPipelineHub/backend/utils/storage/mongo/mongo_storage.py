from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from flask import Flask, jsonify, current_app
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection

# ─── Constants ────────────────────────────────────────────────────────────
DATA_DB      = "data_sources"
SOURCES_COL  = "sources"
CHUNKS_COL   = "chunks"
PIPELINE_DB  = "pipeline_monitoring"
PIPELINE_COL = "pipelines"

# ─── JSON Safety Helper ─────────────────────────────────────────────────────
def _make_json_safe(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert ObjectIds and datetimes into strings for JSON-serialization."""
    safe: Dict[str, Any] = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            safe[k] = str(v)
        elif isinstance(v, datetime):
            safe[k] = v.isoformat()
        elif isinstance(v, dict):
            safe[k] = _make_json_safe(v)
        elif isinstance(v, list):
            safe[k] = [
                str(i) if isinstance(i, ObjectId)
                else _make_json_safe(i) if isinstance(i, dict)
                else i
                for i in v
            ]
        else:
            safe[k] = v
    return safe

# ─── Repository Interfaces ─────────────────────────────────────────────────
class SourceRepository(ABC):
    @abstractmethod
    def get_all(self, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all source summaries, optionally filtered by type."""
        ...

class PipelineRepository(ABC):
    @abstractmethod
    def get_status_map(self, pipeline_ids: List[str]) -> Dict[str, str]:
        """Given a list of pipeline_ids, return a map {pipeline_id -> status}."""
        ...

# ─── MongoStorage (implements both repos + old methods) ─────────────────────
class MongoStorage(SourceRepository, PipelineRepository):
    def __init__(self, mongo_uri: str):
        self.client = MongoClient(mongo_uri)
        self._collection_index_map: Dict[str, List[Dict[str, Any]]] = {
            CHUNKS_COL:   [{'keys': [('source_id', 1), ('chunk_index', 1)], 'unique': True}],
            SOURCES_COL: [{'keys': [('source_id', 1)],              'unique': True}],
            PIPELINE_COL:[{'keys': [('pipeline_id', 1)],            'unique': True}],
        }
        self._indexed_cols: set[Tuple[str, str]] = set()

    def _get_collection(self, db_name: str, col_name: str) -> Collection:
        if col_name not in self._collection_index_map:
            raise ValueError(f"Unknown collection '{col_name}' in {db_name}")
        col = self.client[db_name][col_name]
        key = (db_name, col_name)
        if key not in self._indexed_cols:
            for idx in self._collection_index_map[col_name]:
                col.create_index(idx['keys'], unique=idx.get('unique', False))
            self._indexed_cols.add(key)
        return col

    # — Existing methods —
    def upsert_chunks(
        self,
        db_name: str,
        source_id: str,
        chunks: List[Dict[str, Any]]
    ) -> None:
        col = self._get_collection(db_name, CHUNKS_COL)
        ops = []
        for idx, chunk in enumerate(chunks):
            doc_id = f"{source_id}_{idx}"
            doc = {
                '_id':       doc_id,
                'source_id': source_id,
                'text':      chunk['text'],
                **chunk.get('metadata', {})
            }
            ops.append(UpdateOne({'_id': doc_id}, {'$set': doc}, upsert=True))
        if ops:
            col.bulk_write(ops)

    def upsert_source_summary(
        self,
        source_id: str,
        source_name: str,
        source_type: str,
        summary: Dict[str, Any],
        type_data: Optional[Dict[str, Any]] = None
    ) -> None:
        col = self._get_collection(DATA_DB, SOURCES_COL)
        now = datetime.utcnow()
        doc: Dict[str, Any] = {
            'source_id':   source_id,
            'source_name': source_name,
            'source_type': source_type,
            'last_sync_at': now,
            **summary
        }
        if type_data is not None:
            doc['type_data'] = type_data
        col.update_one(
            {'source_id': source_id},
            {'$set': doc, '$setOnInsert': {'created_at': now}},
            upsert=True
        )

    def get_all_sources(
        self,
        source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        col = self._get_collection(DATA_DB, SOURCES_COL)
        query: Dict[str, Any] = {}
        if source_type:
            query['source_type'] = source_type.upper()
        return list(col.find(query))

    def upsert_documents(
        self,
        db_name: str,
        col_name: str,
        docs: List[Dict[str, Any]],
        key_field: str
    ) -> None:
        col = self._get_collection(db_name, col_name)
        ops = []
        for doc in docs:
            if key_field not in doc:
                raise ValueError(f"Missing key field '{key_field}' in {doc}")
            ops.append(
                UpdateOne({key_field: doc[key_field]}, {'$set': doc}, upsert=True)
            )
        if ops:
            col.bulk_write(ops)

    def find_documents(
        self,
        db_name: str,
        col_name: str,
        filter_query: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        col = self._get_collection(db_name, col_name)
        return list(col.find(filter_query or {}))

    # — Implement repository interface —
    def get_all(self, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.get_all_sources(source_type)

    def get_status_map(self, pipeline_ids: List[str]) -> Dict[str, str]:
        if not pipeline_ids:
            return {}
        col = self._get_collection(PIPELINE_DB, PIPELINE_COL)
        cursor = col.find(
            {'pipeline_id': {'$in': pipeline_ids}},
            {'pipeline_id': 1, 'status': 1}
        )
        return {d['pipeline_id']: d.get('status', '') for d in cursor}

# ─── Service Layer ──────────────────────────────────────────────────────────
class SourceService:
    def __init__(
        self,
        src_repo: SourceRepository,
        pl_repo: PipelineRepository
    ):
        self._src = src_repo
        self._pl  = pl_repo

    def list_sources_with_status(
        self,
        source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        raw = self._src.get_all(source_type)
        ids = [s.get('last_pipeline_id') for s in raw if s.get('last_pipeline_id')]
        status_map = self._pl.get_status_map(ids)

        enriched: List[Dict[str, Any]] = []
        for s in raw:
            s['status'] = status_map.get(s.get('last_pipeline_id'))
            enriched.append(_make_json_safe(s))
        return enriched
