#for running in /venv :
#     #!/venv/bin/python
import subprocess, requests, re
import huggingface_hub
import os, sys, time
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
#from decimal import Decimal

# FLOW:
# * if debug: 
#    run bash
# * if training:
#   1. start api server - currently done separately via gunicorn 
#   2. login to hf
#   3. update the dataset file 
#   4. update the trainer args file 
#   5. start the training command in screen 
#   6. check that screen was done and check the logs for success
#   7. once finished export the model to a separate folder - no need for export as we only use adapters so we just upload
#   8. create card.json in the model folder
#   9. upload the model to hf 

#Jinja template files
DATASET_FILE_TEMPLATE="dataset_info.json.j2"
ARGS_TEMPLATE="trainer_args.yaml.j2"
CARD_TEMPALTE="model_card.json.j2"
DATASET_FILE="/app/LLaMA-Factory/data/dataset_info.json"
ARGS_FILE="/app/LLaMA-Factory/trainer_args.yaml"
CARD_FILE="card.json"
SCREEN_LOG_FILE="/app/screen.log"

#LLama argumetns
current_date=datetime.today().strftime('%Y-%b-%d')
dataset_name=os.environ.get("DATASET", "test").strip()
project_name=os.environ.get("PROJECT","test").strip()
num_train_epochs=f"epoch{os.environ.get('NUM_TRAIN_EPOCHS', '0').strip()}"
#model_name=os.environ["DATASET"]   #.replace("_","-").replace(".","-").replace("--","-") + "-" + current_date   #'_', '.', '--' is not valid in model names in hugging face
project_name = re.sub(r'[^a-zA-Z0-9-]', '-', project_name).strip('-')
#model_name = f"{model_name}-{os.environ.get('NUM_TRAIN_EPOCHS','')}-{current_date}"
model_name_parts = [project_name, num_train_epochs, current_date]
model_name = '-'.join(filter(None, map(str.strip, model_name_parts))).strip('-')

training_done_message="Training completed. Do not forget to share your model on huggingface.co/models =)"
model_output_folder="/app/LLaMA-Factory/saves/test"
session_name="training"



#hugging face functions
def hf_login():
    print("logging in to hugging face using predefined token")
    huggingface_hub.login(os.environ['token']) # might be unnecessary  

def hf_upload():
    #this function uploads the whole results folder to hugging face 
    #note that it will upload to the space according to the token used
    print("uploading fine-tuned model to hugging face")
    api = huggingface_hub.HfApi()
    api.upload_large_folder(repo_id=model_name, repo_type="model",folder_path=model_output_folder)

#General functions

def run_command(cmd):
    print("running command: {}".format(cmd))
    try:
        p = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True,text=True)
        output,error = p.communicate()
        if p.returncode != 0:
            print("command failed")
            print("****** ERROR ******")
            print(error)        
        return output
    except Exception as e:
        print("Command execution failed: {}".format(e))

def url_query(url,headers):
    response = requests.get(url, headers=headers)
    return response.json()    
    
def update_file(file, data):
    with open(file,'w') as f:
       f.write(data)

def update_jinja(template_file,output_file):
    print("updating arguments file {}".format(output_file))
    env_vars = os.environ
    env = Environment(loader = FileSystemLoader('/app/templates'))
    template = env.get_template(template_file)
    output = template.render(env=env_vars)
    update_file(output_file,output)

# def convert_scientific_to_decimal(num):
#     num=Decimal(num)
#     return num

# def run_command_screen(cmd):
#     print("running command {}".format(cmd))
#     proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
#     statusProc = subprocess.run('screen -ls', shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
#     statusString = statusProc.stdout.decode('ascii')
#     print(statusString)


