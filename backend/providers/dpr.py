from pymongo import MongoClient
from be_utils.helm import HELM, HELMCommands
from be_utils.utils import json_to_yaml, helm_response
from be_utils.db.db import mongo, Collections
import json
from bson import ObjectId
from config.configParams import config
            
client = MongoClient(f"mongodb://{config.get('dpr', 'mongo_ext_addr')}:27017")
promptlab_db = client["promptLab"]

@mongo
def dpr_helm_install(user_data):
    if list(get_running_deployments()):
        return helm_response(False, "Another installation is currently running, please wait before starting a new one.")  
    
    
    result = Collections.by_name('dpr').insert_one({})  
    process_id = str(result.inserted_id)
    user_data["global"]["process_id"] = process_id  
    user_data["global"]["connection"] = config.get("dpr", "mongo_ext_addr")
    user_data["global"]["hf_token"] = config.get("hf", "HF_TOKEN")

    file_path, yaml_data = json_to_yaml(user_data)

    deployment_name = yaml_data.get("global", {}).get("deployment_name", "")
    hf_token = yaml_data.get("global", {}).get("hf_token", "")
    api_url = yaml_data.get("global", {}).get("api_url", "")
    namespace = yaml_data.get("global", {}).get("namespace", "")

    helm = HELM(api_url=api_url, namespace=namespace)
    helm_install = helm.run_helm_command(HELMCommands.INSTALL, deployment_name=deployment_name, values=file_path, namespace=namespace, pipeline="pre_training_helm")

    if helm_install["status"] == "success":
        data = json.loads(helm_install["data"])
        data["is_deleted"] = False
        data.pop("manifest", None)
        data.pop("chart", None)

        Collections.by_name('dpr').update_one(
            {"_id": result.inserted_id},
            {"$set": data}
        )

        helm_install.pop("data", None)
        helm_install["_id"] = process_id  
    else:
        Collections.by_name('dpr').delete_one({"_id": result.inserted_id})

    return helm_install



# @mongo
# def helm_upgrade(user_data):

#     id = user_data["_id"]
#     helm_set_params = []

#     for key, value in user_data["global"].items():
#         helm_set_params.append(f"--set global.{key}={value}")

#     helm_set_params_str = " ".join(helm_set_params)

#     creds = get_config_creds(id)
#     if creds:
#         helm = HELM(api_url=creds["api_url"], namespace=creds["namespace"])
#         helm_upgrade = helm.run_helm_command(HELMCommands.UPGRADE, deployment_name=creds["deployment_name"], helm_set_params=helm_set_params_str, namespace=creds["namespace"])

#         if helm_upgrade["status"] == "success":
#             result = Collections.by_name('dpr').update_one(
#                 {"_id": ObjectId(id)},   
#                 {"$set": {f"config.global.{key}": value for key, value in user_data["global"].items()}}
#             )
#             if result.matched_count > 0:
#                 helm_upgrade["data"] = "upgrade dpr process completed"

#         return helm_upgrade

@mongo
def dpr_helm_uninstall(id, status):
    creds = get_config_creds(id)
    if creds:
        helm = HELM(api_url=creds["api_url"], namespace=creds["namespace"])
        helm_uninstall = helm.run_helm_command(HELMCommands.UNINSTALL, deployment_name=creds["deployment_name"], namespace=creds["namespace"])
        if helm_uninstall["status"] == "success":
            Collections.by_name('dpr').update_one({"_id": ObjectId(id)}, {"$set": {"status": status}, "$currentDate": {"finished_running": True}})
            try:
                promptlab_db["processedPrompts"].drop() 
                print("Successfully dropped processedPrompts collection from promptLab database.")
            except Exception as e:
                print(f"Error dropping processedPrompts collection: {e}")
                
        return helm_uninstall


@mongo
def get_promptlab_stats(id):
    result = promptlab_db["statistics"].find_one({"_id": ObjectId(id)}, {"_id": 0})
    return result

@mongo
def delete_dpr_deployment(id):
    """
    :return: list of deployments that are currently running (haven't been deleted from the db)
    """
    result = Collections.by_name('dpr').update_one({"_id": ObjectId(id)}, {"$set": {"is_deleted": True}})
    return result.modified_count

