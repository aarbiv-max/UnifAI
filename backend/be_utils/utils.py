from config.configParams import config_params
from subprocess import PIPE, Popen
import functools
import shutil
import ipaddress
import asyncio
import re
import tarfile
import os
import sys
import math
import time
import json
from queue import Queue, Empty
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from bson.json_util import dumps, RELAXED_JSON_OPTIONS
from flask import Response
import json 
import yaml

def composed(*decs):
    def deco(f):
        for dec in reversed(decs):
            f = dec(f)
        return f

    return deco


def make_async(f):
    @functools.wraps(f)
    async def wrapper(*args, **kwargs):
        return await f(*args, **kwargs)

    return wrapper


def run_in_executor(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return inner


def run_once(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(*args, **kwargs)

    wrapper.has_run = False
    return wrapper


async def run_tasks_async(tasks):
    """
    Run tasks in async way
    :param tasks: array of tasks - async functions
    :return: array of the results of the tasks in the same order they were in the tasks array
    """
    return await asyncio.gather(*tasks)


def shell_exec(cmdline):
    """
    Run a shell command using shell and pipe and returns the output and return code.
    :param cmdline: command line to be executed
    :return:
    @:param rc : return code
    @:param stdout: output to stdout of the command
    """
    proc = Popen(cmdline, shell=True, stdout=PIPE, universal_newlines=True)
    stdout = proc.communicate()[0]
    rc = proc.returncode
    return rc, stdout


def is_equal(name, compared_to):
    """
    :param name:
            1- normal string
            2- start with p which means prefix ex. p:name
            3- start with s which mean suffix ex. s:name
    :param compared_to: string compare name to
    :return:
    """
    if not name:
        return False
    compared_to = compared_to.lower()
    s_name = name.strip().split(':')
    if len(s_name) > 1:
        compare_type = s_name[0].lower()
        name_to_compare = s_name[1].lower()
        if compare_type == 'r':
            return True if re.match(r"{}".format(name_to_compare), compared_to) else False
        elif compare_type == 'p':
            return True if compared_to.startswith(name_to_compare) else False
        elif compare_type == 's':
            return True if compared_to.endswith(name_to_compare) else False
        else:
            pass
    else:
        return True if name.lower() == compared_to.lower() else False


def match_template(names, compared_to):
    names = names.split(',')
    for name in names:
        if is_equal(name, compared_to):
            return True
    return False


def add_string_regex_symbol(string, symbol):
    if string:
        ret = []
        for elem in string.split(','):
            if not elem.strip().startswith(symbol):
                ret.append('{}{}'.format(symbol, elem.strip()))
            else:
                ret.append(elem.strip())
        ret = ','.join(ret)
        return ret
    else:
        return string


def parse_k8s_command(output):
    """

    :param output: output of k8s normal command
    :return: list that contains lists, every element in the list is as in the line of output the command
    example:
    -----------------------------------input------------------------------------------------------------
    NAMESPACE           NAME                                   READY   UP-TO-DATE   AVAILABLE   AGE
    gatekeeper-system   gatekeeper-audit                       1/1     1            1           40d
    -----------------------------------output-----------------------------------------------------------
    [['NAMESPACE', 'NAME', 'READY', 'UP-TO-DATE', 'AVAILABLE', 'AGE'],
    ['gatekeeper-system', 'gatekeeper-audit', '1/1', '1', '1', '40d']]

    """
    return [[elem for elem in line.split(' ') if elem.strip()] for line in output.split('\n') if
            line.strip()]


async def run_client(client, clients_data):
    """
    tasks that runs client on agents
    :param clients_data: clients_data[destination_ip] :{
                                                        'dest_port': 8760,
                                                        'args': [],
                                                        'kwargs': {}
                                                        }
          args and kwargs are the arguments for the Client we want to run
    :param client: client to run
    :return:
    """
    tasks = []
    for dest_ip, data in clients_data.items():
        tasks.append(
            client(ip_address=dest_ip, port=data['dest_port'], host=data['name'], *data['args'], **data['kwargs'])())
    results = await run_tasks_async(tasks)
    return results


def recursive_iter(obj, keys=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from recursive_iter(v, keys + (k,))
    elif any(isinstance(obj, t) for t in (list, tuple)):
        for idx, item in enumerate(obj):
            yield from recursive_iter(item, keys + (idx,))
    else:
        yield keys, obj


def build_dict_from_path(original_dict, path, ret_dict):
    if len(path) == 1:
        pass


def make_json_paths(data, mongo_paths=True):
    """
    This function gets one sample, and builds the $group object for aggregation with mongo
    :param data:
    :param mongo_paths: make paths to mongo or normal json
    :return:
    """
    res = {}
    for keys, item in recursive_iter(data):
        keys = '.'.join([str(k) for k in keys])
        res[keys] = {'$push': f'${keys}'} if mongo_paths else keys

    return res


def get_agents_port():
    return config_params.get_param_by_env('agents_port')


def get_asc_port():
    return config_params.get_param_by_env('asc_port')


def get_be_ip():
    return os.environ["BE_IP_ADDRESS"]


def get_rabbitmq_port():
    return config_params.RABBITMQ_RABBITMQ_PORT


def make_tarfile(file_path, dest):
    output_filename = f'{os.path.join(dest, os.path.basename(file_path))}.tar.gz'
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(file_path, arcname=os.path.basename(file_path))
    return output_filename


def extract_tarfile(tar_to_extract, dest):
    with tarfile.open(tar_to_extract) as tar:
        tar.extractall(dest)
    return os.path.join(dest, os.path.basename(tar_to_extract).replace('.tar.gz', ''))


def mkdir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def delete_file(filename):
    if os.path.exists(filename):
        os.remove(filename)


def delete_dir(dirname):
    if os.path.exists(dirname):
        shutil.rmtree(dirname)


def retry(tries, delay=1, backoff=2):
    """Retries a function or method until it returns True.

    delay sets the initial delay in seconds, and backoff sets the factor by which
    the delay should lengthen after each failure. backoff must be greater than 1,
    or else it isn't really a backoff. tries must be at least 0, and delay
    greater than 0."""

    if backoff <= 1:
        raise ValueError("backoff must be greater than 1")

    tries = math.floor(tries)
    if tries < 0:
        raise ValueError("tries must be 0 or greater")

    if delay <= 0:
        raise ValueError("delay must be greater than 0")

    def deco_retry(f):
        @functools.wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay  # make mutable
            exception = None
            while mtries > 0:
                try:
                    rv = f(*args, **kwargs)  # first attempt
                except Exception as e:
                    rv = False
                    exception = e
                if rv:  # Done on success
                    return rv

                mtries -= 1  # consume an attempt
                time.sleep(mdelay)  # wait...
                mdelay *= backoff  # make future wait longer

            if exception:
                raise exception
            return False  # Ran out of tries :-(

        return f_retry  # true decorator -> decorated function

    return deco_retry  # @retry(arg[, ...]) -> true decorator


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


CHUNK_SIZE = 8192


def read_file_chunks(path, delete_file_after_read=True):
    with open(path, 'rb') as fd:
        while 1:
            buf = fd.read(CHUNK_SIZE)
            if buf:
                yield buf
            else:
                if delete_file_after_read:
                    delete_file(path)
                break


def stream_data(queue: Queue, timeout=None, stop_str='EOF', initiator=b''):
    try:
        yield initiator
        while True:
            if timeout:
                chunk = queue.get(timeout=10)  # Adjust timeout as needed
            else:
                chunk = queue.get()
            if chunk is None or chunk == stop_str:  # Assuming None is used to signal the end
                break
            yield chunk
    except Empty:
        pass  # Handle empty queue condition if necessary


def byte_to_mg_convertor(bytes):
    return round(bytes / math.pow(1024, 2))


def get_platform():
    return os.environ['PLATFORM']


def in_subnet(subnet, ip):
    return ipaddress.ip_address(ip) in ipaddress.ip_network(subnet)


def get_mysql_password():
    return os.environ['MYSQL_UNDERCLOUD_PASSWORD']


def get_root_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_scripts_dir_path():
    return os.path.join(get_root_dir(), 'scripts')


class change_dir(object):
    """Sets the cwd within the context

    Args:
        path (Path): The path to the cwd
    """

    def __init__(self, path: Path):
        self.path = path
        self.origin = Path().absolute()

    def __enter__(self):
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.origin)


def parse_sql_data(raw_data, table_prefix='#'):
    res = {}
    separator = '\t'
    lines = raw_data.split('\n')
    cur_headers = []
    cur_table = None
    for line in lines:
        if line.startswith(table_prefix):
            cur_table = line.split(table_prefix)[1]
        elif line:
            s_line = [elem.strip() for elem in line.split(separator) if elem.strip()]
            for i in range(len(s_line)):
                s_line[i] = None if s_line[i] == 'NULL' else s_line[i]
            if cur_table not in res:
                res[cur_table] = []
                cur_headers = s_line
            else:
                res[cur_table].append({key: s_line[i] for i, key in enumerate(cur_headers)})
    return res


def init_flask_logger(log_file_name):
    root_dir = get_root_dir()
    logs_dir = os.path.join(root_dir, 'logs')
    mkdir(logs_dir)
    log_path = os.path.join(logs_dir, log_file_name)

    # Set up the logging configuration
    log_level = logging.INFO

    # Create a rotating file handler to handle log messages
    file_handler = RotatingFileHandler(log_path, maxBytes=100000000, backupCount=3)
    file_handler.setLevel(log_level)

    # Create a stream handler to log to stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)

    # Create a logging format for both handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    stdout_handler.setFormatter(formatter)

    # Add both handlers to the root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stdout_handler)

    # Set the log level for the root logger
    root_logger.setLevel(log_level)


def string_to_ascii(s):
    return ''.join(str(ord(char)) for char in s)


def dump_combined_json_file(json_objects, output_file):
    """
    Create a single JSON file containing all given JSON-like documents from a MongoDB cursor with numbered keys.
    :param json_objects: MongoDB cursor containing JSON-like documents.
    :param output_file: Path to the output file.
    :return: True if the file creation is successful, otherwise raise an exception.
    """
    numbered_json = {str(i + 1): doc for i, doc in enumerate(json_objects)}

    try:
        with open(output_file, "w") as fp:
            json.dump(numbered_json, fp)
        return True
    except Exception as e:
        raise Exception(f'Failed to create JSON file: {str(e)}')


def sum_json(obj1, obj2):
    # Ensure both inputs are dictionaries
    if not isinstance(obj1, dict) or not isinstance(obj2, dict):
        return obj1 + obj2 if isinstance(obj1, (int, float)) and isinstance(obj2, (int, float)) else obj1

    # Initialize the result dictionary
    result = {}

    # Get all unique keys from both dictionaries
    all_keys = set(obj1.keys()) | set(obj2.keys())

    for key in all_keys:
        if key in obj1 and key in obj2:
            # If both dictionaries have the key, add the values (recursive call if values are dictionaries)
            result[key] = sum_json(obj1[key], obj2[key])
        elif key in obj1:
            # If only the first dictionary has the key, use its value
            result[key] = obj1[key]
        else:
            # If only the second dictionary has the key, use its value
            result[key] = obj2[key]

    return result


def divide_json(obj, divisor):
    # Ensure the divisor is not zero to avoid division by zero errors
    if divisor == 0:
        return "Error: Division by zero"

    # If the object is a dictionary, recursively divide all its values
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            result[key] = divide_json(value, divisor)
        return result

    # If the object is a list, recursively divide all its elements
    elif isinstance(obj, list):
        return [divide_json(element, divisor) for element in obj]

    # If the object is a number, perform the division
    elif isinstance(obj, (int, float)):
        return obj / divisor

    # If the object is of any other type, return it as None
    else:
        return obj


def max_json(obj1, obj2):
    # If both objects are dictionaries, recursively find the max of corresponding values
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        result = {}
        for key in set(obj1.keys()) | set(obj2.keys()):
            val1 = obj1.get(key)
            val2 = obj2.get(key)
            result[key] = max_json(val1, val2)
        return result

    # If both objects are lists of the same length, find the max of corresponding elements
    elif isinstance(obj1, list) and isinstance(obj2, list) and len(obj1) == len(obj2):
        return [max_json(val1, val2) for val1, val2 in zip(obj1, obj2)]

    # If both objects are numbers, return their maximum
    elif isinstance(obj1, (int, float)) and isinstance(obj2, (int, float)):
        return max(obj1, obj2)

    # In all other cases, return None
    else:
        return obj1


def min_json(obj1, obj2):
    # If both objects are dictionaries, recursively find the min of corresponding values
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        result = {}
        for key in set(obj1.keys()) | set(obj2.keys()):
            val1 = obj1.get(key)
            val2 = obj2.get(key)
            result[key] = min_json(val1, val2)
        return result

    # If both objects are lists of the same length, find the min of corresponding elements
    elif isinstance(obj1, list) and isinstance(obj2, list) and len(obj1) == len(obj2):
        return [min_json(val1, val2) for val1, val2 in zip(obj1, obj2)]

    # If both objects are numbers, return their minimum
    elif isinstance(obj1, (int, float)) and isinstance(obj2, (int, float)):
        return min(obj1, obj2)

    # In all other cases, return None
    else:
        return obj1


def is_subpath(child_path, parent_path):
    # Normalize and get absolute paths
    abs_child_path = os.path.abspath(os.path.normpath(child_path))
    abs_parent_path = os.path.abspath(os.path.normpath(parent_path))

    # Split paths into components
    child_components = abs_child_path.split(os.sep)
    parent_components = abs_parent_path.split(os.sep)
    # Check if the child path components start with the parent path components
    return child_components[:len(parent_components)] == parent_components

"""
mongodb has some "ubnormal" fields, like ObjectID,
which the simple jsonify function of flask can't handle.

The 'json_response' method here converts the response to a 'real' json using
mongodb's utilities
"""


def to_json(obj):
    return dumps(obj, json_options=RELAXED_JSON_OPTIONS)


def json_response(obj):
    return Response(to_json(obj), mimetype="application/json")

def json_to_yaml(json_input):
    """
    Convert JSON data (string or dictionary) to YAML format,
    save to a file in /tmp directory, and return the full file path.
    
    :param json_input: JSON string or Python dictionary
    :return: Full path of the saved YAML file
    """
    if isinstance(json_input, str):
        json_data = json.loads(json_input)
    else:
        json_data = json_input

    yaml_data = yaml.dump(json_data, default_flow_style=False, sort_keys=False)

    # Define the file path in /tmp
    file_path = '/tmp/output.yaml'

    # Write the YAML data to a file in /tmp
    with open(file_path, 'w') as file:
        file.write(yaml_data)
    yaml_data = yaml.safe_load(yaml_data)
    # Return the full file path
    return file_path ,yaml_data

def helm_response(success: bool, data):
    status = "success" if success else "failed"
    return {"status": status, "data": data}