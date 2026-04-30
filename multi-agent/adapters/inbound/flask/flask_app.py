from flask import Flask
from config.app_config import AppConfig
from .endpoints import register_all_endpoints
from flask_cors import CORS
from global_utils.flask.request_rules import RequestRules


def create_app(container, config: AppConfig = None) -> Flask:
    """
    Application factory.

    Receives a fully-wired AppContainer from the entry point.
    This adapter never creates the container itself — it only consumes it.
    """
    config = config or AppConfig.get_instance()
    app = Flask(__name__)
    app.version = config.get("version", "1.0.0")
    app.config["admin_allowed_users"] = config.admin_allowed_users

    max_upload = config.file_upload_max_count * config.file_upload_max_size_mb * 1024 * 1024
    app.config["MAX_CONTENT_LENGTH"] = max_upload + 1024 * 1024
    app.config["FILE_UPLOAD_MAX_COUNT"] = config.file_upload_max_count
    app.config["FILE_UPLOAD_MAX_SIZE_BYTES"] = config.file_upload_max_size_mb * 1024 * 1024
    app.config["ALLOWED_MIME_TYPES"] = config.file_upload_allowed_mime_types

    CORS(app, resources={r"/api/*": {"origins": "*",
                                     "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                                     "allow_headers": ["Content-Type", "Authorization"],
                                     "supports_credentials": True}})

    app.container = container
    register_all_endpoints(app)
    RequestRules(app)

    return app
