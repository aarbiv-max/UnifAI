import time
import pymongo
from data_sources.slack.slack_config_manager import SlackConfigManager
from data_sources.slack.slack_connector import SlackConnector
from data_sources.slack.slack_data_processor import SlackProcessor
from data_sources.slack.slack_chunker_strategy import SlackChunkerStrategy
from data_sources.slack.slack_pipeline_scheduler import SlackDataPipeline
from utils.storage.mongo.mongo_helpers import get_mongo_storage
from utils.storage.storage_manager import StorageManager
from utils.embedding.embedding_generator_factory import EmbeddingGeneratorFactory
from utils.storage.vector_storage_factory import VectorStorageFactory
from shared.logger import logger
 
def _get_configured_connector() -> SlackConnector:
    config_manager = SlackConfigManager()
    config_manager.set_project_tokens(
        project_id="example-project",
        bot_token="xoxb-2253118358-8783454711008-dwnxf7cPBpeVLlLw8KMurohb",
        user_token="xoxb-2253118358-8783454711008-dwnxf7cPBpeVLlLw8KMurohb"
    )
    config_manager.set_default_project("example-project")
    return SlackConnector(config_manager)

def get_available_slack_channels(channel_types: str):
    connector = _get_configured_connector()
    if connector.authenticate():
        return connector.get_available_slack_channels(types=channel_types)
    else:
        raise RuntimeError("Slack authentication failed")

