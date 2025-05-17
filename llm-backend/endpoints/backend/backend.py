import logging
import os
from flask import Blueprint, jsonify, Response, stream_with_context
from webargs import fields
from be_utils.flask.api_args import from_body, from_query, abort
import provider.backend.backend as llm_provider

backend_bp = Blueprint("backend", __name__)


@backend_bp.route("/", methods=["GET"])
def sanity_check():
    return 'There is access to api backend'


@backend_bp.route("/registerAdapter", methods=["POST"])
@from_body({
    "repo_id": fields.Str(data_key="repoId", required=True),
    "epoch": fields.Integer(data_key="epoch", required=True),
    "checkpoint_step": fields.Integer(data_key="checkpointStep", required=True),
})
def register_adapter(repo_id, checkpoint_step, epoch):
    return llm_provider.register_adapter(repo_id, checkpoint_step, epoch)


@backend_bp.route("/loadModel", methods=["GET"])
@from_query({
    "adapter_id": fields.Str(data_key="adapterId", required=True)
})
def load_model(adapter_id):
    return jsonify(llm_provider.load_model(adapter_id))


@backend_bp.route("/inference", methods=["POST"])
@from_body({
    "adapter_uid": fields.Str(data_key="adapterUid", required=False, load_default=None),
    "messages": fields.List(fields.Dict(), load_default=[], required=False, data_key="messages"),
    "temperature": fields.Str(data_key="temperature", required=False, load_default=None),
    "session_id": fields.Str(data_key="sessionId", required=False, load_default="N/A"),
    "max_gen_len": fields.Str(data_key="maxGenLen", required=False, load_default="12000"),
})
def inference_post(adapter_uid, messages, temperature, session_id, max_gen_len):
    return Response(llm_provider.inference(adapter_uid,
                                           messages,
                                           temperature,
                                           max_new_tokens=int(max_gen_len),
                                           session_id=session_id),
                    content_type='text/plain')


@backend_bp.route("/stopInference", methods=["GET"])
@from_query({
    "session_id": fields.Str(data_key="sessionId", required=False, default="N/A"),
})
def stop_inference(session_id):
    return jsonify(llm_provider.stop_inference(session_id))


@backend_bp.route("/getModels", methods=["GET"])
def get_models():
    return jsonify(llm_provider.get_registered_models())


@backend_bp.route("/saveToken", methods=["POST"])
@from_body({
    "token": fields.Str(data_key="token", required=True),
})
def save_token(token):
    return jsonify(llm_provider.save_hf_token(token))


@backend_bp.route("/getHfRepoFiles", methods=["GET"])
@from_query({
    "repo_id": fields.Str(data_key="repoId", required=True),
    "repo_type": fields.Str(data_key="repoType", required=True),
})
def get_hf_repo_files(repo_id, repo_type):
    return jsonify(llm_provider.get_hf_repo_files(repo_id, repo_type))


@backend_bp.route("/getLoadedModel", methods=["GET"])
def get_loaded_model():
    return jsonify(llm_provider.get_loaded_model())


@backend_bp.route("/unloadModel", methods=["GET"])
def unload_model():
    return jsonify(llm_provider.unload_model())


@backend_bp.route("/clearChatHistory", methods=["GET"])
@from_query({
    "session_id": fields.Str(data_key="sessionId", required=False, default="N/A"),
})
def clear_chat_history(session_id):
    return jsonify(llm_provider.clear_chat_history(session_id))


@backend_bp.route("/loadChatContext", methods=["POST"])
@from_body({
    "chat": fields.List(fields.Dict(), load_default=[], required=False, data_key="chat"),
    "session_id": fields.String(data_key="sessionId", required=True),
})
def load_chat_context(chat, session_id):
    return jsonify(llm_provider.load_chat_context(chat, session_id))


@backend_bp.errorhandler(Exception)
def handle_exception(error):
    """
    Global error handler for the blueprint.
    Logs the exception and returns a JSON response with an error message and 500 status code.
    """
    logging.exception("Unhandled Exception: %s", error)
    response = jsonify({"error": str(error)})
    response.status_code = 500
    return response
