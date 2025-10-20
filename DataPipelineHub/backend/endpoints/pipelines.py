from flask import Blueprint, jsonify
from webargs import fields
from shared.logger import logger
from global_utils.helpers.apiargs import from_body, from_query
from pipeline.pipeline_service import PipelineCeleryService
from pipeline.pipeline_repository import PipelineRepository
from utils.auth_manager import get_current_user
from config.constants import PipelineStatus

pipelines_bp = Blueprint("pipelines", __name__)


@pipelines_bp.route("/embed", methods=["PUT"])
@from_body({
    "data": fields.List(fields.Dict(), required=True),
    "type": fields.Str(required=True),
})
def start_pipeline(data, type):
    """
    Trigger the embedding pipeline for registered data sources.
    First calls registration task, waits for completion, then calls pipeline execution tasks.
    
    Args:
        data: List of data sources to register and process
        type: Type of data source (SLACK, DOCUMENT, etc.)
        
    Returns:
        JSON response indicating task submission status
    """
    try:
        pipeline_celery_service = PipelineCeleryService()
        response_data, status_code = pipeline_celery_service.execute_pipeline_workflow_with_registration(data, type)
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Failed to start pipeline: {str(e)}")
        return jsonify({"error": str(e)}), 500

@pipelines_bp.route("/queue/pending-count", methods=["GET"])
def get_pending_pipelines_count():
    """
    Get the total count of pending pipelines in the queue.
    
    Returns:
        JSON response with pending pipelines count
    """
    try:
        pipeline_repo = PipelineRepository()
        
        # Count pending pipelines
        pending_count = pipeline_repo.pipelines_collection.count_documents({
            "status": PipelineStatus.PENDING.value
        })
        
        # Debug logging
        logger.info(f"Pending pipelines count: {pending_count}")
        
        # Get some sample pending pipelines for debugging
        sample_pending = list(pipeline_repo.pipelines_collection.find(
            {"status": PipelineStatus.PENDING.value},
            {"pipeline_id": 1, "source_type": 1, "metadata": 1}
        ).limit(5))
        logger.info(f"Sample pending pipelines: {sample_pending}")
        
        return jsonify({
            "pending_count": pending_count
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get pending pipelines count: {str(e)}")
        return jsonify({"error": str(e)}), 500


@pipelines_bp.route("/queue/user-position", methods=["GET"])
@from_query({"source_type": fields.Str(required=True)})
def get_user_queue_position(source_type):
    """
    Get the current user's position in the queue for a specific source type.
    """
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "User not authenticated"}), 401

        pipeline_repo = PipelineRepository()
        coll = pipeline_repo.pipelines_collection
        source_type = source_type.upper()

        username = current_user.get("username")
        user_id = current_user.get("user_id")

        # Find the earliest pending pipeline created by this user
        user_pipeline = coll.find_one(
            {
                "status": PipelineStatus.PENDING.value,
                "source_type": source_type,
                "$or": [
                    {"metadata.upload_by": username},
                    {"metadata.user_id": user_id},
                    {"metadata.username": username}
                ]
            },
            sort=[("created_at", 1), ("_id", 1)]
        )

        if not user_pipeline:
            total_pending = coll.count_documents({
                "status": PipelineStatus.PENDING.value,
                "source_type": source_type
            })
            return jsonify({
                "user_position": None,
                "total_pending": total_pending,
                "has_pending": False
            }), 200

        created_at = user_pipeline["created_at"]
        pipeline_id = user_pipeline["_id"]

        # Get total pending count
        total_pending = coll.count_documents({
            "status": PipelineStatus.PENDING.value,
            "source_type": source_type
        })

        # Count pipelines created before this one
        user_position = coll.count_documents({
            "status": PipelineStatus.PENDING.value,
            "source_type": source_type,
            "$or": [
                {"created_at": {"$lt": created_at}},
                {"created_at": created_at, "_id": {"$lt": pipeline_id}}
            ]
        }) + 1

        return jsonify({
            "user_position": user_position,
            "total_pending": total_pending,
            "has_pending": True
        }), 200

    except Exception as e:
        logger.error(f"Failed to get user queue position: {str(e)}")
        return jsonify({"error": str(e)}), 500