def embed_slack_channels_flow(channel_list):
    connector = _get_configured_connector()
    if not connector.authenticate():
        raise RuntimeError("Slack authentication failed")
    
    mongo_client   = pymongo.MongoClient("mongodb://ae8f0dd8e6cd046539c3f0b7c6a75f13-508991814.us-east-1.elb.amazonaws.com:27017")
    slack_pipeline = SlackDataPipeline(mongo_client, logger=logger)
    
    processor = SlackProcessor()
    chunker = SlackChunkerStrategy(max_tokens_per_chunk=500, overlap_tokens=50, time_window_seconds=300)
    
    embedding_config = {
        "type": "sentence_transformer",
        "model_name": "all-MiniLM-L6-v2",
        "batch_size": 32
    }
    embedding_generator = EmbeddingGeneratorFactory.create(embedding_config)
    
    # QdrantStorage via factory
    storage_config = {
        "type": "qdrant",
        "collection_name": "slack_data",
        "embedding_dim": embedding_generator.embedding_dim,
        "url": "http://a467739e076d04bf1b15aa68187cbc05-1112405490.us-east-1.elb.amazonaws.com",
        "port": 6333
    }
    qstore = VectorStorageFactory.create(storage_config)
    qstore.initialize()
    mongo_storage= get_mongo_storage()
    
    # Cast to QdrantStorage since we know it's a Qdrant instance
    from utils.storage.qdrant_storage import QdrantStorage
    qdrant_store = qstore if isinstance(qstore, QdrantStorage) else None
    if not qdrant_store:
        raise RuntimeError("Expected QdrantStorage instance")
    
    # Wrap Qdrant + MongoStorage in a manager
    manager = StorageManager(qdrant_store, mongo_storage)

    response = []
    for channel in channel_list:
        cid  = channel["channel_id"]
        cname= channel["channel_name"]

        # 1️⃣ Register & start monitoring
        pipeline_id = slack_pipeline.process_slack_channel(cid, cname)
        slack_pipeline.monitor.start_log_monitoring(target_logger=logger, pipeline_id=f"slack_{cid}")

        # 2️⃣ Register channel in source data collection IMMEDIATELY
        try:
            initial_summary = {
                "chunks_generated": 0,
                "embeddings_created": 0,
                "processing_time_s": 0,
                "last_pipeline_id": pipeline_id,
            }

            slack_type_data = {
                "message_count": 0,
                "api_calls": 0,
                "is_private": channel["is_private"]
            }

            # Register the source immediately with initial data
            mongo_storage.upsert_source_summary(
                source_id=cid,
                source_name=cname,
                source_type="SLACK",
                summary=initial_summary,
                type_data=slack_type_data
            )

            # 3️⃣ Fetch messages first
            messages, thread_msgs = connector.get_conversations_history(cid)
            
            # Update source with message count immediately after fetching
            fetched_summary = {
                "chunks_generated": 0,
                "embeddings_created": 0,
                "processing_time_s": 0,
                "last_pipeline_id": pipeline_id,
            }

            fetched_slack_type_data = {
                "message_count": len(messages),
                "api_calls": 0,
                "is_private": channel["is_private"]
            }

            # Update source with message count
            mongo_storage.upsert_source_summary(
                source_id=cid,
                source_name=cname,
                source_type="SLACK",
                summary=fetched_summary,
                type_data=fetched_slack_type_data
            )
            
            # 4️⃣ Process, chunk, embed
            processed_main  = processor.process(messages,  channel_name=cname)
            processed_threads = [processor.process(t, channel_name=cname) for t in thread_msgs]

            all_chunks   = chunker.chunk_content(processed_main) + \
                           [chunk for t in processed_threads for chunk in t]
            
            # Add source_id to all chunks for Qdrant filtering/deletion
            for chunk in all_chunks:
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["metadata"]["source_id"] = cid
                chunk["metadata"]["source_type"] = "SLACK"
                # Ensure chunk_index for easier identification
                if "chunk_index" not in chunk["metadata"]:
                    chunk["metadata"]["chunk_index"] = len([c for c in all_chunks if c is chunk])
            
            embeddings   = embedding_generator.generate_embeddings(all_chunks)

            # 5️⃣ Build summary
            if hasattr(slack_pipeline.slack_monitor, "get_api_calls"):
                slack_api_calls = slack_pipeline.slack_monitor.get_api_calls(pipeline_id)
            else:
                slack_api_calls = 0
            start = time.time()

            # 6️⃣ Store embeddings in Qdrant
            enriched = embedding_generator.generate_embeddings(all_chunks)
            qstore.store_embeddings(enriched)

            # 7️⃣ Update source summary with final data
            final_summary = {
                "chunks_generated":   len(all_chunks),
                "embeddings_created": len(enriched),
                "processing_time_s":  time.time() - start,
                "last_pipeline_id":   pipeline_id,
            }

            final_slack_type_data = {
                "message_count": len(messages),
                "api_calls":     slack_api_calls,
                "is_private":    channel["is_private"]
            }

            # Update the source with final processing results
            mongo_storage.upsert_source_summary(
                source_id=cid,
                source_name=cname,
                source_type="SLACK",
                summary=final_summary,
                type_data=final_slack_type_data
            )

            # 8️⃣ Mark success in monitor
            slack_pipeline.monitor.finish_log_monitoring()

            response.append({
              "channel":     cname,
              "status":      "success",
              "chunks_stored": len(all_chunks)
            })

        except Exception as e:
            # 9️⃣ On error, record it and update source status
            logger.error(f"Error embedding {cname}: {e}")
            if pipeline_id:
                slack_pipeline.monitor.record_error(pipeline_id, str(e))
            
            # Update source status to failed
            error_summary = {
                "chunks_generated": 0,
                "embeddings_created": 0,
                "processing_time_s": 0,
                "last_pipeline_id": pipeline_id,
                "status": "failed",
                "error": str(e)
            }

            error_slack_type_data = {
                "message_count": 0,
                "api_calls": 0,
                "is_private": channel["is_private"]
            }

            mongo_storage.upsert_source_summary(
                source_id=cid,
                source_name=cname,
                source_type="SLACK",
                summary=error_summary,
                type_data=error_slack_type_data
            )
            
            response.append({
              "channel":     cname,
              "status":      "failed",
              "error":       str(e)
            })

    return response

# def embed_slack_channels_flow(channel_list):
#     connector = _get_configured_connector()
#     if not connector.authenticate():
#         raise RuntimeError("Slack authentication failed")

#     processor = SlackProcessor()
#     chunker = SlackChunkerStrategy(max_tokens_per_chunk=500, overlap_tokens=50, time_window_seconds=300)

#     embedding_config = {
#         "type": "sentence_transformer",
#         "model_name": "all-MiniLM-L6-v2",
#         "batch_size": 32
#     }
#     embedding_generator = EmbeddingGeneratorFactory.create(embedding_config)

#     storage_config = {
#         "type": "qdrant",
#         "collection_name": "slack_data",
#         "embedding_dim": embedding_generator.embedding_dim,
#         "url": "http://a467739e076d04bf1b15aa68187cbc05-1112405490.us-east-1.elb.amazonaws.com",
#         "port": 6333
#     }
#     vector_storage = VectorStorageFactory.create(storage_config)
#     vector_storage.initialize()

