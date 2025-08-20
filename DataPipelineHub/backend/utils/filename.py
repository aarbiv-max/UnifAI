import os
import re
import unicodedata


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe filesystem usage while preserving non-English letters.

    - Normalize Unicode to NFKC to avoid visually confusable characters
    - Replace path separators with underscores
    - Allow any alphanumeric characters (including non-English), plus space, dot, underscore, dash
    - Collapse whitespace to single underscores
    - Strip leading/trailing dots/underscores
    - Fallback to a default name if empty after cleaning
    """
    if not isinstance(filename, str):
        return "uploaded_document"

    name = unicodedata.normalize("NFKC", filename)
    name = name.replace("/", "_").replace("\\", "_").replace(os.sep, "_")
    cleaned = re.sub(r"\s+", "_", name, flags=re.UNICODE)
    cleaned = cleaned.strip("._")
    return cleaned or "uploaded_document"

