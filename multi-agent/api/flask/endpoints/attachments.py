from flask import Blueprint, jsonify, current_app
from global_utils.helpers.apiargs import from_body
from webargs import fields

attachments_bp = Blueprint("attachments", __name__)


@attachments_bp.route("/upload-and-process", methods=["POST"])
@from_body({
    "files": fields.List(fields.Dict(), required=True),
})
def upload_and_process(files):
    """
    Upload document attachments and extract text content.
    
    Accepts base64-encoded files (PDF, DOCX, MD).
    Returns extracted text content for each file.
    
    Request body:
        files: [{name: str, content: str (base64)}]
    
    Response:
        attachments: [{filename, extension, text_content, char_count}]
    """
    try:
        svc = current_app.container.attachment_service

        # Validate
        valid, errors = svc.validate_files(
            [{"name": f["name"], "size": len(f.get("content", ""))} for f in files]
        )
        if errors:
            return jsonify({"errors": errors}), 400

        # Process
        results = svc.process_attachments(files)
        return jsonify({
            "attachments": [r.to_dict() for r in results]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attachments_bp.route("/supported-types", methods=["GET"])
def get_supported_types():
    """Return allowed file extensions for prompt attachments."""
    from attachments.models import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES
    return jsonify({
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "max_file_size_bytes": MAX_FILE_SIZE_BYTES,
        "max_file_size_mb": MAX_FILE_SIZE_BYTES // (1024 * 1024),
    }), 200