#     # Create MongoDB client
#     mongo_client = pymongo.MongoClient("mongodb://ae8f0dd8e6cd046539c3f0b7c6a75f13-508991814.us-east-1.elb.amazonaws.com:27017")

#     # Create data pipeline with existing logger
#     slack_pipeline = SlackDataPipeline(mongo_client, logger=logger)

#     response = []
#     for channel in channel_list:
#         try:
#             channel_id = channel["channel_id"]
#             channel_name = channel["channel_name"]

#             # Process the slack channel using our pipeline
#             slack_pipeline.process_slack_channel(channel_id, channel_name)

#             # Start log monitoring - this will uses the event-driven handler system
#             slack_pipeline.monitor.start_log_monitoring(target_logger=logger, pipeline_id=f"slack_{channel_id}")

#             messages, thread_messages = connector.get_conversations_history(channel_id)
#             processed_messages_data = processor.process(messages, channel_name=channel_name) 
#             processed_thread_data = [
#                 processor.process(thread, channel_name=channel_name)
#                 for thread in thread_messages
#             ]

#             for processed_data in [processed_messages_data, processed_thread_data]:
#                 chunks = chunker.chunk_content(processed_data)
#                 enriched = embedding_generator.generate_embeddings(chunks)
#                 vector_storage.store_embeddings(enriched)

#                 response.append({
#                     "channel": channel_name,
#                     "status": "success",
#                     "chunks_stored": len(enriched)
#                 })
                
#             slack_pipeline.monitor.finish_log_monitoring()
#         except Exception as e:
#             logger.error(f"Failed to embed channel {channel.get('channel_name')}: {str(e)}")
#             response.append({
#                 "channel": channel.get("channel_name"),
#                 "status": "failed",
#                 "error": str(e)
#             })

#     return response

def count_channel_chunks(channel_name: str) -> int:
    storage_config = {
        "type": "qdrant",
        "collection_name": "slack_data",
        "embedding_dim": 384,  # Must match embedding model
        "url": "http://a467739e076d04bf1b15aa68187cbc05-1112405490.us-east-1.elb.amazonaws.com",
        "port": 6333
    }
    vector_storage = VectorStorageFactory.create(storage_config)
    vector_storage.initialize()

    return vector_storage.count(filters={"metadata.channel_name": channel_name})

def get_best_match_results(query: str, top_k_results: int = 5):
    embedding_config = {
        "type": "sentence_transformer",
        "model_name": "all-MiniLM-L6-v2",
        "batch_size": 32
    }
    embedding_generator = EmbeddingGeneratorFactory.create(embedding_config)
    
    # Create vector storage
    storage_config = {
        "type": "qdrant",
        "collection_name": "slack_data",
        "embedding_dim": embedding_generator.embedding_dim,
        "url": "http://a467739e076d04bf1b15aa68187cbc05-1112405490.us-east-1.elb.amazonaws.com",
        "port": 6333
    }
    vector_storage = VectorStorageFactory.create(storage_config)
    vector_storage.initialize()
    
    query_embedding = embedding_generator.generate_query_embedding(query)
    
    search_results = vector_storage.search(
        query_embedding=query_embedding,
        top_k=top_k_results,
    )

    return search_results

def _initialize_storage_components():
    """Initialize and return storage components for deletion operations."""
    embedding_config = {
        "type": "sentence_transformer", 
        "model_name": "all-MiniLM-L6-v2",
        "batch_size": 32
    }
    embedding_generator = EmbeddingGeneratorFactory.create(embedding_config)
    
    storage_config = {
        "type": "qdrant",
        "collection_name": "slack_data", 
        "embedding_dim": embedding_generator.embedding_dim,
        "url": "http://a467739e076d04bf1b15aa68187cbc05-1112405490.us-east-1.elb.amazonaws.com",
        "port": 6333
    }
    qdrant_storage = VectorStorageFactory.create(storage_config)
    qdrant_storage.initialize()
    
    mongo_storage = get_mongo_storage()
    
    return qdrant_storage, mongo_storage

