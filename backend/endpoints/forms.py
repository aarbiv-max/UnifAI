import logging
from flask import Blueprint
from backend.be_utils.utils import json_response
from backend.providers.forms import get_field_value, get_forms, insert_new_form
from helpers.apiargs import from_body
from webargs import fields
from flask import jsonify
from shared.fields import FormFields
from helpers.apiargs import from_query

forms_bp = Blueprint("forms", __name__)

@forms_bp.route("/insert", methods=["POST"])
@from_body({
    "project_name":            fields.Str(required=True, data_key="projectName"),
    "training_name":           fields.Str(required=True, data_key="trainingName"),
    "git_url":                 fields.Str(required=True, data_key="gitUrl"),
    "git_credential_key":      fields.Str(required=True, data_key="gitCredentialKey"),
    "git_folder_path":         fields.Str(load_default='', data_key="gitFolderPath"),
    "git_branch_name":         fields.Str(required=True, data_key="gitBranchName"),
    "tests_code_framework":    fields.Str(required=True, data_key="testsCodeFramework"),
    "number_of_tests":         fields.Int(load_default=None, data_key="numberOfTests"),
    "dataset_grading_upgrade": fields.Bool(load_default=False, data_key="datasetGradingUpgrade"),
    "files_path":              fields.List(fields.Str(), load_default=[], data_key="filesPath")
})
def insert_form(project_name, training_name, git_url, git_credential_key, git_folder_path, git_branch_name,
                tests_code_framework, number_of_tests, dataset_grading_upgrade, files_path):
    try:
        # Insert form data into MongoDB collection
        result = insert_new_form(project_name, training_name, git_url, git_credential_key, git_folder_path, git_branch_name,
                                 tests_code_framework, number_of_tests, dataset_grading_upgrade, files_path)

        # Return success response with inserted id
        return jsonify({"status": "success", "inserted_id": str(result.inserted_id)}), 201

    except Exception as e:
        # Log the error and return error response
        logging.error(f"Error saving form data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@forms_bp.route("retrieve", methods=["GET"])
def retrieve_forms():
    try:
        # Insert LLM prompt into MongoDB collection
        result = get_forms()

        # Return success response with inserted id
        return json_response({"result": result})

    except Exception as e:
        # Log the error and return error response
        logging.error(f"Error retrieving existing forms: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    

@forms_bp.route("status", methods=["GET"])
@from_query({"form_id": fields.Str(load_default='', data_key="formId")})
def retrieve_form_status(form_id):
    form_status = get_field_value(form_id, FormFields.STATUS.name)
    
    if form_status is None:
        return json_response({"error": "Form not found"}), 404
    
    return json_response({"status": form_status})