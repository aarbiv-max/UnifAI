import os
import sys

from utils.storage.mongo.mongo_storage import MongoStorage, SourceService

# Add the parent directory of 'backend' (the root of the project) to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from endpoints import register_all_endpoints
from flask import Flask
from flask_cors import CORS
from global_utils.flask.request_rules import RequestRules
from global_utils.config import ConfigManager

# from config.configParams import config_params
# from be_utils.db.flaks_db import register_mongo
# from be_utils.utils import init_flask_logger

# Init FLASK
app = Flask(__name__)
CORS(app)

# init_flask_logger('access.log')
# app.config['result_backend'] = config_params.MONGODB_URL
# app.config['MONGO_URI'] = os.path.join(config_params.MONGODB_URL, config_params.MONGODB_BACKEND_COLLECTION)

# app.db = register_mongo(app)

register_all_endpoints(app)

# Following configuration is required to interact with global_utils such celery in other parts of the application  
initial_config = {
  "rabbitmq_port": "5672",
  "rabbitmq_ip": "0.0.0.0",
  "mongodb_port": "27017",
  "mongodb_ip": "0.0.0.0"
}

config = ConfigManager(initial_config=initial_config)

# mongo_ip   = config.get_param_by_env("mongodb_ip")
# mongo_port = config.get_param_by_env("mongodb_port")
mongo_uri  = "mongodb://ae8f0dd8e6cd046539c3f0b7c6a75f13-508991814.us-east-1.elb.amazonaws.com:27017"

# ─── 3) Init your storage and stash it on the app ─────────────────────────
#    We only pass the URI; the DB name can be chosen per-call later.
app.mongo_storage = MongoStorage(mongo_uri)
app.source_service  = SourceService(app.mongo_storage, app.mongo_storage)
# Init before_request/after_request rules
RequestRules(app)

if __name__ == '__main__':
    # hostname = config_params.get_param_by_env('hostname')
    # port = config_params.get_param_by_env('backend_port')
    hostname = "0.0.0.0"
    port = "13456"
    app.run(host=hostname, port=port, debug=True)
