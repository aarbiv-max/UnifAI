"""Data source endpoints - driving adapter."""
from flask import Blueprint, jsonify
from webargs import fields

from bootstrap.app_container import data_source_service
from global_utils.helpers.apiargs import from_query, from_body
from shared.logger import logger

data_sources_bp = Blueprint("data_sources", __name__)


@data_sources_bp.route("/data.sources.get", methods=["GET"])
@from_query({
    "source_type": fields.Str(required=True),
    "filter_query": fields.Str(required=False, load_default=None)
})
def get_sources(source_type, filter_query):
    """
    Retrieve all data sources of a given type including pipeline statistics.
    
    Parameters:
        source_type (str): The data source type to list.
        filter_query (str | None): Optional filter string to narrow results; may be None.
    
    Returns:
        A JSON response with {"sources": [...] } and HTTP 200 on success, or {"error": "<message>"} and HTTP 500 on failure.
    """
    try:
        sources = data_source_service().list_with_stats(source_type)
        return jsonify({"sources": sources}), 200
    except Exception as e:
        logger.error(f"Failed to get available data sources list: {str(e)}")
        return jsonify({"error": str(e)}), 500


@data_sources_bp.route("/data.source.delete", methods=["DELETE"])
@from_body({"pipeline_ids": fields.List(fields.Str(), required=True)})
def delete_sources(pipeline_ids):
    """
    Delete multiple data sources identified by their IDs and return an aggregated result.
    
    Processes each ID in `pipeline_ids` (treated as a source ID for backend lookup), attempts to delete the corresponding source and its vector data, and accumulates per-item success/failure details.
    
    Parameters:
        pipeline_ids (list[str]): List of IDs provided by the API (named `pipeline_ids` for compatibility but used as source IDs for lookup).
    
    Returns:
        tuple: A Flask JSON response and HTTP status code.
            - If all deletions succeed: JSON with "status": "success", a success message, and detailed "results"; HTTP 200.
            - If some deletions succeed and some fail: JSON with "status": "partial", counts and detailed "results"; HTTP 207.
            - If all deletions fail: JSON with "status": "error", a failure message, and detailed "results"; HTTP 500.
            - On unexpected error: JSON `{"error": <message>}`; HTTP 500.
    """
    try:
        svc = data_source_service()
        results = {"succeeded": [], "failed": []}
        
        for source_id in pipeline_ids:
            try:
                # Get source by source_id (matching backend behavior)
                source = svc.get_by_id(source_id)
                if not source:
                    results["failed"].append({
                        "pipeline_id": source_id,
                        "error": "Source not found"
                    })
                    continue
                
                result = svc.delete(source.source_id)
                if result.success:
                    results["succeeded"].append({
                        "pipeline_id": source_id,
                        "result": {
                            "source_id": result.source_id,
                            "source_name": result.source_name,
                            "qdrant_embeddings_deleted": result.vectors_deleted,
                            "mongo_source_deleted": result.source_deleted,
                            "mongo_pipelines_deleted": result.pipelines_deleted,
                        }
                    })
                else:
                    results["failed"].append({
                        "pipeline_id": source_id,
                        "error": result.message
                    })
            except Exception as e:
                results["failed"].append({
                    "pipeline_id": source_id,
                    "error": str(e)
                })
        
        # Format response based on results
        if len(results["failed"]) == 0:
            return jsonify({
                "status": "success",
                "message": f"Successfully deleted {len(results['succeeded'])} source(s)",
                "results": results
            }), 200
        elif len(results["succeeded"]) > 0:
            return jsonify({
                "status": "partial",
                "message": f"Deleted {len(results['succeeded'])} source(s), {len(results['failed'])} failed",
                "results": results
            }), 207  # Multi-Status
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to delete all {len(results['failed'])} source(s)",
                "results": results
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to delete data sources: {str(e)}")
        return jsonify({"error": str(e)}), 500


@data_sources_bp.route("/data.source.details.get", methods=["GET"])
@from_query({"source_id": fields.Str(required=True)})
def get_source_details(source_id):
    """
    Retrieve detailed information for a single data source, including full text.
    
    Parameters:
        source_id (str): Identifier of the data source to fetch.
    
    Returns:
        A Flask JSON response tuple:
          - On success (found): JSON {"success": True, "source": <source object>}, HTTP 200.
          - If not found: JSON {"success": False, "message": "Source <source_id> not found"}, HTTP 404.
          - On error: JSON {"error": "<error message>"}, HTTP 500.
    """
    try:
        result = data_source_service().get_with_stats(source_id)
        
        if result:
            return jsonify({"success": True, "source": result}), 200
        else:
            return jsonify({
                "success": False,
                "message": f"Source {source_id} not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Failed to get data source details for {source_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@data_sources_bp.route("/data.source.update", methods=["PUT"])
@from_body({
    "source_id": fields.Str(required=True),
    "updates": fields.Dict(required=True)
})
def update_source(source_id, updates):
    """
    Update an existing data source identified by its source ID.
    
    Parameters:
        source_id (str): Identifier of the source to update.
        updates (dict): Mapping of fields and values to apply to the source.
    
    Returns:
        tuple: A Flask response tuple (JSON, status_code). On success the JSON contains
        {"status": "success", "message": "...", "modified": True} with HTTP 200. If the
        source is not found the JSON contains {"status": "error", "message": "..."} with
        HTTP 404. On unexpected errors the JSON contains {"error": "<message>"} with HTTP 500.
    """
    try:
        success = data_source_service().update(source_id, updates)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Source {source_id} updated successfully",
                "modified": True
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": f"Source {source_id} not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Failed to update data source {source_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
