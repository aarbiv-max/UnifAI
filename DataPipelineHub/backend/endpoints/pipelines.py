from flask import Blueprint, jsonify
from webargs import fields
from shared.logger import logger
from global_utils.helpers.apiargs import from_body
from pipeline.pipeline_service import PipelineCeleryService

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
