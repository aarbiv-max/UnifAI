from flask import Blueprint, jsonify
from webargs import fields
from be_utils.utils import json_response
from providers.training import create_json_format, get_datasets_for_training, get_step_statuses, get_running_deployment, get_trained_models_data, register_model, training_helm_uninstall, training_helm_install
from helpers.apiargs import from_query, from_body
from shared.fields import FormFields

training_bp = Blueprint("training", __name__)


@training_bp.route("/uninstall", methods=["POST"])
@from_body({
    "id":        fields.Str(required=True, data_key="id"),
    "status":    fields.Str(required=True, data_key="status")
})
def uninstall(id, status):
    uninstall = training_helm_uninstall(id, status)
    return jsonify({"status": "success", "response": uninstall}), 200


@training_bp.route("/install", methods=["POST"])
@from_body({
    "data": fields.Dict(required=True),
    "mode": fields.String(required=True)
})
def deploy(data, mode):
    helm_json = create_json_format(data) if mode == "create" else data['jsonFile']
    install = training_helm_install(helm_json) 
    return (jsonify(install), 200) if install.get("status") == "success" else (jsonify(install), 500)

@training_bp.route("/runningDeployment", methods=["GET"])
def get_displayed_instance():
    try:
        result = get_running_deployment()
        return jsonify({"status": "success", "response": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@training_bp.route("/availableDatasets", methods=["GET"])
def get_available_datasets():
    try:
        result = get_datasets_for_training()
        return jsonify({"status": "success", "response": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@training_bp.route("/getStatus", methods=["GET"])
@from_query({"id": fields.Str(load_default='', data_key="formId")})
def retrieve_form_status(id):
    form_status = get_step_statuses(id)
    if form_status is None:
        return json_response({"error": "Form not found"}), 404
    return json_response({"status": form_status})

@training_bp.route("/trainedModels", methods=["GET"])
def get_trained_models():
    try:
        result = get_trained_models_data()
        return jsonify({"status": "success", "response": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@training_bp.route("/register", methods=["POST"])
@from_body({
    "id":             fields.Str(required=True, data_key="id")
})
def register(id):
    result = register_model(id)
    return jsonify({"status": "success", "response": result}), 200