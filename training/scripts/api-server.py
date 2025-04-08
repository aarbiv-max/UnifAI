from flask import Flask, jsonify
import subprocess,os

app = Flask(__name__)

def run_command(command):
    try:
        output = subprocess.check_output(command, shell=True).decode().strip()
    except subprocess.CalledProcessError as e:
        output = str(e)
    return output

@app.route('/api/test', methods=['GET'])
def get_nvitop():
    return jsonify("This is a test endpoint")

@app.route('/api/nvitop/', methods=['GET'])
def get_nvitop():
    output = run_command("nvitop")
    return jsonify({"nvitop_output": output})

@app.route('/api/training/status', methods=['GET'])
def get_last_line_from_log():
    SCREEN_LOG_FILE="/app/screen.log"
    #this function gets the last line from the screen log       
    with open(SCREEN_LOG_FILE,'rb') as f:
        f.seek(-2, os.SEEK_END)
        while f.read(1) != b'\n':
            f.seek(-2, os.SEEK_CUR) 
        #print(f.readline().decode())
        output=f.readline().decode()
    return jsonify({"log output": output})

@app.route('/api/folder/<path:folder>', methods=['GET'])
def get_folder_status(folder):
    output = run_command(f"ls -lia {folder}")
    return jsonify({"folder_ls_output": output})

if __name__ == '__main__':
    from gunicorn.app.wsgiapp import run
    run(debug=True, host='0.0.0.0', port=8080)
    #app.run(debug=True, host='0.0.0.0', port=8080)

