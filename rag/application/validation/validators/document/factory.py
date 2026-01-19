"""Document validator factory."""
from typing import List

from domain.validation.port import DataSourceValidator
from .duplicate_validator import DuplicateValidator
from .extension_validator import ExtensionValidator
from .size_validator import SizeValidator
from .name_duplicate_validator import NameDuplicateValidator


class DocValidators:
    """
    Constructs the document validators pipeline.
    
    Supports two modes:
    1. Full validation (skip_validation=False): All validators run
       Used for external API calls that didn't pre-validate
       
    2. MD5-only validation (skip_validation=True): Only DuplicateValidator runs
       Used for UI uploads that were pre-validated via /docs/validate endpoint
       
    Validator execution order:
    1. ExtensionValidator - checks file type is supported
    2. SizeValidator - checks file doesn't exceed max size
    3. NameDuplicateValidator - checks no same-name doc exists for user
    4. DuplicateValidator - checks MD5 hash for content duplicates (always runs)
    """

    def __init__(
        self,
        duplicate_validator: DuplicateValidator,
        extension_validator: ExtensionValidator,
        size_validator: SizeValidator,
        name_duplicate_validator: NameDuplicateValidator,
    ) -> None:
        """
        Initialize DocValidators with the validator instances used to assemble validation pipelines.
        
        Parameters:
            duplicate_validator (DuplicateValidator): Validator that performs MD5 duplicate checks.
            extension_validator (ExtensionValidator): Validator that verifies allowed file extensions.
            size_validator (SizeValidator): Validator that enforces size limits.
            name_duplicate_validator (NameDuplicateValidator): Validator that detects duplicate file names.
        """
        self._duplicate_validator = duplicate_validator
        self._extension_validator = extension_validator
        self._size_validator = size_validator
        self._name_duplicate_validator = name_duplicate_validator

    def create_validators(self, skip_validation: bool = False) -> List[DataSourceValidator]:
        """
        Selects and returns the ordered list of document validators to execute.
        
        If `skip_validation` is True, returns only the duplicate (MD5) validator. If False, returns validators in this exact execution order: extension, size, name-duplicate, then duplicate.
        
        Parameters:
            skip_validation (bool): When True, run only the MD5 duplicate check; when False, run the full validation pipeline.
        
        Returns:
            List[DataSourceValidator]: Ordered list of validators to execute.
        """
        if skip_validation:
            # UI flow: files were pre-validated, only check MD5 duplicates
            return [
                self._duplicate_validator,
            ]

        # External API flow: full validation required
        return [
            self._extension_validator,
            self._size_validator,
            self._name_duplicate_validator,
            self._duplicate_validator,
        ]