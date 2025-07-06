import base64
import os
import time
from config.app_config import AppConfig
from utils.storage.mongo.mongo_storage import MongoStorage
from global_utils.utils.util import get_mongo_url
from utils.storage.storage_manager import StorageManager
from utils.monitor.pipeline_monitor import MongoDBPipelineRepository
import pymongo
import uuid
from flask import session, jsonify
from data_sources.docs.doc_connector import DocumentConnector
from data_sources.docs.doc_config_manager import DocConfigManager
from data_sources.docs.document_processor import DocumentProcessor
from data_sources.docs.pdf_chunker_strategy import DoclingProcessingError, PDFChunkerStrategy
from data_sources.docs.doc_pipeline_scheduler import DocDataPipeline
from utils.embedding.embedding_generator_factory import EmbeddingGeneratorFactory
from utils.storage.vector_storage_factory import VectorStorageFactory
from shared.logger import logger
from global_utils.utils.util import get_mongo_url
from utils.storage.mongo.mongo_helpers import get_mongo_storage
from werkzeug.utils import secure_filename

app_config = AppConfig()
upload_folder = app_config.get("upload_folder", "")

mongo_client = pymongo.MongoClient(get_mongo_url())
pipeline_repo = MongoDBPipelineRepository(mongo_client)
data_source_repo = MongoStorage(get_mongo_url())

