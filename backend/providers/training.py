from pymongo import MongoClient
from urllib.parse import urlparse #temporary till the model location is in the DB
from be_utils.helm import HELM, HELMCommands
from be_utils.utils import json_to_yaml, helm_response
from be_utils.db.db import as_objectId, mongo, Collections
from providers.hf import HuggingFaceUtils
import json
from config.configParams import config

db_url = config.get('dpr', 'mongo_ext_addr')
client = MongoClient(f"mongodb://{db_url}:27017")
training_db = client["training"]

@mongo
def training_helm_install(user_data):    
    # create the new process id in the BE db and then use it for the training DB 
    result = Collections.by_name('training').insert_one({})  
    process_id = str(result.inserted_id)
    
    # add db info to the yaml file
    user_data["ConfigMap"]["data"]["DB_URL"] = db_url
    user_data["ConfigMap"]["data"]["DB_NAME"] = "training"
    user_data["ConfigMap"]["data"]["DB_COLLECTION_NAME"] = "stats"
    user_data["ConfigMap"]["data"]["PROCESS_ID"] = process_id
    file_path, yaml_data = json_to_yaml(user_data)

    api_url = yaml_data["api_url"]
    data = yaml_data["ConfigMapTrainerArgs"]["data"]
    namespace = yaml_data["Global"]["namespace"] 
    deployment_name = yaml_data["Global"]["deployment_name"] 
        
    helm = HELM(api_url=api_url, namespace=namespace)
    helm_install = helm.run_helm_command(HELMCommands.INSTALL, deployment_name=deployment_name, values=file_path, namespace=namespace, pipeline="training")

    if helm_install["status"] == "success":
        data = json.loads(helm_install["data"])
        data["is_deleted"] = False
        data["status"] = "RUNNING"
        data.pop("manifest", None)
        data.pop("chart", None)

        Collections.by_name('training').update_one({"_id": result.inserted_id}, {"$set": data})

        helm_install.pop("data", None)
        helm_install["_id"] = process_id  
    else:
        Collections.by_name('training').delete_one({"_id": result.inserted_id})     

    return helm_install


@mongo
def training_helm_uninstall(id, status):
    creds = get_config_creds(id)
    if creds:
        helm = HELM(api_url=creds["api_url"], namespace=creds["namespace"])
        helm_uninstall = helm.run_helm_command(HELMCommands.UNINSTALL, deployment_name=creds["deployment_name"], namespace=creds["namespace"])
    
        if helm_uninstall["status"] == "success":
            training_db["steplogs"].update_one({"_id": id}, {"$set": {"status": status}})
            Collections.by_name('training').update_one({"_id": as_objectId(id)}, {"$set": {"uninstalled": True, "status": status}, "$currentDate": {"finished_running": True}})    
            try:
                training_db["training"].drop() 
                print("Successfully dropped training collection from training database.")
            except Exception as e:
                print(f"Error dropping training collection: {e}")
        return helm_uninstall

@mongo
def get_config_creds(id):
    config_data = Collections.by_name('training').find_one({'_id': as_objectId(id)})
    if config_data:
        config_file = config_data.get("config", {})
        return {
            "namespace": config_file.get("Global").get("namespace"),
            "deployment_name": config_file.get("Global").get("deployment_name"),
            "api_url": config_file.get("api_url")
        }
    return {}

def create_json_format(user_data):
    def extract_config(data, exclude_keys=None):
        exclude_keys = exclude_keys or []
        return {k: data.get(k, "") for k in data if k not in exclude_keys}

    input_selection = extract_config(user_data["inputSelection"])
    global_config = extract_config(user_data["Global"], exclude_keys=["api_url"])
    training_config = extract_config(user_data["training"], exclude_keys=["GPU_NUM", "PROJECT"])

    api_option = user_data["Global"]["cluster"]

    json_output = {
        "api_url": config.get("dpr", "preprod_cluster" if api_option == "Preproduction Cluster" else "prod_cluster"),
        "Global": global_config,
        "ConfigMap": {
            "data": {
                "GPU_NUM": user_data["training"].get("GPU_NUM", ""),
                "PROJECT": user_data["training"].get("PROJECT", ""),
                "DATASET_REPO": input_selection.get("DATASET_REPO", ""),
                "DATASET_FILE_NAME": input_selection.get("DATASET_FILE_NAME", ""),
            }
        },
        "ConfigMapTrainerArgs": {
            "data": {**training_config, "QUANTIZATION": str(training_config.get("QUANTIZATION", "True"))}
        }
    }

    return json_output

