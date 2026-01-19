"""Document endpoints - driving adapter."""
from flask import Blueprint, jsonify
from webargs import fields

from bootstrap.app_container import (
    data_source_service,
    file_storage,
    file_validation_service,
    retrieval_service,
)
from global_utils.helpers.apiargs import from_query, from_body
from infrastructure.config.doc_config_manager import DocConfigManager
from shared.logger import logger

docs_bp = Blueprint("docs", __name__)


@docs_bp.route("/upload", methods=["POST"])
@from_body({
    "files": fields.List(fields.Dict(), required=True),
})
def upload_docs(files):
    """
    Upload document files and persist them using the configured file storage service.
    
    Parameters:
        files (list[dict]): List of file payloads where each dict contains file metadata and base64-encoded content (for example keys: "filename", "content").
    
    Returns:
        tuple: (JSON response, int) — On success returns {"message": "Files uploaded successfully"}, 200. On failure returns {"error": "<message>"}, 500.
    """
    try:
        storage = file_storage()
        storage.save_files(files)
        
        return jsonify({"message": "Files uploaded successfully"}), 200
        
    except Exception as e:
        logger.error(f"Failed to upload files: {str(e)}")
        return jsonify({"error": str(e)}), 500


@docs_bp.route("/validate", methods=["POST"])
@from_body({
    "files": fields.List(fields.Dict(), required=True),
    "username": fields.Str(required=True),
    "check_duplicates": fields.Bool(required=False, load_default=True)
})
def validate_files(files, username, check_duplicates):
    """
    Validate file metadata and detect issues such as unsupported extensions, oversized files, and duplicate names.
    
    Parameters:
        files (list[dict]): File metadata objects containing at least 'name' (str) and 'size' (int, bytes).
        username (str): Identifier of the user performing the upload; used to scope validation rules.
        check_duplicates (bool): Whether to check for duplicate filenames.
    
    Returns:
        dict: On success, a dictionary with:
            - "valid_files": list of validated file info (e.g., {"name", "normalized_name", "size"}),
            - "errors": list of error objects (each containing "file_name", "error_type", "message"),
            - "has_errors": bool indicating whether any validation errors were found.
        On failure, a dictionary with an "error" key describing the failure.
    """
    try:
        service = file_validation_service(username=username)
        result = service.validate(files, check_duplicates=check_duplicates)
        return jsonify(result.to_dict()), 200
    except Exception as e:
        logger.error(f"Failed to validate files: {str(e)}")
        return jsonify({"error": str(e)}), 500


@docs_bp.route("/supported-extensions", methods=["GET"])
def get_supported_extensions():
    """
    Return the list of supported document file extensions.
    
    Returns:
        tuple: A Flask JSON response tuple. On success, the JSON payload contains
        `"supported_extensions"` mapped to a list of extensions and the HTTP status
        is 200. On failure, the JSON payload contains `"error"` with the error
        message and the HTTP status is 500.
    """
    try:
        config = DocConfigManager()
        extensions = config.get_supported_file_types()
        return jsonify({"supported_extensions": extensions}), 200
    except Exception as e:
        logger.error(f"Failed to get supported extensions: {str(e)}")
        return jsonify({"error": str(e)}), 500


@docs_bp.route("/available.docs.get", methods=["GET"])
@from_query({
    "cursor": fields.Str(required=False, load_default=None),
    "limit": fields.Int(required=False, load_default=50),
    "search": fields.Str(required=False, load_default=None),
})
def get_available_docs(cursor, limit, search):
    """
    Retrieve a paginated list of available documents with DONE status.
    
    Parameters:
        cursor (str | None): Pagination cursor identifying the page start; use None to start from the beginning.
        limit (int): Maximum number of documents to return.
        search (str | None): Optional search string to filter documents by name or metadata.
    
    Returns:
        response (flask.Response): JSON payload. On success, contains {"documents": [...]} with the requested page of documents; on failure, contains {"error": "<message>" }.
    """
    try:
        result = data_source_service().list_available_docs(
            cursor=cursor,
            limit=limit,
            search=search,
        )
        return jsonify(result.to_dict(data_key="documents")), 200
        
    except Exception as e:
        logger.error(f"Failed to get available docs: {str(e)}")
        return jsonify({"error": str(e)}), 500


@docs_bp.route("/available.tags.get", methods=["GET"])
@from_query({
    "cursor": fields.Str(required=False, load_default=""),
    "limit": fields.Int(required=False, load_default=50),
    "search_regex": fields.Str(required=False, load_default=None),
})
def get_available_tags(cursor, limit, search_regex):
    """
    Retrieve paginated tag options from documents with DONE status.
    
    Parameters:
        cursor (str): Cursor for pagination; an empty string is treated as no cursor (start from the beginning).
        limit (int): Maximum number of tag options to return.
        search_regex (str | None): Optional regex to filter tags by label or value.
    
    Returns:
        dict: JSON-serializable mapping with keys:
            - `options` (list): List of tag objects in `{label, value}` format.
            - `nextCursor` (str | None): Cursor for the next page, or `None` if there is no next page.
            - `hasMore` (bool): `true` if more pages are available, `false` otherwise.
            - `total` (int): Total number of matching tags.
        In error cases, returns a dict with an `error` string describing the failure.
    """
    try:
        result = data_source_service().get_available_tags(
            cursor=cursor if cursor else None,
            limit=limit,
            search=search_regex,
        )
        
        # Format response to match backend structure
        return jsonify({
            "options": result.data,  # Already in [{label, value}] format
            "nextCursor": result.next_cursor,
            "hasMore": result.has_more,
            "total": result.total,
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get available tags: {str(e)}")
        return jsonify({"error": str(e)}), 500


@docs_bp.route("/query.match", methods=["GET"])
@from_query({
    "query": fields.Str(required=True),
    "top_k_results": fields.Int(required=False, load_default=5),
    "scope": fields.Str(required=False, load_default="public"),
    "logged_in_user": fields.Str(required=False, load_default="default", data_key="loggedInUser"),
    "doc_ids": fields.List(fields.Str(), required=False, load_default=None, data_key="docIds"),
    "tags": fields.List(fields.Str(), required=False, load_default=None),
})
def query_match(query, top_k_results, scope, logged_in_user, doc_ids, tags):
    """
    Search documents by semantic similarity, with optional filters.
    
    Parameters:
        query (str): Text query to match against document content.
        top_k_results (int): Maximum number of matches to return.
        scope (str): "public" or "private". When "private", restricts results to documents uploaded by `logged_in_user`.
        logged_in_user (str): Username used to scope private searches.
        doc_ids (list[str] | None): Optional list of document IDs to restrict the search to.
        tags (list[str] | None): Optional list of tags to filter results.
    
    Returns:
        tuple: A Flask JSON response and HTTP status code. On success the JSON contains a "matches" key with the search results; on failure the JSON contains an "error" key with an error message.
    """
    try:
        svc = retrieval_service("DOCUMENT")
        results = svc.search(
            query=query,
            limit=top_k_results,
            scope=scope,
            user=logged_in_user,
            doc_ids=doc_ids,
            tags=tags,
        )
        
        return jsonify({"matches": results}), 200
        
    except Exception as e:
        logger.error(f"Failed to query documents: {str(e)}")
        return jsonify({"error": str(e)}), 500
