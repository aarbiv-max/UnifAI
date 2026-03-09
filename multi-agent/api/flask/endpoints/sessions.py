from flask import Blueprint, jsonify, current_app, Response
from global_utils.helpers.apiargs import from_body, from_query
from webargs import fields
import json
from pydantic.json import pydantic_encoder
from session.exceptions import BlueprintNotFoundError
from api.flask.streaming import HeartbeatStream

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.route("/user.session.create", methods=["POST"])
@from_body({
    "blueprint_id": fields.Str(data_key="blueprintId", required=True),
    "user_id": fields.Str(data_key="userId", required=True),
    "metadata": fields.Dict(data_key="metadata", required=False, load_default=lambda: {}, dump_default=lambda: {})
})
def create_user_session(blueprint_id, user_id, metadata):
    try:
        session_svc = current_app.container.session_service
        session = session_svc.create(user_id=user_id,
                                     blueprint_id=blueprint_id,
                                     metadata=metadata)
        return jsonify(session.get_run_id()), 200
    except BlueprintNotFoundError as e:
        return jsonify({
            "error": str(e), 
            "error_type": "BLUEPRINT_NOT_FOUND",
            "blueprint_id": e.blueprint_id
        }), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/user.session.execute", methods=["POST"])
@from_body({
    "session_id": fields.Str(data_key="sessionId", required=True),
    "inputs": fields.Dict(data_key="inputs", required=True),
    "stream_mode": fields.List(fields.Str(), data_key="streamMode", load_default=lambda: ["custom"]),
    "stream": fields.Bool(data_key="stream", load_default=False),
    "scope": fields.Str(data_key="scope", load_default="public"),
    "logged_in_user": fields.Str(data_key="loggedInUser", required=False, load_default=lambda: "")
})
def execute_user_session(session_id, inputs, stream_mode, stream, scope, logged_in_user):
    """
    Execute (or stream) an existing session.
    - If `stream` is False (default), returns the full result as JSON.
    - If `stream` is True, returns an NDJSON stream of chunks.
    """
    svc = current_app.container.session_service

    try:
        if not stream:
            # synchronous run
            result = svc.execute(
                session_id=session_id,
                inputs=inputs,
                stream=False,
                scope=scope,
                logged_in_user=logged_in_user
            )
            return json.dumps(result, default=pydantic_encoder), 200

        # streaming run
        def generate():
            source = svc.execute(
                session_id=session_id,
                inputs=inputs,
                stream=True,
                stream_mode=stream_mode,
                scope=scope,
                logged_in_user=logged_in_user
            )
            heartbeat_stream = HeartbeatStream(source)

            try:
                for chunk in heartbeat_stream:
                    yield json.dumps(chunk, default=pydantic_encoder) + "\n"
            except GeneratorExit:
                heartbeat_stream.close()
                raise

        return Response(
            generate(),
            mimetype="application/x-ndjson"
        )
    
    except BlueprintNotFoundError as e:
        return jsonify({
            "error": str(e), 
            "error_type": "BLUEPRINT_DELETED",
            "blueprint_id": e.blueprint_id,
            "session_id": e.session_id
        }), 410  # Gone
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/session.state.get", methods=["GET"])
@from_query({
    "session_id": fields.Str(data_key="sessionId", required=True),
})
def get_session_state(session_id):
    try:
        svc = current_app.container.session_service
        state = svc.get_state(run_id=session_id)
        return jsonify(state), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/session.status.get", methods=["GET"])
