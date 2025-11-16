from typing import Optional, Dict, Any, List, Tuple
from common.interfaces import DataSourceValidator, ValidationIssue
from services.documents.duplicate_checker import DocumentDuplicateChecker


class DuplicateValidator(DataSourceValidator):
    name = "DuplicateValidator"
    error_message = "This file appears to be a duplicate from an existing file and was not added. File: {source_name}"
    error_message_key = "File duplicated error"

    def __init__(self, mongo_storage: Any) -> None:
        # The validator owns and initializes its dependency
        self.duplicate_checker = DocumentDuplicateChecker(mongo_storage)

    def validate(self, **kwargs: Any) -> Tuple[bool, Optional[ValidationIssue]]:
        try:
            if self.duplicate_checker.is_duplicate(kwargs):
                return False, self.build_issue(
                    self.error_message.format(source_name=kwargs.get("source_name"))
                )
        except Exception:
            return True, None

        return True, None


def build_doc_validators(mongo_storage: Any) -> List[DataSourceValidator]:
    """Return the default list of validators to apply to a single doc.

    Keep this minimal and composable; callers can extend/replace as needed.
    """
    return [
        DuplicateValidator(mongo_storage),
    ]