def _get_channel_info(mongo_storage, channel_id: str) -> str:
    """Get channel name from MongoDB before deletion."""
    try:
        channel_info = mongo_storage.find_documents("data_sources", "sources", {"source_id": channel_id})
        return channel_info[0]["source_name"] if channel_info else "Unknown"
    except Exception:
        return "Unknown"

def _delete_from_qdrant(qdrant_storage, channel_id: str) -> int:
    """Delete channel embeddings from Qdrant storage."""
    try:
        # Count embeddings to be deleted (using correct metadata path)
        deleted_count = qdrant_storage.count(filters={"metadata.source_id": channel_id})
        logger.info(f"Found {deleted_count} embeddings to delete for channel {channel_id}")
        
        if deleted_count == 0:
            logger.warning(f"No embeddings found in Qdrant for channel {channel_id} - this may indicate the filter isn't matching")
            return 0
        
        # Delete embeddings (using correct metadata path)
        qdrant_storage.delete(filters={"metadata.source_id": channel_id})
        logger.info(f"Deleted {deleted_count} embeddings from Qdrant for channel {channel_id}")
        
        # Verify deletion by counting again
        remaining_count = qdrant_storage.count(filters={"metadata.source_id": channel_id})
        if remaining_count > 0:
            logger.error(f"Deletion incomplete: {remaining_count} embeddings still remain for channel {channel_id}")
        else:
            logger.info(f"Successfully verified deletion - no embeddings remain for channel {channel_id}")
        
        return deleted_count
    except Exception as e:
        logger.error(f"Error deleting from Qdrant: {e}")
        return 0

def _delete_from_mongodb(channel_id: str) -> tuple[bool, int]:
    """Delete channel data from MongoDB collections."""
    try:
        client = pymongo.MongoClient("mongodb://ae8f0dd8e6cd046539c3f0b7c6a75f13-508991814.us-east-1.elb.amazonaws.com:27017")
        
        # Delete from sources collection
        sources_col = client["data_sources"]["sources"]
        delete_result = sources_col.delete_one({"source_id": channel_id})
        source_deleted = delete_result.deleted_count > 0
        logger.info(f"Deleted {delete_result.deleted_count} document(s) from MongoDB sources for channel {channel_id}")
        
        # Delete from pipeline monitoring collection
        pipeline_col = client["pipeline_monitoring"]["pipelines"]
        pipeline_result = pipeline_col.delete_many({"pipeline_id": {"$regex": f"^slack_{channel_id}"}})
        pipeline_deleted = pipeline_result.deleted_count
        logger.info(f"Deleted {pipeline_deleted} pipeline document(s) from MongoDB for channel {channel_id}")
        
        return source_deleted, pipeline_deleted
    except Exception as e:
        logger.error(f"Error deleting from MongoDB: {e}")
        raise e

def _create_deletion_result(channel_id: str, channel_name: str, qdrant_count: int, mongo_deleted: bool, pipeline_count: int) -> dict:
    """Create standardized deletion result dictionary."""
    return {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "qdrant_embeddings_deleted": qdrant_count,
        "mongo_source_deleted": mongo_deleted,
        "mongo_pipelines_deleted": pipeline_count,
        "success": True
    }

def delete_slack_channel(channel_id: str) -> dict:
    """
    Delete a slack channel from both MongoDB and Qdrant storage.
    
    Args:
        channel_id: The ID of the channel to delete
        
    Returns:
        dict: Result information about the deletion
        
    Raises:
        Exception: If deletion fails
    """
    try:
        # Initialize storage components
        qdrant_storage, mongo_storage = _initialize_storage_components()
        
        # Get channel info before deletion
        channel_name = _get_channel_info(mongo_storage, channel_id)
        
        # Delete from Qdrant
        qdrant_deleted_count = _delete_from_qdrant(qdrant_storage, channel_id)
        
        # Delete from MongoDB
        mongo_deleted, pipeline_deleted_count = _delete_from_mongodb(channel_id)
        
        # Create result
        result = _create_deletion_result(
            channel_id, channel_name, qdrant_deleted_count, 
            mongo_deleted, pipeline_deleted_count
        )
        
        logger.info(f"Successfully deleted channel {channel_name} ({channel_id})")
        return result
        
    except Exception as e:
        logger.error(f"Failed to delete channel {channel_id}: {e}")
        raise e