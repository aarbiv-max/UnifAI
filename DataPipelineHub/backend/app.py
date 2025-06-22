from dotenv import load_dotenv
load_dotenv()  # Add this at the top of app.py

import os
import sys

# Add the parent directory of 'backend' (the root of the project) to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from endpoints import register_all_endpoints
from flask import Flask
from flask_cors import CORS
from global_utils.flask.request_rules import RequestRules
from utils.auth_manager import AuthManager
from config.app_config import AppConfig

# from be_utils.db.flaks_db import register_mongo
# from be_utils.utils import init_flask_logger

# Init FLASK
app = Flask(__name__)

# Configure CORS to allow credentials
CORS(app, supports_credentials=True, origins=os.environ.get("FRONTEND_URL", "http://localhost:5000"))

# init_flask_logger('access.log')
# app.config['result_backend'] = config_params.MONGODB_URL
# app.config['MONGO_URI'] = os.path.join(config_params.MONGODB_URL, config_params.MONGODB_BACKEND_COLLECTION)

# app.db = register_mongo(app)

# Initialize Authentication Manager
auth_manager = AuthManager(app)

# Store auth_manager in app extensions for easy access
app.extensions['auth_manager'] = auth_manager

register_all_endpoints(app)
config = AppConfig()

# Init before_request/after_request rules
RequestRules(app)

if __name__ == '__main__':
    # hostname = config_params.get_param_by_env('hostname')
    # port = config_params.get_param_by_env('backend_port')

    # Load environment variables for Keycloak
    required_env_vars = [
        'KEYCLOAK_BASE_URL',
        'CLIENT_ID', 
        'CLIENT_SECRET'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables before running the application.")
        sys.exit(1)
    
    hostname = "0.0.0.0"
    port = "13456"
    app.run(host=config.hostname, port=config.port, debug=True)

    # cert_file = os.path.join(os.path.dirname(__file__), 'cert.pem')
    # key_file = os.path.join(os.path.dirname(__file__), 'key.pem')

    # print(cert_file)
    # print(key_file)
    # # ✅ Enable HTTPS
    # app.run(
    #     host=hostname,
    #     port=port,
    #     debug=True,
    #     ssl_context=(cert_file, key_file)
    # )