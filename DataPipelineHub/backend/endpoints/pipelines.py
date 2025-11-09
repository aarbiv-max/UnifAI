from flask import Blueprint, jsonify, session
from webargs import fields
from shared.logger import logger
from global_utils.helpers.apiargs import from_body
from pipeline.pipeline_service import PipelineCeleryService
from registration.registration_service import RegistrationService

pipelines_bp = Blueprint("pipelines", __name__)


@pipelines_bp.route("/embed", methods=["PUT"])
@from_body({
    "data": fields.List(fields.Dict(), required=True),
    "type": fields.Str(required=True),
})
def start_pipeline(data, type):
    """
    Trigger the embedding pipeline for registered data sources.
    Performs registration synchronously, then enqueues pipeline execution tasks to Celery.
    
    Args:
        data: List of data sources to register and process
        type: Type of data source (SLACK, DOCUMENT, etc.)
        
    Returns:
        JSON response indicating submission status
    """
    try:
        current_user = session.get('user', {}).get('username', 'default')

        registration_response = RegistrationService().register_sources(
            data_list=data,
            source_type=type.upper(),
            upload_by=current_user,
        )

        registered_sources = registration_response.get("registered_sources", [])
        if registered_sources:
            pipeline_celery_service = PipelineCeleryService()
            response_data, status_code = pipeline_celery_service.execute_pipeline(registered_sources, type)
        else:
            response_data, status_code = {
                "status": "no_registered_sources",
                "message": "No sources registered; skipping pipeline execution",
                "pipeline_worker_tasks_submitted": 0,
                "source_count": 0,
            }, 200

        result = {
            "registration_completed": True,
            "registration": registration_response,
            "pipeline_execution": {
                "data": response_data,
                "status_code": status_code,
            },
        }
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Failed to start pipeline: {str(e)}")
        return jsonify({"error": str(e)}), 500
