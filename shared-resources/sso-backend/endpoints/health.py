from flask import Blueprint, jsonify
from config.app_config import AppConfig

health_bp = Blueprint("health", __name__)

@health_bp.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Server is healthy"}), 200

@health_bp.route("/version", methods=["GET"])
def get_version():
    app_config = AppConfig.get_instance()
    return jsonify({"module_version": app_config.module_version}), 200
