"""Slack endpoints - driving adapter."""
from flask import Blueprint, jsonify, request
from webargs import fields

from bootstrap.app_container import (
    slack_connector,
    vector_stats_service,
    retrieval_service,
    slack_stats_service,
    slack_event_dispatch_service,
)
from global_utils.helpers.apiargs import from_query
from shared.logger import logger

slack_bp = Blueprint("slack", __name__)

# Default project ID - should come from session/config in production
DEFAULT_PROJECT_ID = "default"


@slack_bp.route("/fetch.available.slack.channels", methods=["PUT"])
def fetch_slack_channels():
    """
    Fetch and cache Slack channels from the API.
    
    Returns:
        flask.Response: On success, a JSON response {"status": "channels fetched and cached", "count": <int>} with HTTP 200. On failure, a JSON response {"error": "<message>"} with HTTP 500.
    """
    try:
        connector = slack_connector(DEFAULT_PROJECT_ID)
        channels = connector.fetch_and_cache_channels()
        return jsonify({"status": "channels fetched and cached", "count": len(channels)}), 200
    except Exception as e:
        logger.error(f"Failed to fetch available Slack channels: {str(e)}")
        return jsonify({"error": str(e)}), 500


@slack_bp.route("/available.slack.channels.get", methods=["GET"])
@from_query({
    "types": fields.Str(required=True, data_key="types"),
    "cursor": fields.Str(required=False, load_default="", data_key="cursor"),
    "limit": fields.Int(required=False, load_default=50, data_key="limit"),
    "search_regex": fields.Str(required=False, load_default=None, data_key="search_regex"),
})
def get_available_channels(types, cursor, limit, search_regex):
    """
    Retrieve cached Slack channels with optional filtering and pagination.
    
    Parameters:
        types (str): Comma-separated channel type filters (e.g., "public_channel,private_channel").
        cursor (str): Pagination cursor returned by a previous call; use empty string or None for the first page.
        limit (int): Maximum number of channels to return.
        search_regex (str|None): Optional regular expression to filter channel names.
    
    Returns:
        tuple: (Response, int) where the JSON body contains a "channels" key with the paginated channels and related metadata, and the int is the HTTP status code.
    """
    try:
        connector = slack_connector(DEFAULT_PROJECT_ID)
        result = connector.get_available_slack_channels_from_cache(
            types=types,
            cursor=cursor if cursor else None,
            limit=limit,
            search_regex=search_regex,
        )
        return jsonify(result.to_dict(data_key="channels")), 200
        
    except Exception as e:
        logger.error(f"Failed to get available Slack channels: {str(e)}")
        return jsonify({"error": str(e)}), 500


@slack_bp.route("/slack.channel.chunks", methods=["GET"])
@from_query({"channel_name": fields.Str(required=True)})
def get_channel_chunks(channel_name):
    """
    Return the number of stored data chunks for the given Slack channel.
    
    Returns:
        dict: JSON-serializable mapping containing:
            - channel_name (str): the provided channel name
            - chunk_count (int): number of matching chunks
    """
    try:
        count = vector_stats_service().count_by_filter(
            collection_name="slack_data",
            filters={"metadata.channel_name": channel_name},
        )
        return jsonify({
            "channel_name": channel_name,
            "chunk_count": count,
        }), 200
        
    except Exception as e:
        logger.error(f"Counting chunks failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@slack_bp.route("/user.info.get", methods=["GET"])
@from_query({
    "user_id": fields.Str(required=False, load_default=None, data_key="user_id"),
    "include_locale": fields.Bool(required=False, load_default=False, data_key="include_locale"),
})
def get_user_info(user_id, include_locale):
    """
    Retrieve Slack user information.
    
    If `user_id` is provided, returns information for that user; otherwise returns information for the current authenticated user.
    
    Parameters:
        user_id (str | None): Slack user ID to look up, or None to use the authenticated user.
        include_locale (bool): If True, include locale information in the returned user data.
    
    Returns:
        dict: JSON response with `status: "success"` and `user_info` (dict) on success; on error returns JSON with an `error` string.
    """
    try:
        connector = slack_connector(DEFAULT_PROJECT_ID)
        user_info = connector.get_user_info(user_id=user_id, include_locale=include_locale)
        
        return jsonify({"status": "success", "user_info": user_info}), 200
            
    except Exception as e:
        logger.error(f"Failed to get Slack user info: {str(e)}")
        return jsonify({"error": str(e)}), 500


@slack_bp.route("/query.match", methods=["GET"])
@from_query({
    "query": fields.Str(required=True),
    "top_k_results": fields.Int(required=False, load_default=5),
    "scope": fields.Str(required=False, load_default="public"),
    "logged_in_user": fields.Str(required=False, load_default="default", data_key="loggedInUser"),
})
def query_match(query, top_k_results, scope, logged_in_user):
    """
    Perform a semantic search over Slack messages.
    
    Parameters:
        query (str): Text query to search for.
        top_k_results (int): Maximum number of results to return.
        scope (str): Search scope (e.g., "public" or other access scopes).
        logged_in_user (str): Identifier of the requesting user used to scope results.
    
    Returns:
        A Flask JSON response containing `search_results` (list of matching result objects) with HTTP status 200 on success, or `error` (string) with HTTP status 500 on failure.
    """
    try:
        svc = retrieval_service("SLACK")
        results = svc.search(
            query=query,
            limit=top_k_results,
            scope=scope,
            user=logged_in_user,
        )
        
        return jsonify({"search_results": results}), 200
        
    except Exception as e:
        logger.error(f"Failed to query Slack messages: {str(e)}")
        return jsonify({"error": str(e)}), 500


@slack_bp.route("/stats", methods=["GET"])
def slack_stats():
    """
    Retrieve aggregated Slack statistics.
    
    Returns:
        A Flask JSON response containing the aggregated statistics as a dictionary (HTTP 200) on success; on failure returns a JSON object with an "error" message and HTTP 500.
    """
    try:
        stats = slack_stats_service().get_stats()
        return jsonify(stats.to_dict()), 200
    except Exception as e:
        logger.error(f"Failed to get Slack stats: {str(e)}")
        return jsonify({"error": str(e)}), 500


@slack_bp.route("/events", methods=["POST"])
def slack_events():
    """
    Handle incoming Slack Events API webhooks.
    
    Processes the JSON payload from Slack. If the payload is a URL verification challenge, returns the challenge string; otherwise returns a JSON acknowledgement and dispatches event callbacks for asynchronous processing.
    
    Returns:
        Flask response: For URL verification, the raw challenge string with HTTP 200. For other events, a JSON object `{"status": "ok", "message": <message>}` with HTTP 200. On failure, a JSON object `{"error": <error message>}` with HTTP 500.
    """
    try:
        payload = request.get_json()
        result = slack_event_dispatch_service().handle_webhook(payload)
        
        # URL verification returns the challenge directly
        if result.event_type == "url_verification":
            return result.message, 200
            
        return jsonify({
            "status": "ok",
            "message": result.message,
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to handle Slack event: {str(e)}")
        return jsonify({"error": str(e)}), 500