def get_config_creds(id):
    config_data = Collections.by_name('dpr').find_one({'_id': ObjectId(id)})
    if config_data:
        config = config_data.get("config", {}).get("global", {})
        return {
            "namespace": config.get("namespace"),
            "api_url": config.get("api_url"),
            "deployment_name": config_data.get("name"),
            "hf_token": config_data.get("hf_token"),
        }
    return {}

def create_json_format(user_data):
    def extract_config(data, exclude_keys=None):
        exclude_keys = exclude_keys or []
        return {k: data.get(k, "") for k in data if k not in exclude_keys}

    global_config = extract_config(user_data["global"], exclude_keys=["api_url"])
    file_env = extract_config(user_data["file"], exclude_keys=["combinedDataset"])
    promptlab_env = extract_config(user_data["promptLab"], exclude_keys=["vllm_orbiter_args", "OUTPUT_DATASET_FILE_NAME"])
    reviewer_env = extract_config(user_data["reviewer"]) if global_config.get("enable_reviewer") else {}

    output_dataset_filename = user_data["promptLab"].get("OUTPUT_DATASET_FILE_NAME", "")
    promptlab_env["OUTPUT_DATASET_FILE_NAME"] = output_dataset_filename if \
        output_dataset_filename.startswith("train-") else "train-" + output_dataset_filename
        
    api_option = user_data["global"]["api_url"]
    
    json_output = {
        "global": {
            **global_config,
            "api_url": config.get("dpr", "preprod_cluster" if api_option == "Preproduction Cluster" else "prod_cluster"),
            "orbiter_model_hf_id": user_data["promptLab"].get("PROMPT_LAB_MODEL_HF_ID", ""),
            "promptlab_env": {**promptlab_env, **file_env},
        }
    }
    
    if global_config.get("enable_reviewer", True):
        json_output["global"].update({
            "reviewer_model_hf_id": reviewer_env.get("REVIEWER_MODEL_HF_ID", ""),
            "reviewer_env": reviewer_env,
        })
    
    return json_output

@mongo
def get_not_deleted_deployments():
    """
    :return: list of deployments that are currently running (haven't been deleted from the db)
    """
    deployments = Collections.by_name('dpr').find(
        {"is_deleted": False},
        {"_id": 1, "name": 1, "config": 1, "info.first_deployed": 1, "finished_running": 1, "status": 1}
    )
    deployments_with_stats = []

    for deployment in deployments:
        stats = get_promptlab_stats(deployment["_id"])

        deployments_with_stats.append({
            "_id": str(deployment["_id"]),
            "name": deployment.get("name"),
            "config": deployment.get("config", {}),
            "first_deployed": deployment.get("info", {}).get("first_deployed", "N/A"),
            "finished_running": deployment.get("finished_running", ""),
            "status": deployment.get("status", "N/A"),
            "stats": stats or {}
        })

    return deployments_with_stats

@mongo
def get_running_deployments():
    deployments = Collections.by_name('dpr').find(
        {"status": {"$nin": ["UNINSTALLED", "DONE"]}}
    )
    return deployments

@mongo
def celery_check_dpr_progress():
    """
    Fetches Helm stats for all currently running deployments.
    """
    print("Starting fetch stats for dpr")
    running_deployments = get_running_deployments()
    for deployment in running_deployments:
        id = deployment["_id"]
        mongodb_stats = get_promptlab_stats(id)
        if mongodb_stats:
            no_remaining_prompts = mongodb_stats['prompts_failed'] + mongodb_stats['prompts_pass'] == mongodb_stats['number_of_prompts']
            if no_remaining_prompts and mongodb_stats.get('exported', False):
                dpr_helm_uninstall(id, "DONE")
                
@mongo
def get_dataset_list():
    """
    :return: list of dicts with repo and file for all deployments marked as done
    """
    deployments = Collections.by_name('forms').find(
        {"status": 'done'}
    )

    dataset_list = []
    for deployment in deployments:
        repo = deployment.get('hf_repo')
        file = deployment.get('hf_file')
        if repo and file:
            dataset_list.append({ "repo": repo, "file": file })
    return dataset_list