def upload_docs(files):
    try:
        for file in files:
            filename = secure_filename(file["name"])
            content = base64.b64decode(file["content"])
            with open(os.path.join(upload_folder, filename), "wb") as f:
                f.write(content)
    except Exception as e:
        logger.error(f"Failed to upload files: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_available_doc_list(user, scope="private"):
    """
    Fetches a list of available documents uploaded by a specific user.
    Enriches each document with additional metadata from the data source.
    
    Args:
        user: The user requesting the documents
        scope: Either "private" (user's documents only) or "public" (all public documents)
    """
    if scope == "private":
        # Get only documents uploaded by the user
        docs = pipeline_repo.get_pipeline_by_query({"source_type": "DOCUMENT","upload_by": user, "deleted": {"$ne": True}})
    elif scope == "public":
        # Get all public documents
        docs = pipeline_repo.get_pipeline_by_query({"source_type": "DOCUMENT", "deleted": {"$ne": True}})
    else:
        # Default to private scope
        docs = pipeline_repo.get_pipeline_by_query({"source_type": "DOCUMENT","upload_by": user, "deleted": {"$ne": True}})
    
    if not docs:
        return []

    filtered_docs = []
    for doc in docs:
        doc["file_type"] = doc.get("name", "").rsplit(".", 1)[-1].lower()
        
        pipeline_id = doc.get("pipeline_id")
        doc_data = data_source_repo.get_source_by_query({"last_pipeline_id": pipeline_id})
        if not doc_data:
            continue

        # Get privacy information from the data source
        privacy = doc_data[0].get("scope", "private")
        
        # Filter based on scope and privacy
        if scope == "public" and privacy != "public":
            continue
        elif scope == "private" and doc.get("upload_by") != user:
            continue
        
        type_data = doc_data[0].get("type_data", {})
        doc.update({
            "chunks": doc_data[0].get("chunks_generated", []),
            "path": type_data.get("source_path", ""),
            "file_size": type_data.get("file_size", 0),
            "page_count": type_data.get("page_count", 0),
            "full_text": type_data.get("full_text", ""),
            "scope": scope
        })
        
        filtered_docs.append(doc)

    return filtered_docs

def embed_docs_flow(doc_list, upload_by, scope="private"):
    # Create data pipeline with existing logger
    doc_pipeline = DocDataPipeline(mongo_client, logger=logger)
    
    # Insert the documents queue into the pipeline db
    for doc in doc_list:
        doc_name = doc.get("doc_name", "")
        doc_path = os.path.join(upload_folder, doc_name)
        doc_id = str(uuid.uuid4())
        doc["doc_id"] = doc_id
        doc["doc_path"] = doc_path
        doc["scope"] = scope
        
        start = time.time()
        doc_pipeline.register_doc(doc_id, doc_name, upload_by)
        
    config = DocConfigManager()
    config.set_config_value("chunk_size", 800)
    config.set_config_value("chunk_overlap", 100)

    doc_connector = DocumentConnector(config)
    doc_processor = DocumentProcessor()

    # Create PDF chunker
    pdf_chunker = PDFChunkerStrategy(
        max_tokens_per_chunk=config._config["chunk_size"],
        overlap_tokens=config._config["chunk_overlap"]
    )

    # Create embedding generator
    embedding_config = {
        "type": "sentence_transformer",
        "model_name": "all-MiniLM-L6-v2",
        "batch_size": 32
    }
    
    embedding_generator = EmbeddingGeneratorFactory.create(embedding_config)

    # Create vector storage, mongo storage and manager
    storage_config = {
        "type": "qdrant",
        "collection_name": "pdf_doc_data",
        "embedding_dim": embedding_generator.embedding_dim,
    }
    vector_storage = VectorStorageFactory.create(storage_config)
    vector_storage.initialize()
    mongo_storage = get_mongo_storage()
    manager = StorageManager(vector_storage, mongo_storage)
    
    response = []
    for doc in doc_list:
        try:
            doc_id = doc["doc_id"]
            doc_path = doc["doc_path"]
            doc_name = doc["doc_name"]
            doc_scope = doc.get("scope", "private")
            doc_pipeline.process_doc(doc_id)
 
            # Start log monitoring - this will uses the event-driven handler system
            doc_pipeline.monitor.start_log_monitoring(target_logger=logger, pipeline_id=f"doc_{doc_id}")

            result = doc_connector.process_document(doc_path, upload_by)
            # Process with various options
            processed_documents = doc_processor.process(
                result,
                clean_markdown=False, # Clean markdown content
                clean_text=False,     # Leave text content as is for now
                remove_references=False,  # Don't remove references yet
                preserve_original=True  # Keep original content
            )
            
            # Add scope information to the processed document metadata
            if processed_documents.get("metadata"):
                processed_documents["metadata"]["scope"] = doc_scope
            else:
                processed_documents["metadata"] = {"scope": doc_scope}
            
            embedding_ready_docs = doc_processor.prepare_for_single_doc_embedding(processed_documents)
            
            chunks = pdf_chunker.chunk_content([embedding_ready_docs])
            enriched_chunks = embedding_generator.generate_embeddings(chunks)
            common_summary = {
                "chunks_generated":   len(chunks),
                "embeddings_created": len(enriched_chunks),
                "processing_time_s":  time.time() - start,
                "last_pipeline_id":   f"doc_{doc_id}"
            }

            doc_type_data = {
                "doc_path": doc_path,
                "page_count": result.get("metadata", {}).get("page_count", 0),
                "full_text": result.get("text", ""),
                "file_size": result.get("metadata", {}).get("file_size", 0),
            }

            manager.persist(
                source_id=doc_id,
                source_name=doc_name,
                upload_by=upload_by,
                source_type="DOCUMENT",
                enriched_chunks=enriched_chunks,
                summary=common_summary,
                type_data=doc_type_data,
                scope=doc.get("scope", "private")
            )
            
            vector_storage.store_embeddings(enriched_chunks)

            response.append({
                "doc": doc_name,
                "status": "success",
                "chunks_stored": len(enriched_chunks)
            })

            doc_pipeline.monitor.finish_log_monitoring()
            
        except Exception as e:
            logger.error(f"Failed to embed doc {doc.get('doc_name')}: {str(e)}")
            response.append({
                "doc": doc.get("doc_name"),
                "status": "failed",
                "error": str(e)
            })

    return response

def get_best_match_results(query: str, top_k_results: int = 5, scope: str = "public", logged_in_user: str = "default"):
    # Create embedding generator
    embedding_config = {
        "type": "sentence_transformer",
        "model_name": "all-MiniLM-L6-v2",
        "batch_size": 32
    }
    embedding_generator = EmbeddingGeneratorFactory.create(embedding_config)
    
    # Create vector storage
    storage_config = {
        "type": "qdrant",
        "collection_name": "pdf_doc_data",
        "embedding_dim": embedding_generator.embedding_dim,
    }
    vector_storage = VectorStorageFactory.create(storage_config)
    vector_storage.initialize()
    
    query_embedding = embedding_generator.generate_query_embedding(query)
    
    # Set up filters based on scope
    # Private scope: only documents uploaded by the user
    # Public scope: all public documents + user's own documents (regardless of scope)
    filters = {"upload_by": logged_in_user} if scope == "private" else \
        {"or": [{"scope": "public"}, {"upload_by": logged_in_user}]}
    
    search_results = vector_storage.search(
        query_embedding=query_embedding,
        top_k=top_k_results,
        filters=filters
    )

    return search_results

def delete_document(pipeline_id: str):
    """
    Delete a document pipeline by its ID.
    
    Args:
        pipeline_id: The ID of the pipeline to delete.
        
    Returns:
        True if deletion was successful, False otherwise.
    """    
    source = data_source_repo.delete_source(pipeline_id)
    pipeline = pipeline_repo.delete_pipeline(pipeline_id)
    # add here removal from qdrant!!! not implemented yet
    return source and pipeline
