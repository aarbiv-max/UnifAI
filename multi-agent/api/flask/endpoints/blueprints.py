from flask import Blueprint, jsonify, current_app, request
from global_utils.helpers.apiargs import from_body, from_query
from webargs import fields
import yaml
from werkzeug.exceptions import BadRequest

blueprints_bp = Blueprint("blueprints", __name__)


@blueprints_bp.route("/available.blueprints.get", methods=["GET"])
@from_query({
    "user_id": fields.Str(data_key="userId", required=True)
})
def available_doc_list(user_id):
    try:
        svc = current_app.container.blueprint_service
        return jsonify(svc.list_draft_docs(user_id=user_id)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@blueprints_bp.route("/blueprint.save", methods=["POST"])
@from_body({
    "blueprint_raw": fields.Str(data_key="blueprintRaw", required=False),  # optional for non-JSON/YAML raw
    "user_id": fields.Str(data_key="userId", required=False, load_default="alice")
})
def save_blueprint(blueprint_raw=None, user_id="alice"):
    try:
        # Case 1: JSON body with field 'blueprintRaw'
        if blueprint_raw:
            raw_text = blueprint_raw

        # Case 2: Raw text body (YAML or JSON), e.g., Content-Type: application/x-yaml or text/plain
        elif request.content_type and (
                "yaml" in request.content_type or request.content_type.startswith("text/plain")
        ):
            raw_text = request.data.decode("utf-8")

        # Case 3: form-data file upload
        elif "blueprint_raw" in request.files:
            file = request.files["blueprint_raw"]
            raw_text = file.read().decode("utf-8")

        # Case 4: form-data string field
        elif "blueprint_raw" in request.form:
            raw_text = request.form["blueprint_raw"]

        else:
            raise BadRequest("Missing blueprint data in request")

        # Parse the YAML or JSON string
        try:
            parsed = yaml.safe_load(raw_text)
            if not isinstance(parsed, dict):
                raise ValueError("Parsed blueprint must be a dictionary.")
        except Exception as e:
            raise BadRequest(f"Invalid blueprint format: {e}")

        # Save using service
        svc = current_app.container.blueprint_service
        blueprint_id = svc.save_draft(user_id=user_id, draft_dict=parsed)

        return jsonify({
            "status": "success",
            "blueprint_id": blueprint_id
        }), 201

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@blueprints_bp.route("/blueprint.draft.schema.get", methods=["GET"])
def blueprint_draft_schema_get():
    """
    Returns the schema for blueprint drafts.
    """
    try:
        svc = current_app.container.blueprint_service
        schema = svc.get_draft_schema()
        return jsonify(schema), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