@mongo
def get_step_statuses(doc_id: str):
    """
    Return the status of the currently running or last completed step.
    If a step is currently running, return its mapped status.
    Otherwise, return "done" if all steps are done.
    """
    deployment = training_db['steplogs'].find_one({"_id": doc_id}, {"steps": 1})
    if not deployment:
        return "initializing"
    
    step_status_map = {
        "prepare_files": "preparing",
        "finetune_model": "training",
        "update_card_file": "updating",
        "upload_to_huggingface": "uploading to Hugging Face"
    }

    steps = deployment.get("steps", {})
    for step_name, times in steps.items():
        if times["start"] and not times["end"]:
            return step_status_map.get(step_name, "unknown")

    update_training_data(doc_id)
    return "done"

@mongo
def update_training_data(training_id: str):
    '''
    Creates a trained models collection if doesn't exist
    then creates a document for the trained model from the current finished training
    updates the document with the card.json info and a list of all the files in the repository
    '''
    model_training_data = training_db["steplogs"].find_one({"_id": training_id}, {"model_location": 1})
    model_url = model_training_data["model_location"]
    url = urlparse(model_url)
    model_location = url.path.lstrip('/')
    hf_instance = HuggingFaceUtils()
    model_file_list = hf_instance.list_repo_files(model_location)
    hf_instance.download_file(model_location, "card.json")
    with open("/tmp/card.json","r") as f:
        model_data =f.read()
    trained_model_data = json.loads(model_data)
    set_data = {"training_id": training_id, "model_location": model_url, "model_file_list": model_file_list, "status": "DONE", "model_data": trained_model_data}
    Collections.by_name('training').update_one({"_id": as_objectId(training_id)}, {"$set": set_data})
    

@mongo
def get_running_deployment():
    deployment = Collections.by_name('training').find_one({"status": "RUNNING"})
    
    return {"id": (str(deployment["_id"])),
            "name": deployment["name"],
            "config": deployment["config"],
            "startTime": deployment["info"]["first_deployed"]} if deployment else {}

@mongo
def get_datasets_for_training():
    datasets = Collections.by_name('dpr').find({'status': "DONE"})
    
    dataset_list = []
    for dataset in datasets:
        repo = dataset["config"]["global"]["promptlab_env"]["OUTPUT_DATASET_REPO"]
        file = dataset["config"]["global"]["promptlab_env"]["OUTPUT_DATASET_FILE_NAME"]
        if repo and file:
            dataset_list.append({"repo": repo, "file": file + ".json"})

    return dataset_list

@mongo
def get_trained_models_data():
    """
    Return all documents from training.stepslogs where status == "DONE",
    and join each with its corresponding data.
    If id get only specific document with the crresponding id
    """
    stepslogs = training_db["steplogs"].find({"status": "DONE"}, {"model_location": 1, "repo_path": 1})

    results = []

    for stepslog in stepslogs:
        training_doc = Collections.by_name("training").find({"_id": as_objectId(stepslog["_id"])}, {"name": 1, "config": 1, "model_file_list": 1, "model_data": 1, "registered": 1})

        for doc in training_doc:
            results.append({
                "id": stepslog["_id"],
                "name": doc.get("name", ""),
                "huggingfaceUrl": stepslog.get("model_location"),
                "repoPath": stepslog.get("repo_path"),
                "modelFileList": doc.get("model_file_list", []),
                "finetuneSteps": doc.get("model_data").get("finetune_steps")[0] if doc.get("model_data").get("finetune_steps", []) else [],
                "config": doc.get("config", {}),
                "registered": doc.get("registered", False)
            })
    return results


@mongo
def register_model(id):
    result = Collections.by_name('training').update_one({"_id": as_objectId(id)}, {"$set": {"registered": True}})
    return "registered" if result.modified_count > 0 else "not registered"

@mongo
def check_training_progress():
    """
    Check the progress of the training process.
    """
    installed = Collections.by_name('training').find({"uninstalled": {"$ne": True}, "status": "DONE"})
    for installation in installed:
        deployment_id = installation.get("_id")
        training_helm_uninstall(deployment_id, "DONE")
