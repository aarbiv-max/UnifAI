"""
elements/llms/openai/validator.py

Validator for OpenAI LLM - checks API connectivity and model availability.
"""

from typing import List

from openai import (
    OpenAI,
    AuthenticationError,
    PermissionDeniedError,
    BadRequestError,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIStatusError,
)

from elements.common.validator import (
    BaseElementValidator,
    ValidatorReport,
    ValidationContext,
    ValidationMessage,
    ValidationCode,
)
from elements.llms.common.validation_codes import LLMValidationCode
from elements.llms.openai.config import OpenAIConfig


class OpenAILLMValidator(BaseElementValidator):
    """
    Validates OpenAI LLM configuration.
    
    Checks:
    - API endpoint reachability
    - API key validity
    - Model availability
    """

    def validate(
        self,
        config: OpenAIConfig,
        context: ValidationContext,
    ) -> ValidatorReport:
        """
        Validate OpenAI LLM config.
        
        Returns ValidatorReport (service adds metadata).
        """
        messages: List[ValidationMessage] = []

        try:
            client = OpenAI(
                base_url=str(config.base_url),
                api_key=config.api_key,
                timeout=context.timeout_seconds,
            )
            available_models = client.models.list()
            model_ids = {m.id for m in available_models.data}

            if config.model_name in model_ids:
                messages.append(self._info(
                    LLMValidationCode.MODEL_AVAILABLE.value,
                    f"Successfully connected and found model '{config.model_name}'",
                    field="model_name",
                ))
            else:
                messages.append(self._error(
                    LLMValidationCode.MODEL_NOT_FOUND.value,
                    f"Model '{config.model_name}' not found",
                    field="model_name",
                ))

        except (AuthenticationError, PermissionDeniedError):
            # 401, 403
            messages.append(self._error(
                ValidationCode.INVALID_CREDENTIALS.value,
                "Authentication failed - check API key",
                field="api_key",
            ))
        except BadRequestError:
            # 400 - Google uses this for invalid API keys
            messages.append(self._error(
                ValidationCode.INVALID_CREDENTIALS.value,
                "Bad request - check API key and configuration",
                field="api_key",
            ))
        except RateLimitError:
            # 429
            messages.append(self._error(
                LLMValidationCode.RATE_LIMITED.value,
                "Rate limit exceeded",
                field="base_url",
            ))
        except APITimeoutError:
            messages.append(self._error(
                ValidationCode.NETWORK_TIMEOUT.value,
                f"Connection timed out after {context.timeout_seconds}s",
                field="base_url",
            ))
        except APIConnectionError:
            messages.append(self._error(
                ValidationCode.ENDPOINT_UNREACHABLE.value,
                "Cannot connect to API endpoint",
                field="base_url",
            ))
        except APIStatusError as e:
            # Any other 4xx/5xx
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                f"API error (HTTP {e.status_code})",
                field="base_url",
            ))

        return self._build_report(messages=messages)

