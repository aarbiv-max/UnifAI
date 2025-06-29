from bson import ObjectId
from be_utils.db.db import mongo, Collections
from shared.enums import FormStatus
import configparser

config = configparser.ConfigParser()
config.read("config/backend.cfg")

@mongo
def insert_new_form(project_name, training_name, git_url, git_credential_key, git_folder_path, git_branch_name,
                    tests_code_framework, number_of_tests, dataset_grading_upgrade, files_path):
    """inserting new form to the database

    :param str git_url: representing the git repo url
    :param str git_credential_key: authentication key for the dedicated git repo
    :param str git_folder_path: valid folder to expand exist on the dedicated git repo
    :param str git_branch_name: valid branch to expand from under the dedicated git repo 
    :return:
    """
    result = Collections.by_name('forms').insert_one({'projectName': project_name,
                                                      'trainingName': training_name,
                                                      'gitUrl': git_url,
                                                      'gitCredentialKey': git_credential_key,
                                                      'gitFolderPath': git_folder_path,
                                                      'gitBranchName': git_branch_name,
                                                      'testsCodeFramework': tests_code_framework,
                                                      'numberOfTests': number_of_tests,
                                                      'datasetGradingUpgrade': dataset_grading_upgrade,
                                                      'filesPath': files_path})
    return result

@mongo
def get_forms():
    """ getting all the existing forms from our forms collection
    
    :return: list of forms
    """
    result = Collections.by_name('forms').find()
    return result

@mongo
def get_form(form_id):
    """ getting form document
    
    :return: list of forms
    """
    try:
        obj_id = ObjectId(form_id) 
    except:
        print(f"❌ Invalid ObjectId: {form_id}")  
        return None 
    
    result = Collections.by_name('forms').find_one({"_id": obj_id})
    return result if result else None 

@mongo
def get_field_value(doc_id, field_name):
    """
    Retrieve the value of a specified field from a document in a forms collection.

    :param doc_id: The unique identifier of the document.
    :param field_name: The name of the field to retrieve.
    :return: The value of the field, or None if the document or field is not found.
    """
    doc = Collections.by_name('forms').find_one({"_id": ObjectId(doc_id)}, {field_name: 1, "_id": 0})
    return doc.get(field_name) if doc else None

@mongo
def update_form_status(form_id, status: FormStatus):
    """ update form status
        :return: res status
    """
    forms = Collections.by_name('forms')
    update_data = {"$set": {"status": status.value}}
    
    if status.value == 'done':
        
        form = forms.find_one({"_id": ObjectId(form_id)})
        if form and "projectName" in form:
            project_name = form["projectName"]
            hf_space = config.get("hf", "HF_SPACE", fallback=None)
            repo_id = f"{hf_space}/{project_name}"

            update_data["$set"].update({
                "hf_repo": f"{repo_id}",
                "hf_file": f"{project_name}.json"
            })

    result = forms.update_one({"_id": ObjectId(form_id)}, update_data)
        
    return {
        "success": result.modified_count > 0,
        "message": "Form status updated successfully." if result.modified_count > 0
                    else "No form found with the given id or status unchanged."
    }