import logging
from endpoints.schemas import MessageSchema
from flask import Blueprint
from webargs import fields
from helpers.apiargs import from_query, from_body
from flask import jsonify
from backend.providers.chat import delete_session_from_chat_history, get_chat_history, rename_title_of_chat_session, update_current_chat_history
from helpers.evaluator.evaluator_agent import EvaluatorAgent

chat_bp = Blueprint("chatHistory", __name__)

@chat_bp.route("/", methods=["GET"])
@from_query({
    "model_id":        fields.Str(required=True, data_key="modelId")
})
def get_chat_history_per_model(model_id):
    try:
        # Retrieve the chats saved in the DB for the current model
        result = get_chat_history(model_id)
        return jsonify({"status": "success", "response": result}), 200

    except Exception as e:
        logging.error(f"Error retreiving the chats for model: {model_id}")
        return jsonify({"status": "error", "message": str(e)}), 500

@chat_bp.route("/updateCurrentChat", methods=["POST"])
@from_body({
    "session_id":      fields.Str(required=True, data_key="sessionId"),
    "messages":        fields.List(fields.Nested(MessageSchema), required=True, data_key="messages"),
    "first_message":   fields.Str(required=True, data_key="firstMessage"),
    "model_id":        fields.Str(required=True, data_key="modelId"),
})
def update_current_chat(session_id, messages, first_message, model_id):
    try:
        result = update_current_chat_history(session_id, messages, first_message, model_id)
        return {"status": "success", "result": result}

    except Exception as e:
        logging.error(f"Error updating the chat for session: {session_id}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@chat_bp.route("/deleteSession", methods=["POST"])
@from_body({
    "session_id":       fields.Str(required=True, data_key="sessionId"),
})
def delete_chat_session(session_id):
    try:
        result = delete_session_from_chat_history(session_id)
        return {"status": "success", "result": result}

    except Exception as e:
        logging.error(f"Error deleting the chat session: {session_id}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@chat_bp.route("/renameSession", methods=["POST"])
@from_body({
    "session_id":       fields.Str(required=True, data_key="sessionId"),
    "title":            fields.Str(required=True, data_key="title")
})
def rename_chat_session(session_id, title):
    try:
        result = rename_title_of_chat_session(session_id, title)
        return {"status": "success", "result": result}

    except Exception as e:
        logging.error(f"Error renaming the chat session: {session_id}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@chat_bp.route("/evaluate", methods=["POST"])
@from_body({
    "code":                 fields.Str(required=True, data_key="code"),
    "repository_location":  fields.Str(required=True, data_key="repositoryLocation"),
    "framework":            fields.Str(required=True, data_key="framework"),
    "gitRepoLink":          fields.Str(required=True, data_key="gitRepoLink"),
})
def evaluate_code(code, repository_location, framework, gitRepoLink):
    try: 
        evaluator = EvaluatorAgent(repository_location, framework, gitRepoLink)
        evaluation_result = evaluator.evaluate_generated_code(code)
        return {"status": "success", "result": evaluation_result}
    
    except Exception as e:
        logging.error(f"Error evaluate the code for the repository: {repository_location}")
        return jsonify({"status": "error", "message": str(e)}), 500