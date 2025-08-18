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
    "limit": fields.Int(required=False, load_default=50),
    "offset": fields.Int(required=False, load_default=0),
})
def list_resources(user_id, category=None, type=None, limit=50, offset=0):
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
})
def update_resource(resource_id, config):
    svc = current_app.container.resources_service
    try:
        doc = svc.update(resource_id, config=config)
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


@resources_bp.route("/resource.schema", methods=["GET"])
def get_resource_schema():
    """Get the JSON schema for ResourceDoc model."""
    svc = current_app.container.resources_service
    try:
        schema = svc.get_resource_schema()
        return jsonify(schema), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
