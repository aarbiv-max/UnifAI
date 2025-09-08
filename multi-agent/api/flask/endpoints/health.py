from flask import Blueprint, jsonify
import os

health_bp = Blueprint("health", __name__)

@health_bp.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Server is healthy"}), 200

@health_bp.route("/version", methods=["GET"])
def get_version():
    module_version = os.getenv("MODULE_VERSION", "unknown")
    return jsonify({"module_version": module_version}), 200