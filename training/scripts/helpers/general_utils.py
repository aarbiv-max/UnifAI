import subprocess
import requests
import os
import time
import sys
from datetime import datetime
from jinja2 import Environment, FileSystemLoader


def run_command(cmd):
    print("running command: {}".format(cmd))
    try:
        p = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True,text=True)
        output,error = p.communicate()
        if p.returncode != 0:
            print("command failed")
            print("****** ERROR ******")
            print(error) 
        print("command started successfully") 
        print(output)
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

def get_dataset_info():
    output = run_command("python /app/LLaMA-Factory/dataset-token-size-distribution.py") 
    lines = output.splitlines()
    #get the cutoff_length (also named context length)
    for line in lines:
        if 'Max_tokens' in line.strip():
            max_tokens = str(line.replace('Max_tokens:','').strip())
            print("max tokens value is: {}".format(max_tokens))
        elif 'Dataset_size' in line.strip():
            dataset_size = str(line.replace('Dataset_size:',''))
    return max_tokens, dataset_size

def get_save_steps():
    #This function calculates the save_steps for the llamafactory-cli trani command
    #the formula is: 
    # dataset_size/batch_size 
    #where:
    #batch_size = gradient_accumulation_steps * per_device_train_batch_size * num of GPUs
    dataset_size = int(os.environ['DATASET_SIZE'])
    batch_size = int(os.environ['GRADIENT_ACCUMULATION_STEPS']) * int(os.environ['PER_DEVICE_TRAIN_BATCH_SIZE']) * int(os.environ['GPU_NUM'])
    os.environ["BATCH_SIZE"] = str(batch_size)
    print(f"dataset_size: {dataset_size}")
    print(f"batch_size: {batch_size}")
    print("calculating save steps")
    save_steps = dataset_size / batch_size
    print(f"save steps {save_steps}")
    return save_steps

def get_last_line_from_log(file):
    #this function gets the last line from the screen log       
    with open(file,'rb') as f:
        f.seek(-2, os.SEEK_END)
        while f.read(1) != b'\n':
            f.seek(-2, os.SEEK_CUR) 
        print(f.readline().decode())

#Training specific functions
def check_training_process():
    '''
    check if screen is still active in the system, if so this means that the training is still ongoing
    '''
    while True:
      statusProc = subprocess.run('screen -ls', shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
      statusString = statusProc.stdout.decode('ascii')
      #if statusString and "No Sockets found" not in statusString:
      if not statusString or "No Sockets found" in statusString:
        print("screen is not running")
        break
      print("{}: training still in progress".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
      time.sleep(300)

def check_train_log(file):
    '''
    check the training log for the specific fininshed message, this can (and should) changed into a more general function to look for a text in file and return true/false
    '''
    training_done_message="Training completed. Do not forget to share your model on huggingface.co/models =)"
    print("checking fine tuning process log")
    with open(file,) as f:
        if training_done_message in f.read():
           print("training completed successfuly")
        else:
           print("training didn't finish successfuly, please check the process log at {}".format(file))
           sys.exit()

def is_screen_alive(session_name):
    """Check if a given screen session is active."""
    result = subprocess.run('screen -ls', shell=True, stdout=subprocess.PIPE)
    return session_name in result.stdout.decode('utf-8')

def is_file_exist(file):
    """Check if a given file path exists."""
    exist = os.path.isfile(file)
    return exist
 
def follow_log_while_screen_active(log_path, session_name, logger):
    """Tail the log file and log it to MongoDB while screen session is running."""
    while not is_file_exist(log_path):
        print("waiting for log file to be created")
        time.sleep(1)
    print(f"following log of screen {session_name}")
    with open(log_path, 'r') as f:
        f.seek(0, 2)  # Start at end of file
        while is_screen_alive(session_name):
            line = f.readline()
            if not line:
                time.sleep(1)
                continue
            logger.info(line.strip())
        logger.info("Screen session '{}' has ended. Stopping log tail.".format(session_name))