@from_query({
    "session_id": fields.Str(data_key="sessionId", required=True),
})
def get_session_status(session_id):
    try:
        svc = current_app.container.session_service
        status = svc.get_status(run_id=session_id)
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/session.user.chat.get", methods=["GET"])
@from_query({
    "user_id": fields.Str(data_key="userId", required=True),
})
def get_session_user_chat(user_id):
    try:
        svc = current_app.container.session_service
        return jsonify(svc.get_user_sessions_chat_history(user_id)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/session.user.blueprints.get", methods=["GET"])
@from_query({
    "user_id": fields.Str(data_key="userId", required=True),
})
def get_user_blueprints(user_id):
    try:
        svc = current_app.container.session_service
        return jsonify(svc.get_user_blueprints(user_id)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/session.delete", methods=["DELETE"])
@from_query({
    "session_id": fields.Str(data_key="sessionId", required=True),
})
def delete_session(session_id):
    """
    Delete a session by session_id.
    Returns success: true if deleted, false if not found.
    """
    # TODO: Add authorization check - verify user has permission to delete this session
    try:
        svc = current_app.container.session_service
        deleted = svc.delete(run_id=session_id)
        return jsonify({"success": deleted}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/session.stream.subscribe", methods=["GET"])
@from_query({
    "session_id": fields.Str(data_key="sessionId", required=True),
    "from_id": fields.Str(data_key="fromId", required=False, load_default="0"),
    "heartbeat_interval": fields.Int(data_key="heartbeatInterval", required=False, load_default=15)
})
def subscribe_to_session_stream(session_id, from_id, heartbeat_interval):
    """
    Subscribe to a session's event stream via Redis Streams.
    
    Provides two phases:
      1. Replay: Returns all historical events since `from_id`
      2. Live: Blocks and waits for new events as they arrive
    
    This enables GUI reconnection - when a user navigates away and returns,
    they can resume from where they left off by providing the last seen event ID.
    
    The response format matches user.session.execute to ensure consistency
    between initial streaming and reconnection scenarios.
    
    Query Parameters:
        sessionId: The session to subscribe to
        fromId: Start reading after this event ID ("0" for all history)
        heartbeatInterval: Seconds between heartbeat messages (default 15)
    
    Returns:
        NDJSON stream of events in the same format as user.session.execute:
        {"type": "custom", ...event data...}
        
        Heartbeat messages: {"type": "heartbeat"}
        End signal: {"type": "stream_end"}
    """
    stream_reader = current_app.container.redis_stream_reader
    
    # Check if Redis is available
    if not _is_redis_available():
        return jsonify({
            "error": "Stream subscription not available - Redis not configured",
            "error_type": "REDIS_UNAVAILABLE"
        }), 503
    
    # Check if session exists
    status = stream_reader.get_session_status(session_id)
    if status is None:
        return jsonify({
            "error": f"Session {session_id} not found in stream",
            "error_type": "SESSION_NOT_FOUND"
        }), 404

    def generate():
        last_id = from_id
        heartbeat_ms = heartbeat_interval * 1000
        
        try:
            # Phase 1: Replay historical events
            history = stream_reader.read_history(session_id, from_id=from_id)
            for event_id, event_data in history:
                last_id = event_id
                # Return event_data directly to match user.session.execute structure
                yield json.dumps(event_data, default=pydantic_encoder) + "\n"
                
                # Check for stream end in history
                if event_data.get("type") == "stream_end":
                    return
            
            # Phase 2: Live - block and wait for new events
            while True:
                events = stream_reader.read_blocking(
                    session_id,
                    last_id=last_id if last_id != "0" else "$",
                    block_ms=heartbeat_ms
                )
                
                if not events:
                    yield json.dumps({"type": "heartbeat"}) + "\n"
                    continue
                
                for event_id, event_data in events:
                    last_id = event_id
                    # Return event_data directly to match user.session.execute structure
                    yield json.dumps(event_data, default=pydantic_encoder) + "\n"
                    
                    # Check for terminal events
                    event_type = event_data.get("type")
                    if event_type in ("stream_end", "stream_error"):
                        return
        
        except GeneratorExit:
            pass

    return Response(
        generate(),
        mimetype="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@sessions_bp.route("/session.stream.status", methods=["GET"])
@from_query({
    "session_id": fields.Str(data_key="sessionId", required=True),
})
def get_session_stream_status(session_id):
    """
    Get the streaming status of a session.
    
    Returns metadata about the session's Redis stream including:
      - Whether the session is currently active (running)
      - Total number of events emitted
      - Last event ID (for resume capability)
      - Timestamps for started/completed/failed
    
    Query Parameters:
        sessionId: The session to check
    
    Returns:
        JSON object with stream status, or error if not found.
    """
    stream_reader = current_app.container.redis_stream_reader
    
    if not _is_redis_available():
        return jsonify({
            "error": "Stream status not available - Redis not configured",
            "error_type": "REDIS_UNAVAILABLE"
        }), 503
    
    try:
        status = stream_reader.get_session_status(session_id)
        
        if status is None:
            return jsonify({
                "error": f"Session {session_id} not found in stream",
                "error_type": "SESSION_NOT_FOUND",
                "session_id": session_id
            }), 404
        
        return jsonify(status), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/session.stream.active", methods=["GET"])
def list_active_session_streams():
    """
    List all currently active (running) session streams.
    
    Returns:
        JSON array of session IDs that are currently streaming.
    """
    stream_reader = current_app.container.redis_stream_reader
    
    if not _is_redis_available():
        return jsonify({
            "error": "Stream listing not available - Redis not configured",
            "error_type": "REDIS_UNAVAILABLE"
        }), 503
    
    try:
        active_sessions = stream_reader.list_active_sessions()
        return jsonify({
            "active_sessions": active_sessions,
            "count": len(active_sessions)
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _is_redis_available() -> bool:
    """Check if Redis stream reader is available and functional."""
    try:
        reader = current_app.container.redis_stream_reader
        if reader is None:
            return False
        return reader.is_available()
    except Exception:
        return False
