from flask import Blueprint, jsonify, current_app, request
from global_utils.helpers.apiargs import from_body
from webargs import fields
import yaml
from werkzeug.exceptions import BadRequest

blueprints_bp = Blueprint("blueprints", __name__)


@blueprints_bp.route("/available.blueprints.get", methods=["GET"])
def available_doc_list():
    try:
        svc = current_app.container.blueprint_service
        return jsonify(svc.list_dicts()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@blueprints_bp.route("/blueprint.save", methods=["POST"])
@from_body({
    "blueprint_raw": fields.Str(data_key="blueprintRaw", required=False)  # optional for non-JSON/YAML raw
})
def save_blueprint(blueprint_raw=None):
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
        blueprint_id = svc.save(parsed)

        return jsonify({
            "status": "success",
            "blueprint_id": blueprint_id
        }), 201

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
