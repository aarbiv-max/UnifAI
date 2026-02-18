"""
Admin Config API endpoints.

Provides REST API for admin configuration:
  GET  /api/admin-config/config.get          — full template merged with stored values
  PUT  /api/admin-config/config.section.update — update one section's values
"""
from flask import Blueprint, jsonify, current_app
from global_utils.helpers.apiargs import from_body
from webargs import fields
import logging

logger = logging.getLogger(__name__)

admin_config_bp = Blueprint("admin_config", __name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Read — template + stored values
# ─────────────────────────────────────────────────────────────────────────────
@admin_config_bp.route("/config.get", methods=["GET"])
def get_config():
    """
    Return the full admin config template merged with stored values.

    The UI uses this to render the admin configuration page dynamically.
    """
    try:
        svc = current_app.container.admin_config_service
        config = svc.get_config()
        return jsonify(config.model_dump(mode="json")), 200
    except Exception as e:
        logger.exception("Error getting admin config")
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
#  Write — update one section
# ─────────────────────────────────────────────────────────────────────────────
@admin_config_bp.route("/config.section.update", methods=["PUT"])
@from_body({
    "section_key": fields.Str(data_key="sectionKey", required=True),
    "values": fields.Dict(required=True),
})
def update_section(section_key, values):
    """
    Update the stored values for a single config section.

    Body:
        sectionKey: The section key (e.g. "slack_channel_restrictions")
        values: Dict of field_key -> new value

    Returns:
        status: "success"
        on_update_action: Action identifier for downstream side-effects
                          (e.g. "clean_restricted_slack_channels"), or null.
    """
    try:
        svc = current_app.container.admin_config_service
        success, action = svc.update_section(section_key, values)

        return jsonify({
            "status": "success",
            "on_update_action": action,
        }), 200

    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception("Error updating admin config section '%s'", section_key)
        return jsonify({"error": str(e)}), 500
