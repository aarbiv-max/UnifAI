import asyncio

from flask import request
from flask import jsonify
from flask import Blueprint
from backend.providers.parser import get_parsed_elements_by_git_repos, trigger_parser
from helpers.apiargs import from_body, from_query
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

@parser_bp.route('/parsedElements', methods=['GET'])
@from_query({"git_repos_link": fields.List(fields.Str(), load_default='', data_key="gitReposLink")})
def parsed_elements(git_repos_link):
    """API endpoint to retrieve parsed elements from db."""
    try:
        documents = get_parsed_elements_by_git_repos(git_repos_link)
        return jsonify({"status": "success", "data": documents})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
