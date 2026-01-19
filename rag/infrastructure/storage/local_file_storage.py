"""Local file system storage adapter for document uploads."""
import base64
import os
from typing import List, Dict

from global_utils.utils import secure_filename
from shared.logger import logger


class LocalFileStorage:
    """
    Local filesystem storage for uploaded documents.
    
    Handles saving base64-encoded files to a configured upload directory.
    Uses secure_filename to sanitize filenames before saving.
    
    Usage:
        storage = LocalFileStorage("/path/to/uploads")
        storage.save_files([
            {"name": "doc.pdf", "content": "base64_encoded_content..."}
        ])
    """

    def __init__(self, upload_folder: str):
        """
        Create a LocalFileStorage configured to store uploads at the given folder.
        
        Parameters:
            upload_folder (str): Path to the directory where uploaded files will be stored; the directory is created if it does not exist.
        """
        self._upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

    @property
    def upload_folder(self) -> str:
        """
        Return the configured upload folder path used for storing files.
        
        Returns:
            str: The configured upload folder path.
        """
        return self._upload_folder

    def save_files(self, files: List[Dict[str, str]]) -> List[str]:
        """
        Save multiple files provided as base64-encoded payloads.
        
        Parameters:
            files (List[Dict[str, str]]): List of dictionaries each containing:
                - "name": the desired filename
                - "content": base64-encoded file data
        
        Returns:
            List[str]: Full filesystem paths where each file was saved, in the same order as input.
        
        Raises:
            ValueError: If any dictionary is missing the required "name" or "content" keys.
        """
        saved_paths = []
        
        for file in files:
            if "name" not in file or "content" not in file:
                raise ValueError("File must have 'name' and 'content' keys")
            
            path = self.save_base64(file["name"], file["content"])
            saved_paths.append(path)
        
        return saved_paths

    def save_base64(self, filename: str, base64_content: str) -> str:
        """
        Save a base64-encoded file to the configured upload folder.
        
        Parameters:
            filename (str): Original filename; it will be sanitized before writing.
            base64_content (str): Base64-encoded file content to decode and save.
        
        Returns:
            str: Full filesystem path where the file was saved.
        """
        content = base64.b64decode(base64_content)
        return self.save(filename, content)

    def save(self, filename: str, content: bytes) -> str:
        """
        Save raw bytes to disk using a sanitized filename.
        
        Parameters:
            filename (str): Original filename; it will be sanitized before writing.
            content (bytes): Raw file bytes to write.
        
        Returns:
            str: Full filesystem path where the file was saved.
        """
        safe_name = secure_filename(filename)
        path = os.path.join(self._upload_folder, safe_name)
        
        with open(path, "wb") as f:
            f.write(content)
        
        logger.info(f"Saved file: {safe_name}")
        return path

    def get_path(self, filename: str) -> str:
        """
        Compute the full filesystem path where a sanitized filename would be stored without writing the file.
        
        Parameters:
            filename (str): Original filename; it will be sanitized before joining into the upload folder path.
        
        Returns:
            str: Full path to the file location within the configured upload folder.
        """
        safe_name = secure_filename(filename)
        return os.path.join(self._upload_folder, safe_name)

    def exists(self, filename: str) -> bool:
        """
        Determine whether a stored file exists for the given filename.
        
        Parameters:
            filename (str): Original filename; it will be sanitized before checking.
        
        Returns:
            `true` if the file exists, `false` otherwise.
        """
        return os.path.exists(self.get_path(filename))

    def delete(self, filename: str) -> bool:
        """
        Delete the named file from the configured upload folder.
        
        Parameters:
            filename (str): Filename to delete; it will be sanitized before resolving the stored path.
        
        Returns:
            bool: `True` if the file was deleted, `False` otherwise.
        """
        path = self.get_path(filename)
        
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted file: {secure_filename(filename)}")
            return True
        return False
