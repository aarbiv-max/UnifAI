from flask import Blueprint, jsonify, make_response,request
from webargs import fields
from providers.dpr import create_json_format, delete_deployment, get_not_deleted_deployments, get_json_file_config, get_promptlab_stats, helm_status, helm_uninstall, helm_install, helm_upgrade#, helm_route #helm_metrics
from helpers.apiargs import from_query, from_body

dpr_bp = Blueprint("dpr", __name__)

@dpr_bp.route("/status", methods=["GET"])
@from_query({
    "id":        fields.Str(required=True, data_key="id")
})
def status(id):
    status = helm_status(id)
    return status


@dpr_bp.route("/uninstall", methods=["POST"])
@from_body({
    "id":        fields.Str(required=True, data_key="id"),
    "status":    fields.Str(required=True, data_key="status")
})
def uninstall(id, status):
    uninstall = helm_uninstall(id, status)
    return uninstall


@dpr_bp.route("/install", methods=["POST"])
@from_body({
    "data": fields.Dict(required=True),
    "mode": fields.String(required=True)
})
def deploy(data, mode):
    helm_json = create_json_format(data) if mode == "create" else data['jsonFile']
    ## user should provide a json structred based on this strcture:
    # {
    #     "global": {
    #         "api_url": "https://api.stc-ai-e1-pp.imap.p1.openshiftapps.com:6443",
    #         "deployment_name": "dpr",
    #         "namespace": "tag-ai--yhabushi-nb", 
    #         "enable_toleration": False,
    #         "multiple_gpu_per_pod": False,
    #         "number_of_gpu": 2,
    #         "vllm_orbiter_replica": 1, 
    #         "enable_reviewer": True,
    #         "vllm_reviewer_replica": 1, 
    #         "orbiter_replica": 1, 
    #         "reviewer_replica": 1, 
    #         "hf_token": "huggingface-token-secret", 
    #         "orbiter_model_hf_id": "meta-llama/Llama-3.1-8B-Instruct", 
    #         "reviewer_model_hf_id": "meta-llama/Llama-3.1-8B-Instruct", 
    #         "reviewer_env": {
    #             "REVIEWER_MODEL_HF_ID": "meta-llama/Llama-3.1-8B-Instruct", 
    #             "REVIEWER_MAX_GENERATION_LENGTH": 16000, 
    #             "REVIEWER_MAX_CONTEXT_LENGTH": 2048, 
    #             "REVIEWER_BATCH_SIZE": 8, 
    #             "REVIEWER_SCORE_THRESHOLD": 75
    #         },
    #         "promptlab_env": {
    #             "PROMPT_LAB_MODEL_HF_ID": "meta-llama/Llama-3.1-8B-Instruct", 
    #             "PROMPT_LAB_MAX_GENERATION_LENGTH": 2048, 
    #             "PROMPT_LAB_MAX_CONTEXT_LENGTH": 16000, 
    #             "PROMPT_LAB_BATCH_SIZE": 8, 
    #             "QUEUE_TARGET_SIZE": 16, 
    #             "TEMPLATE_AGENT": "TAG", 
    #             "TEMPLATE_NAME": "", 
    #             "TEMPLATE_TYPE": "robot_small", 
    #             "MAX_RETRY": 3, 
    #             "INPUT_DATASET_REPO": "cia-tools/ncs_parser", 
    #             "INPUT_DATASET_FILE_NAME": "NCS_TAG.json", 
    #             "OUTPUT_DATASET_REPO": "cia-tools/ncs_parser", 
    #             "OUTPUT_DATASET_FILE_NAME": "yh_output_NCS_TAG_robot_small",
    #             "TEMPLATE_PROJECT_CONTEXT": "", 
    #             "PROJECT_ID": "automation-tests-ncs", 
    #             "PROJECT_REPO": "https://scm.cci.nokia.net/cia/automation-tests-ncs",   
    #         }, 
    #     }
    # }
    install = helm_install(helm_json) 
    return (jsonify(install), 200) if install.get("status") == "success" else install

@dpr_bp.route("/upgrade", methods=["POST"])
def upgrade():
    # user_data={
    #     "_id" : "67a3cb8d76fcd974685cc60e",
    #     "global": {
    #         "vllm_reviewer_replica": 2, 
    #         "orbiter_replica": 2, 
    #         "reviewer_replica": 2, 
    #         "vllm_orbiter_replica": 2, 
    #     }
    # }
    user_data = request.get_json()
    upgrade = helm_upgrade(user_data)
    return upgrade

# @dpr_bp.route("/route", methods=["GET"])
# @from_query({
#     "id":        fields.Str(required=True, data_key="id")
# })
# def route(id):
#     route = helm_route(id)
#     return route

@dpr_bp.route("/delete", methods=["POST"])
@from_body({
    "id":        fields.Str(required=True, data_key="id")
})
def delete(id):
    result = delete_deployment(id)
    return {"data": result}

@dpr_bp.route("/getStats", methods=["GET"])
@from_query({
    "id":        fields.Str(required=True, data_key="id"),
})
def promptlab_stats(id):
    stats = get_promptlab_stats(id)
    return {"data": stats}

# @dpr_bp.route("/metrics", methods=["GET"])
# @from_query({
#     "id":        fields.Str(required=True, data_key="id"),
#     "name":      fields.Str(required=True, data_key="name")
# })
# def get_metrics(id, name):
#     metrics = helm_metrics(id, name)
#     return metrics

@dpr_bp.route("/displayDeployments", methods=["GET"])
def get_displayed_instances():
    try:
        result = get_not_deleted_deployments()
        return result
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@dpr_bp.route("/getConfigFile", methods=["GET"])
@from_query({
    "id":        fields.Str(required=True, data_key="id")
})
def get_config(id):
    try:
        result = get_json_file_config(id)
        return result
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500