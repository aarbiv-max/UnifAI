import logging
from flask import Blueprint
from backend.be_utils.utils import json_response
from backend.providers.prompts import delete_prompt, get_saved_prompts, insert_new_prompt, insert_prompt_comment, insert_prompt_is_complete, insert_prompt_rating
from helpers.apiargs import  from_body
from webargs import fields
from flask import jsonify

prompts_bp = Blueprint("prompts", __name__)

@prompts_bp.route("/savePrompt", methods=["POST"])
@from_body({
    "model_id":                    fields.Str(required=True, data_key="modelId"),
    "model_name":                  fields.Str(required=True, data_key="modelName"),
    "training_name":               fields.Str(required=True, data_key="trainingName"),
    "prompt_entire_text":          fields.Str(required=True, data_key="promptEntireText"),
    "prompt_user_latest_text":     fields.Str(required=True, data_key="promptUserLastQuestionText"),
    "prompt_llm_latest_text":      fields.Str(required=True, data_key="promptLLMLastAnswerText"),
    "prompt_name":                 fields.Str(required=True, data_key="promptName"),
})
def save_prompt(model_id, model_name, training_name, prompt_entire_text, prompt_user_latest_text, prompt_llm_latest_text, prompt_name):
    try:
        # Insert LLM prompt into MongoDB collection
        result = insert_new_prompt(model_id, model_name, training_name, prompt_entire_text, prompt_user_latest_text, prompt_llm_latest_text, prompt_name)

        # Return success response with inserted id
        return jsonify({"status": "success", "inserted_id": str(result.inserted_id)}), 201

    except Exception as e:
        # Log the error and return error response
        logging.error(f"Error saving new prompt: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@prompts_bp.route("/retrievePrompt", methods=["GET"])
def retrieve_prompt():
    try:
        # Insert LLM prompt into MongoDB collection
        result = get_saved_prompts()

        # Return success response with inserted id
        return json_response({"result": result})

    except Exception as e:
        # Log the error and return error response
        logging.error(f"Error saving new prompt: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@prompts_bp.route("/savePromptComment", methods=["POST"])
@from_body({
    "model_id":        fields.Str(required=True, data_key="modelId"),
    "unique_id":       fields.Str(required=True, data_key="uniqueId"),
    "comment":         fields.Str(required=True, data_key="comment"),
})
def save_prompt_comment(model_id, unique_id, comment):
    try:
        # Insert LLM prompt into MongoDB collection
        result = insert_prompt_comment(model_id, unique_id, comment)

        # Return success response
        return jsonify({"status": "success"}), 201

    except Exception as e:
        # Log the error and return error response
        logging.error(f"Error saving new prompt: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@prompts_bp.route("/markPromptAsComplete", methods=["POST"])
@from_body({
    "model_id":        fields.Str(required=True, data_key="modelId"),
    "unique_id":       fields.Str(required=True, data_key="uniqueId"),
    "completed":       fields.Bool(required=True, data_key="completed"),
})
def save_prompt_is_complete(model_id, unique_id, completed):
    try:
        # Insert LLM prompt into MongoDB collection
        result = insert_prompt_is_complete(model_id, unique_id, completed)

        # Return success response
        return jsonify({"status": "success"}), 201

    except Exception as e:
        # Log the error and return error response
        logging.error(f"Error saving new prompt: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@prompts_bp.route("/ratePrompt", methods=["POST"])
@from_body({
    "model_id":           fields.Str(required=True, data_key="modelId"),
    "user_prompt":        fields.Str(required=True, data_key="prompt"),
    "response_prompt":    fields.Str(required=True, data_key="response"),
    "rating":             fields.Number(required=True, data_key="rating"),
    "rating_text":        fields.Str(load_default='', data_key="ratingText"),
})
def save_prompt_rating(model_id, user_prompt, response_prompt, rating, rating_text):
    try:
        # Insert LLM prompt into MongoDB collection
        result = insert_prompt_rating(model_id, user_prompt, response_prompt, rating, rating_text)

        # Return success response
        return jsonify({"status": "success"}), 201

    except Exception as e:
        # Log the error and return error response
        logging.error(f"Error rating new prompt: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@prompts_bp.route("/deletePrompt", methods=["POST"])
@from_body({
    "unique_id":       fields.Str(required=True, data_key="uniqueId"),
})
def delete_prompt_from_db(unique_id):
    try:
        # Delete LLM pre-saved prompt from MongoDB collection
        result = delete_prompt(unique_id)

        # Return success response
        return jsonify({"status": "success"}), 201

    except Exception as e:
        # Log the error and return error response
        logging.error(f"Error deleting prompt: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500