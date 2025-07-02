from flask import Blueprint, jsonify, session
from webargs import fields
from shared.logger import logger
from global_utils.helpers.apiargs import from_query, from_body
from global_utils.celery_app.helpers import send_task
from providers.docs import get_available_doc_list, get_best_match_results

docs_bp = Blueprint("docs", __name__)


@docs_bp.route("/available.docs.get", methods=["GET"])
def available_doc_list():
    try:
        docs = get_available_doc_list()
        return jsonify({"docs": docs}), 200
    except Exception as e:
        logger.error(f"Failed to get available docs list: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@docs_bp.route("/embed.docs", methods=["PUT"])
@from_body({
    "docs": fields.List(fields.Dict(), required=True)
})
def embed_docs(docs):
    try:
        send_task(
            task_name="data_sources.docs.docs_tasks.embed_docs_task",
            celery_queue="docs_queue",
            doc_list=docs,
            upload_by=session.get('user', {}).get('name', 'default')
        )
        return jsonify({"status": "task submitted"}), 202
    except Exception as e:
        logger.error(f"Failed to submit docs embedding task: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@docs_bp.route("/query.match", methods=["GET"])
@from_query({
    "query": fields.Str(required=True),
    "top_k_results": fields.Int(required=False),
    "scope": fields.Str(required=False, load_default="public"),
    "logged_in_user": fields.Str(required=False, load_default="default", data_key="loggedInUser")
})
def best_match_results(query, top_k_results, scope, logged_in_user):    
    try:
        search_results = get_best_match_results(query, top_k_results, scope, logged_in_user)
        return jsonify({"search_results": search_results}), 200
    except Exception as e:
        logger.error(f"Failed to find best match for user query: {str(e)}")
        return jsonify({"error": str(e)}), 500