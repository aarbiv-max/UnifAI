import pymongo
from flask import session
from data_sources.slack.slack_config_manager import SlackConfigManager
from data_sources.slack.slack_connector import SlackConnector
from data_sources.slack.slack_data_processor import SlackProcessor
from data_sources.slack.slack_chunker_strategy import SlackChunkerStrategy
from data_sources.slack.slack_pipeline_scheduler import SlackDataPipeline
from utils.embedding.embedding_generator_factory import EmbeddingGeneratorFactory
from utils.storage.vector_storage_factory import VectorStorageFactory
from shared.logger import logger
from global_utils.utils.util import get_mongo_url

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

def embed_slack_channels_flow(channel_list, upload_by):
    connector = _get_configured_connector()
    if not connector.authenticate():
        raise RuntimeError("Slack authentication failed")

    processor = SlackProcessor()
    chunker = SlackChunkerStrategy(max_tokens_per_chunk=500, overlap_tokens=50, time_window_seconds=300)

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
        "url": "http://localhost",
        "port": 6333
    }
    vector_storage = VectorStorageFactory.create(storage_config)
    vector_storage.initialize()

    # Create MongoDB client
    mongo_client = pymongo.MongoClient(get_mongo_url())

    # Create data pipeline with existing logger
    slack_pipeline = SlackDataPipeline(mongo_client, logger=logger)

    response = []
    for channel in channel_list:
        try:
            channel_id = channel["channel_id"]
            channel_name = channel["channel_name"]

            # Process the slack channel using our pipeline
            slack_pipeline.process_slack_channel(channel_id, channel_name)

            # Start log monitoring - this will uses the event-driven handler system
            slack_pipeline.monitor.start_log_monitoring(target_logger=logger, pipeline_id=f"slack_{channel_id}")

            messages, thread_messages = connector.get_conversations_history(channel_id)
            processed_messages_data = processor.process(messages, channel_name=channel_name) 
            processed_thread_data = [
                processor.process(thread, channel_name=channel_name)
                for thread in thread_messages
            ]

            for processed_data in [processed_messages_data, processed_thread_data]:
                chunks = chunker.chunk_content(processed_data, upload_by)
                enriched = embedding_generator.generate_embeddings(chunks)
                vector_storage.store_embeddings(enriched)

                response.append({
                    "channel": channel_name,
                    "status": "success",
                    "chunks_stored": len(enriched)
                })
                
            slack_pipeline.monitor.finish_log_monitoring()
        except Exception as e:
            logger.error(f"Failed to embed channel {channel.get('channel_name')}: {str(e)}")
            response.append({
                "channel": channel.get("channel_name"),
                "status": "failed",
                "error": str(e)
            })

    return response

def count_channel_chunks(channel_name: str) -> int:
    storage_config = {
        "type": "qdrant",
        "collection_name": "slack_data",
        "embedding_dim": 384,  # Must match embedding model
        "url": "http://localhost",
        "port": 6333
    }
    vector_storage = VectorStorageFactory.create(storage_config)
    vector_storage.initialize()

    return vector_storage.count(filters={"metadata.channel_name": channel_name})

def get_best_match_results(query: str, top_k_results: int = 5, scope: str = "public", logged_in_user: str = "default"):
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
        "url": "http://localhost",
        "port": 6333
    }
    vector_storage = VectorStorageFactory.create(storage_config)
    vector_storage.initialize()
    
    query_embedding = embedding_generator.generate_query_embedding(query)
    
    search_results = vector_storage.search(
        query_embedding=query_embedding,
        top_k=top_k_results,
        filters={"upload_by": logged_in_user} if scope == "private" else {}
    )

    return search_results