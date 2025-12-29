from typing import List, Any, Dict
from common.interfaces import DataSourceValidator, ValidationStage
from .duplicate_validator import DuplicateValidator
from .extension_validator import ExtensionValidator
from .size_validator import SizeValidator
from .name_duplicate_validator import NameDuplicateValidator
from .pre_batch_validator import PreBatchValidator, FileValidationResult


class DocValidators:
    """
    Constructs the document validators pipeline.
    
    Supports stage-based validation: PRE Stage (before file upload) and POST Stage (during registration).

    Validator execution order:
    1. ExtensionValidator - checks file type is supported
    2. SizeValidator - checks file doesn't exceed max size
    3. NameDuplicateValidator - checks no same-name doc exists for user
    4. DuplicateValidator - checks MD5 hash for content duplicates
    """
    
    def create_validators(
        self, 
        stage: ValidationStage = ValidationStage.POST,
        skip_validation: bool = False
    ) -> List[DataSourceValidator]:
        """
        Create the list of validators to run based on stage.
        
        Args:
            stage: ValidationStage.PRE for pre-upload, ValidationStage.POST for registration
            skip_validation: For POST stage only. If True, only include MD5 DuplicateValidator.
                           If False, include all validators for full validation.
                           Ignored for PRE stage.
                           
        Returns:
            List of validators to execute in order.
        """
        if stage == ValidationStage.PRE:
            # PRE validation: extension, size, name duplicate (no MD5)
            return [
                ExtensionValidator(),
                SizeValidator(),
                NameDuplicateValidator(),
            ]
        
        # POST validation
        if skip_validation:
            # UI flow: files were pre-validated, only check MD5 duplicates
            return [
                DuplicateValidator(),
            ]
        
        # External API flow: full validation required
        return [
            ExtensionValidator(),
            SizeValidator(),
            NameDuplicateValidator(),
            DuplicateValidator(),
        ]
    
    def create_pre_batch_validator(
        self,
        username: str,
        check_duplicates: bool = True
    ) -> PreBatchValidator:
        """
        Create a batch validator for PRE-stage validation.
        
        This is a convenience method that creates a PreBatchValidator
        configured with the appropriate validators for pre-upload validation.
        
        Args:
            username: Username for duplicate checking
            check_duplicates: Whether to check for duplicate filenames
            
        Returns:
            PreBatchValidator configured for pre-upload validation
        """
        validators = self.create_validators(stage=ValidationStage.PRE)
        return PreBatchValidator(
            validators=validators,
            username=username,
            check_duplicates=check_duplicates
        )
    
    def validate_pre_batch(
        self,
        files: List[Dict[str, Any]],
        username: str,
        check_duplicates: bool = True
    ) -> FileValidationResult:
        """
        Validate a batch of files for pre-upload validation.
        
        This is a convenience method that creates a batch validator
        and runs validation in one call.
        
        Args:
            files: List of file metadata dictionaries with 'name' and 'size' keys.
                   Example: [{"name": "doc.pdf", "size": 1024000}]
            username: Username for duplicate checking
            check_duplicates: Whether to check for duplicate filenames
            
        Returns:
            FileValidationResult containing valid files and errors.
        """
        batch_validator = self.create_pre_batch_validator(
            username=username,
            check_duplicates=check_duplicates
        )
        return batch_validator.validate_batch(files)