#Training specific functions
def check_training_process():
    while True:
      statusProc = subprocess.run('screen -ls', shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
      statusString = statusProc.stdout.decode('ascii')
      #if statusString and "No Sockets found" not in statusString:
      if not statusString or "No Sockets found" in statusString:
        print("screen is not running")
        break
      print("{}: training still in progress".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
      time.sleep(300)

def get_last_line_from_log():
    #this function gets the last line from the screen log       
    with open(SCREEN_LOG_FILE,'rb') as f:
        f.seek(-2, os.SEEK_END)
        while f.read(1) != b'\n':
            f.seek(-2, os.SEEK_CUR) 
        print(f.readline().decode())

def check_train_log():
    print("checking fine tuning process log")
    with open(SCREEN_LOG_FILE,) as f:
        if training_done_message in f.read():
           print("training completed successfuly")
        else:
           print("training didn't finish successfuly, please check the process log at {}".format(SCREEN_LOG_FILE))
           sys.exit()

def run_training():
    print("Starting LlamaFactory model fine-tuning...")
    cmd = 'screen -L -Logfile {0} -dmS {1} llamafactory-cli train /app/LLaMA-Factory/trainer_args.yaml'.format(SCREEN_LOG_FILE,session_name)
    run_command(cmd)
    check_training_process()
    check_train_log()

def get_cutoff_length():
    output = run_command("python /app/LLaMA-Factory/dataset-token-size-distribution.py") 
    lines = output.splitlines()
    for line in lines:
        if 'Max_tokens' in line.strip():
            max_tokens = line.replace('Max_tokens:','').strip()
            print("max tokens value is: {}".format(max_tokens))
            return max_tokens

def get_save_steps():
    #This function calculates the save_steps for the llamafactory-cli trani command
    #the formula is: 
    # dataset_size/batch_size 
    #where:
    #batch_size = gradient_accumulation_steps * per_device_train_batch_size * num of GPUs
    headers = {'Authorization': 'Bearer {}'.format(os.environ['token'])}
    hf_size_url = "https://datasets-server.huggingface.co/size?dataset={}".format(os.environ["DATASET_REPO"])
    print('getting dataset size')
    output = url_query(hf_size_url,headers)
    for s in output["size"]["splits"]:
        if s["split"] == "train":
            trainsplit = s
    dataset_size = trainsplit['num_rows']  #$.size.splits[?(@.split=='train')].num_rows
    os.environ["DATASET_SIZE"] = str(dataset_size)
    batch_size = int(os.environ['GRADIENT_ACCUMULATION_STEPS']) * int(os.environ['PER_DEVICE_TRAIN_BATCH_SIZE']) * int(os.environ['GPU_NUM'])
    os.environ["BATCH_SIZE"] = str(batch_size)
    print(f"dataset_size: {dataset_size}")
    print(f"batch_size: {batch_size}")
    print("calculating save steps")
    save_steps = dataset_size / batch_size
    print(f"save steps {save_steps}")
    return save_steps
    
def main():
    mode = os.getenv("MODE", "training").lower()  # Default to "training" if MODE is not set
    if mode == "training":
        print("Running in training mode...")
        print("Updating LlamaFactory dataset info file...")
        update_jinja(DATASET_FILE_TEMPLATE,DATASET_FILE)
        os.environ["CUTOFF_LEN"] = str(get_cutoff_length())
        os.environ["SAVE_STEPS"] = str(int(get_save_steps()))
        os.environ["MODEL_NAME"] = str(model_name)
        print("save_steps: {}".format(os.environ["SAVE_STEPS"]))
        update_jinja(ARGS_TEMPLATE,ARGS_FILE)
        hf_login()
        run_training()
        #run_command_screen('screen -L -Logfile /app/train-screen.log -dmS {} llamafactory-cli train /app/LLaMA-Factory/trainer_args.yaml'.format(session_name))
        #create the card.json file
        #check_training_process()
        update_jinja(CARD_TEMPALTE,os.path.join(model_output_folder,CARD_FILE))
        hf_upload()
        print("training process is done, logs are at {}".format(SCREEN_LOG_FILE))
        print("the model can be found at {}".format("https://huggingface.co/taguser/" + model_name))
        time.sleep(300)
        sys.exit(0)
        #subprocess.call(["/bin/bash"])
        #sys.exit(0)
    elif mode == "debug":
        print("Entering debug mode (bash)...")
        subprocess.call(["/bin/bash"])
    else:
        print("Unknown MODE: {}. Exiting.".format(mode))
        sys.exit(1)

if __name__ == "__main__":
    main()