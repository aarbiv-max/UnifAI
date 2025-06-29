from flask import Blueprint, jsonify
from providers.slack.stats import SlackStatsProvider
from utils.storage.mongo.mongo_helpers import get_mongo_storage, get_source_service
from webargs import fields
from shared.logger import logger
from global_utils.helpers.apiargs import from_query, from_body
from global_utils.celery_app.helpers import send_task
from providers.slack.slack import (
    get_available_slack_channels,
    embed_slack_channels_flow,
    count_channel_chunks,
    get_best_match_results,
    delete_slack_channel
)

slack_bp = Blueprint("slack", __name__)

@slack_bp.route("/available.slack.channels.get", methods=["GET"])
@from_query({
    "types": fields.Str(required=True, data_key='types')
})
def available_slack_channels(types):
    try:
        channels = get_available_slack_channels(types)
        return jsonify({"channels": channels}), 200
    except Exception as e:
        logger.error(f"Failed to get available Slack channels: {str(e)}")
        return jsonify({"error": str(e)}), 500


@slack_bp.route("/embed.channels", methods=["PUT"])
@from_body({
    "channels": fields.List(fields.Dict(), required=True)
})
def embed_channels(channels):
    try:
        send_task(
            task_name="data_sources.slack.slack_tasks.embed_slack_channels_task",
            celery_queue="slack_queue",
            channel_list=channels
        )
        return jsonify({"status": "task submitted"}), 202
    except Exception as e:
        logger.error(f"Failed to submit Slack embedding task: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

# @slack_bp.route("/embed.channels.direct", methods=["PUT"])
# @from_body({
#     "channels": fields.List(fields.Dict(), required=True)
# })
# def embed_channels(channels):
#     try:
#         results = embed_slack_channels_flow(channels)
#         return jsonify({"status": "success", "details": results}), 200
#     except Exception as e:
#         logger.error(f"Embedding Slack channels failed: {str(e)}")
#         return jsonify({"error": str(e)}), 500


@slack_bp.route("/slack.channel.chunks", methods=["GET"])
@from_query({
    "channel_name": fields.Str(required=True)
})
def slack_channel_chunks(channel_name):
    try:
        count = count_channel_chunks(channel_name)
        return jsonify({"channel_name": channel_name, "chunk_count": count}), 200
    except Exception as e:
        logger.error(f"Counting chunks failed: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
    
@slack_bp.route("/query.match", methods=["GET"])
@from_query({
    "query": fields.Str(required=True),
    "top_k_results": fields.Int(required=False)
})
def best_match_results(query, top_k_results):
    try:
        search_results = get_best_match_results(query, top_k_results)
        return jsonify({"search_results": search_results}), 200
    except Exception as e:
        logger.error(f"Failed to find best match for user query: {str(e)}")
        return jsonify({"error": str(e)}), 500


@slack_bp.route('/embed.channels', methods=['GET'])
def get_embed_channels():
    """
    Returns all stored channels, optionally filtered by source_type.
    """
    source_type = "SLACK"
    svc = get_source_service()
    channels = svc.list_sources_with_status(source_type)
    return jsonify(channels), 200

@slack_bp.route("/stats", methods=["GET"])
def system_stats():
    provider = SlackStatsProvider()
    stats    = provider.get_stats()
    return jsonify(stats), 200

@slack_bp.route("/embed.channels/<channel_id>", methods=["DELETE"])
def delete_embed_channel(channel_id):
    """
    Delete a slack channel from both MongoDB and Qdrant storage.
    """
    try:
        result = delete_slack_channel(channel_id)
        return jsonify({"status": "success", "message": f"Channel {channel_id} deleted successfully", "result": result}), 200
    except Exception as e:
        logger.error(f"Failed to delete Slack channel {channel_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500