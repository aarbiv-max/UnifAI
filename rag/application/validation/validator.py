"""Validator runner - executes a chain of validators."""
from typing import Optional, Any, List, Tuple

from domain.validation.port import DataSourceValidator
from domain.validation.model import ValidationIssue


class Validator:
    """Runs a list of validators with optional fail-fast behavior."""

    def __init__(self, validators: List[DataSourceValidator], fail_fast: bool = True) -> None:
        """
        Initialize the Validator with a sequence of validators and optional fail-fast behavior.
        
        Parameters:
            validators (List[DataSourceValidator]): Ordered validators to execute against input data.
            fail_fast (bool): If True, stop and return on the first validation failure; if False, run all validators and aggregate failures.
        """
        self.validators = validators
        self.fail_fast = fail_fast

    def validate(self, **kwargs: Any) -> Tuple[bool, Optional[ValidationIssue]]:
        """
        Execute the configured validators with the provided keyword arguments and determine the overall validation outcome.
        
        Parameters:
            **kwargs: Arbitrary keyword arguments forwarded to each validator's `validate` method.
        
        Returns:
            A tuple (bool, Optional[ValidationIssue]):
            - `True`, `None` if all validators pass.
            - `False`, `issue` if a validator fails and `fail_fast` is True (where `issue` is that validator's issue).
            - `False`, `issue` if one or more validators fail and `fail_fast` is False, where `issue` is a composite dictionary with keys `issue_key` (set to `"ValidationError"`), `message` (concatenated human-friendly messages), and `validator_name` (`"Validator"`).
        """
        errors: List[str] = []

        for validator in self.validators:
            is_valid, issue = validator.validate(**kwargs)
            if not is_valid:
                if self.fail_fast:
                    return False, issue
                # Accumulate human-friendly messages
                if issue:
                    errors.append(f"{issue.get('validator_name')}: {issue.get('message')}")

        if errors:
            return False, {"issue_key": "ValidationError", "message": "; ".join(errors), "validator_name": "Validator"}
        return True, None