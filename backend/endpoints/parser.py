import asyncio
from flask import jsonify
from flask import Blueprint
from backend.providers.parser import trigger_parser
from helpers.apiargs import from_body
from webargs import fields
import concurrent.futures

executor = concurrent.futures.ThreadPoolExecutor()
parser_bp = Blueprint("parser", __name__)

@parser_bp.route('/start', methods=['POST'])
@from_body({"form_id": fields.Str(load_default='', data_key="formId")})
def start_parser(form_id):
    """API endpoint to start parsing Git repo."""
    executor.submit(asyncio.run, trigger_parser(form_id))
    return {"status": "success"}, 200
