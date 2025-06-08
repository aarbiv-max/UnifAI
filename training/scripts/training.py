import os, sys, re
from datetime import datetime
from helpers.hf import HF
from helpers.general_utils import update_jinja, get_dataset_info, get_save_steps, run_command, follow_log_while_screen_active
from helpers.logger import setup_mongo_logger, StepLogger

# FLOW:
# * if debug: 
#    run bash
# * if training:
#   1. start api server - currently done separately via gunicorn 
#   2. login to hf  -done automatically
#   3. update the dataset file 
#   4. update the trainer args file 
#   5. start the training command in screen 
#   6. check that screen was done and check the logs for success
#   7. once finished export the model to a separate folder - no need for export as we only use adapters so we just upload
#   8. create card.json in the model folder
#   9. upload the model to hf 

steps = [
"prepare_files",
"finetune_model",
"update_card_file",
"upload_to_huggingface",
]
#huggingface args
hf_base_url = "https://huggingface.co"
hf_username="taguser"
hf_space="cia-tools"
hf = HF()

#Jinja template files
TEMPLATES_DIR='/app/templates'
DATASET_FILE_TEMPLATE="dataset_info.json.j2"
ARGS_TEMPLATE="trainer_args.yaml.j2"
CARD_TEMPALTE="model_card.json.j2"
DATASET_FILE="/app/LLaMA-Factory/data/dataset_info.json"
ARGS_FILE="/app/LLaMA-Factory/trainer_args.yaml"
CARD_FILE="card.json"
SCREEN_LOG_FILE="/app/screen.log"

mongo_url=os.environ["DB_URL"]
db_name = os.environ["DB_NAME"]
collection_name = os.environ["DB_COLLECTION_NAME"]
logger = setup_mongo_logger("genie_training", mongo_url, db_name, collection_name)
process_id = os.environ['PROCESS_ID']
steplogger = StepLogger(process_id)
steplogger.init_status()

#Llama / training args
current_date=datetime.today().strftime('%Y-%b-%d')
dataset_name=os.environ.get("DATASET", "test").strip()
project_name=os.environ.get("PROJECT","test").strip()
num_train_epochs=f"epoch{os.environ.get('NUM_TRAIN_EPOCHS', '0').strip()}"
project_name = re.sub(r'[^a-zA-Z0-9-]', '-', project_name).strip('-')
model_name_parts = [project_name, num_train_epochs, current_date]
model_name = '-'.join(filter(None, map(str.strip, model_name_parts))).strip('-')
model_repo = os.path.join(hf_username, model_name)
model_location = os.path.join(hf_base_url, model_repo)
model_output_folder="/app/LLaMA-Factory/saves/test"

def run_training():
    session_name = "training"
    print("Starting LlamaFactory model fine-tuning...")
    cmd = "screen -L -Logfile {0} -dmS {1} llamafactory-cli train /app/LLaMA-Factory/trainer_args.yaml".format(SCREEN_LOG_FILE,session_name)
    run_command(cmd)
    follow_log_while_screen_active(SCREEN_LOG_FILE, session_name, logger)


def main():
    # mode = os.getenv("MODE", "training").lower()
    # if mode == "debug":
    #     update_jinja(DATASET_FILE_TEMPLATE,DATASET_FILE)
    # else:
        # here we want to create a status RUNNING
    try:
        steplogger.mark_start('prepare_files')
        update_jinja(DATASET_FILE_TEMPLATE,DATASET_FILE)
        os.environ["CUTOFF_LEN"], os.environ["DATASET_SIZE"]  = get_dataset_info()
        logger.debug(os.environ["CUTOFF_LEN"])
        logger.debug(os.environ["DATASET_SIZE"])
        os.environ["SAVE_STEPS"] = str(int(get_save_steps()))
        os.environ["MODEL_NAME"] = str(model_name)
        os.environ["TRAINED_MODEL_REPO"] = model_repo
        print("save_steps: {}".format(os.environ["SAVE_STEPS"]))
        logger.info("Creating training argument file")
        update_jinja(ARGS_TEMPLATE,ARGS_FILE)
        logger.info("finished creating training argument file")
        steplogger.mark_end('prepare_files')
        steplogger.mark_start('finetune_model')
        run_training()
        steplogger.mark_end('finetune_model')

        steplogger.mark_start('update_card_file')
        update_jinja(CARD_TEMPALTE,os.path.join(model_output_folder,CARD_FILE))
        steplogger.mark_end('update_card_file')

        steplogger.mark_start('upload_to_huggingface')
        hf.large_folder_upload(model_name,model_output_folder)
        steplogger.mark_end('upload_to_huggingface')

        steplogger.update_document("status", "DONE")
        steplogger.update_document("repo_path", model_repo)
        steplogger.update_document("model_location", model_location)
        
        # here we want to change the status to DONE
        # add the huggingface url as a new field model_loaction
        # call training_helm_uninstall(id=process_id, status="DONE")
        logger.info("the model can be found at {}".format(model_location))
    except Exception as e:
        logger.error("training failed")
        logger.error(e)


if __name__ == "__main__":
     sys.exit(main())
