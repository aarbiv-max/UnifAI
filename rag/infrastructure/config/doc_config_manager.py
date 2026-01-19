"""Document configuration manager - infrastructure adapter."""
import os
from typing import Dict, List, Any, Optional, Tuple
from infrastructure.config.base_config_manager import BaseConfigurationManager


class DocConfigManager(BaseConfigurationManager):
    """
    Configuration manager for document processing.
    
    Manages settings for document parsing and extraction operations.
    Inherits file loading capability from BaseConfigurationManager.
    """
    
    DEFAULT_CONFIG: Dict[str, Any] = {
        "extraction_mode": "default",
        "include_metadata": True,
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "supported_extensions": [".pdf", ".docx", ".md", ".pptx"],
        "max_file_size_mb": 50,
        "timeout_seconds": 300,
        # Note: The following parameters are kept for future use if docling adds these features
        # Currently docling.DocumentConverter.convert() doesn't support these parameters
        "use_ocr": False,  # Not currently supported by docling
        "ocr_language": "eng",  # Not currently supported by docling
        "extract_tables": True,  # Not currently supported by docling
        "extract_images": False,  # Not currently supported by docling
        "image_extraction_path": "./extracted_images/",
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Create a DocConfigManager, ensure required default settings are present, and prepare the image extraction directory if enabled.
        
        Initializes the base configuration using the optional config_path, merges any keys from DEFAULT_CONFIG into the manager's internal configuration when missing, and creates the directory specified by `image_extraction_path` if `extract_images` is enabled.
        
        Parameters:
            config_path (Optional[str]): Path to a configuration file to load; if None, the manager uses its default loading behavior.
        """
        super().__init__(config_path)
        
        # Set default configurations if not already set (from file or elsewhere)
        for key, value in self.DEFAULT_CONFIG.items():
            if key not in self._config:
                self._config[key] = value
        
        # Create directory for image extraction if enabled
        if self._config.get("extract_images", False):
            os.makedirs(self._config.get("image_extraction_path", "./extracted_images/"), exist_ok=True)
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate the document processing configuration and collect any validation errors.
        
        This performs validation of critical configuration entries used for document parsing and extraction, including:
        - `supported_extensions`: must be a non-empty list.
        - Numeric parameters (`chunk_size`, `chunk_overlap`, `max_file_size_mb`, `timeout_seconds`): must be numeric and fall within sensible ranges.
        - Boolean flags (`include_metadata`, `use_ocr`, `extract_tables`, `extract_images`): must be boolean values.
        - `image_extraction_path`: must be a non-empty string when `extract_images` is enabled.
        
        Returns:
            (is_valid, errors) (Tuple[bool, List[str]]): `is_valid` is True if no validation errors were found; `errors` is a list of human-readable validation messages.
        """
        errors = []
        
        # Validate supported extensions
        supported_extensions = self._config.get("supported_extensions", [])
        if not isinstance(supported_extensions, list) or not supported_extensions:
            errors.append("Supported extensions must be a non-empty list")
            
        # Validate numeric parameters
        numeric_params = {
            "chunk_size": (100, 10000),
            "chunk_overlap": (0, 5000),
            "max_file_size_mb": (1, 1000),
            "timeout_seconds": (30, 3600)
        }
        
        for param, (min_val, max_val) in numeric_params.items():
            value = self._config.get(param)
            if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                errors.append(f"{param} must be a number between {min_val} and {max_val}")
        
        # Validate boolean parameters
        bool_params = ["include_metadata", "use_ocr", "extract_tables", "extract_images"]
        for param in bool_params:
            if not isinstance(self._config.get(param), bool):
                errors.append(f"{param} must be a boolean value")
        
        # Validate path parameters
        if self._config.get("extract_images"):
            image_path = self._config.get("image_extraction_path")
            if not image_path or not isinstance(image_path, str):
                errors.append("image_extraction_path must be a valid directory path when extract_images is enabled")
        
        return len(errors) == 0, errors
    
    def get_supported_file_types(self) -> List[str]:
        """
        Return the list of supported file extensions from the configuration.
        
        Returns:
            List[str]: Supported file extension strings from the current configuration.
        """
        return self.get_config_value("supported_extensions", [])
    
    def is_file_type_supported(self, file_extension: str) -> bool:
        """
        Determines whether a file extension is included in the configured supported file types.
        
        Parameters:
            file_extension (str): The file extension to check; a leading dot is allowed and case is ignored.
        
        Returns:
            `true` if the extension is supported, `false` otherwise.
        """
        file_extension = file_extension.lower().lstrip('.')
        return file_extension in self.get_supported_file_types()