from flask import Blueprint, jsonify, current_app
from global_utils.helpers.apiargs import from_body, from_query
from webargs import fields
from resources.errors import ResourceInUseError

resources_bp = Blueprint("resources", __name__)


@resources_bp.route("/resource.save", methods=["POST"])
@from_body({
    "user_id": fields.Str(data_key="userId", required=True),
    "category": fields.Str(required=True),
    "type": fields.Str(required=True),
    "name": fields.Str(required=True),
    "config": fields.Dict(required=True),
})
def save_resource(user_id, category, type, name, config):
    svc = current_app.container.resources_service
    try:
        doc = svc.create(user_id=user_id,
                         category=category,
                         type=type,
                         name=name,
                         config=config)
        return jsonify(doc.model_dump(mode="json")), 201
    except ValueError as e:  # duplicate name, bad input, etc.
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route("/resource.get", methods=["GET"])
@from_query({
    "resource_id": fields.Str(data_key="resourceId", required=True),
})
def get_resource(resource_id):
    """Get a single resource by ID."""
    svc = current_app.container.resources_service
    try:
        doc = svc.get(resource_id)
        return jsonify(doc.model_dump(mode="json")), 200
    except KeyError as e:
        return jsonify({"error": f"Resource not found: {e}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route("/resources.list", methods=["GET"])
@from_query({
    "user_id": fields.Str(data_key="userId", required=True),
    "category": fields.Str(required=False),
    "type": fields.Str(required=False),
    "limit": fields.Int(required=False, load_default=1000),
    "offset": fields.Int(required=False, load_default=0),
})
def list_resources(user_id, category=None, type=None, limit=1000, offset=0):
    """
    Get resources with flexible filtering and pagination:
    - Only user_id: returns all resources for that user
    - user_id + category: returns all resources of that category for the user
    - user_id + category + type: returns all resources of that specific type for the user
    - limit/offset: pagination support
    """
    svc = current_app.container.resources_service
    try:
        resources, total_count = svc.find_resources(
            user_id=user_id,
            category=category,
            type=type,
            limit=limit,
            offset=offset
        )
        return jsonify({
            "resources": [doc.model_dump(mode="json") for doc in resources],
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(resources) < total_count
            }
        }), 200
    except ValueError as e:  # Invalid category enum
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route("/resource.update", methods=["PUT"])
@from_body({
    "resource_id": fields.Str(data_key="resourceId", required=True),
    "config": fields.Dict(required=True),
    "name": fields.Str(required=False),
})
def update_resource(resource_id, config, name=None):
    svc = current_app.container.resources_service
    try:
        doc = svc.update(resource_id, config=config, name=name)
        return jsonify(doc.model_dump(mode="json")), 200
    except KeyError as e:  # unknown id
        return jsonify({"error": f"Resource not found: {e}"}), 404
    except ValueError as e:  # validation, duplicate name, etc.
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route("/resource.delete", methods=["DELETE"])
@from_query({
    "resource_id": fields.Str(data_key="resourceId", required=True),
})
def delete_resource(resource_id):
    # TODO: Add authorization check - verify user has permission to delete this resource
    svc = current_app.container.resources_service
    try:
        svc.delete(resource_id)
        return jsonify({"status": "deleted"}), 200
    except ResourceInUseError as e:
        # The resource is referenced by blueprints or other resources
        return jsonify({"error": str(e),
                        "blueprints": e.by_blueprints,
                        "resources": e.by_resources}), 400
    except KeyError as e:
        return jsonify({"error": f"Resource not found: {e}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route("/doc.usage.get", methods=["GET"])
@from_query({
    "doc_ids": fields.Str(data_key="docIds", required=True),
})
def get_doc_usage(doc_ids):
    """
    Check whether one or more documents (by source_id) are referenced
    in any retriever's docs list.

    Query param docIds is a comma-separated string of source IDs.
    Returns a list of retrievers grouped as own / others relative to
    the requesting user.
    """
    svc = current_app.container.resources_service
    try:
        ids = [d.strip() for d in doc_ids.split(",") if d.strip()]
        if not ids:
            return jsonify({"retrievers": [], "in_use": False}), 200

        resources = svc.find_doc_usage(ids)
        retrievers = [
            {"rid": r.rid, "name": r.name, "user_id": r.user_id}
            for r in resources
        ]
        return jsonify({
            "retrievers": retrievers,
            "in_use": len(retrievers) > 0,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route("/doc.detach", methods=["POST"])
@from_body({
    "doc_ids": fields.List(fields.Str(), data_key="docIds", required=True),
})
def detach_docs(doc_ids):
    """
    Remove document references from every retriever that uses them.
    Called before actually deleting the documents from the RAG service.
    """
    svc = current_app.container.resources_service
    try:
        modified = svc.remove_docs_from_retrievers(doc_ids)
        return jsonify({"modified_retrievers": modified}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route("/resource.schema", methods=["GET"])
def get_resource_schema():
    """Get the JSON schema for Resource model."""
    svc = current_app.container.resources_service
    try:
        schema = svc.get_resource_schema()
        return jsonify(schema), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route("/resource.validate", methods=["POST"])
@from_body({
    "resource_id": fields.Str(data_key="resourceId", required=True),
    "timeout_seconds": fields.Float(data_key="timeoutSeconds", load_default=10.0),
})
def validate_resource(resource_id, timeout_seconds):
    """Validate a saved resource and its dependencies."""
    svc = current_app.container.resources_service
    try:
        result = svc.validate_resource(
            rid=resource_id,
            timeout_seconds=timeout_seconds,
        )
        return jsonify(result.to_dict()), 200
    except KeyError as e:
        return jsonify({"error": f"Resource not found: {e}"}), 404
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route("/resources.validate", methods=["POST"])
@from_body({
    "resource_ids": fields.List(fields.Str(), data_key="resourceIds", required=True),
    "timeout_seconds": fields.Float(data_key="timeoutSeconds", load_default=10.0),
    "max_workers": fields.Int(data_key="maxWorkers", load_default=10),
})
def validate_resources(resource_ids, timeout_seconds, max_workers):
    """
    Validate multiple resources in parallel.
    
    Request:
        {
            "resourceIds": ["rid1", "rid2", "rid3"],
            "timeoutSeconds": 10.0,
            "maxWorkers": 10
        }
        
    Response:
        [
            { "element_rid": "rid1", "is_valid": true, ... },
            { "element_rid": "rid2", "is_valid": false, ... },
            { "element_rid": "rid3", "is_valid": true, ... }
        ]
        
    Results are returned in the same order as the input resourceIds.
    """
    svc = current_app.container.resources_service
    
    # Validate input
    if not resource_ids:
        return jsonify([]), 200
    
    # Cap max_workers and ensure a positive value
    max_workers = max(1, min(max_workers, 20))
    
    try:
        results = svc.validate_resources(
            rids=resource_ids,
            timeout_seconds=timeout_seconds,
            max_workers=max_workers,
        )
        return jsonify([r.to_dict() for r in results]), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@resources_bp.route("/config.validate", methods=["POST"])
@from_body({
    "category": fields.Str(required=True),
    "type": fields.Str(required=True),
    "name": fields.Str(required=False),
    "config": fields.Dict(required=True),
    "timeout_seconds": fields.Float(data_key="timeoutSeconds", load_default=10.0),
})
def validate_config(category, type, config, name=None, timeout_seconds=10.0):
    """
    Validate a resource config before saving.
    
    Same fields as resource.save but validates without saving to database.
    Useful for pre-save validation in the UI.
    """
    svc = current_app.container.resources_service
    try:
        result = svc.validate_config(
            category=category,
            element_type=type,
            config=config,
            name=name,
            timeout_seconds=timeout_seconds,
        )
        return jsonify(result.to_dict()), 200
    except ValueError as e:
        return jsonify({"error": f"Schema validation failed: {e}"}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
