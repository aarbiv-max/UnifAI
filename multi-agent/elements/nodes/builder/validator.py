"""
Validator for BuilderNode.

Validates the builder node configuration and its LLM dependency.
"""

from typing import List, Dict

from core.ref.models import Ref
from elements.common.validator import (
    BaseElementValidator,
    ValidatorReport,
    ElementValidationResult,
    ValidationContext,
    ValidationMessage,
)
from .config import BuilderNodeConfig


class BuilderNodeValidator(BaseElementValidator):
    """
    Validates BuilderNode configuration and its dependencies.
    
    Builder node is valid if its LLM dependency is valid.
    """

    def validate(
        self,
        config: BuilderNodeConfig,
        context: ValidationContext,
    ) -> ValidatorReport:
        """
        Validate builder node config and its dependencies.
        
        Args:
            config: BuilderNodeConfig to validate
            context: Validation context with dependency results
            
        Returns:
            ValidatorReport with messages and checked dependencies
        """
        messages: List[ValidationMessage] = []
        checked_dependencies: Dict[str, ElementValidationResult] = {}
        all_deps_valid = True

        # Check LLM dependency (required)
        if config.llm:
            llm_rid = self._extract_rid(config.llm)
            if not self._check_dependency(
                context, llm_rid, "llm", messages, checked_dependencies
            ):
                all_deps_valid = False
        else:
            messages.append(self._error(
                "LLM_REQUIRED",
                "Builder node requires an LLM configuration",
            ))
            all_deps_valid = False

        # Add summary message
        if all_deps_valid:
            dep_count = len(checked_dependencies)
            if dep_count > 0:
                messages.append(self._info(
                    "ALL_DEPENDENCIES_VALID",
                    f"All {dep_count} dependencies are valid",
                ))
            else:
                messages.append(self._info(
                    "DEPENDENCIES_NOT_RESOLVED",
                    "LLM dependency configured but not resolved for validation",
                ))

        return self._build_report(
            messages=messages,
            checked_dependencies=checked_dependencies,
        )

    @staticmethod
    def _extract_rid(ref_obj) -> str:
        """Extract rid string from Ref or string."""
        if isinstance(ref_obj, Ref):
            return ref_obj.ref
        return str(ref_obj)

