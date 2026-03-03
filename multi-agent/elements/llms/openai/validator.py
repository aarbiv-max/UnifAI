"""
elements/llms/openai/validator.py

Validator for OpenAI LLM - checks API connectivity and model availability.

Supports both standard OpenAI API and OpenAI-compatible APIs (vLLM, TGI, etc.)
that may not implement the /v1/models endpoint.
"""

import logging
from typing import List, Optional, Set

import httpx

from openai import (
    OpenAI,
    AuthenticationError,
    PermissionDeniedError,
    BadRequestError,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIStatusError,
    NotFoundError,
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

logger = logging.getLogger(__name__)


class OpenAILLMValidator(BaseElementValidator):
    """
    Validates OpenAI LLM configuration.
    
    Checks:
    - API endpoint reachability
    - API key validity
    - Model availability (if supported by the API)
    
    For OpenAI-compatible APIs that don't support /v1/models,
    falls back to a simple completion test.
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
            # Use explicit httpx.Timeout for proper timeout handling
            # connect: time to establish connection
            timeout = httpx.Timeout(
                timeout=context.timeout_seconds,
                connect=min(5.0, context.timeout_seconds),
            )

            http_client = httpx.Client(
                timeout=timeout,
                verify=False,  # Skip SSL verification
            )
            
            client = OpenAI(
                base_url=str(config.base_url),
                api_key=config.api_key,
                http_client=http_client,
            )
            
            model_ids = self._try_list_models(client)
            if model_ids is not None:
                # API supports /v1/models - verify model exists
                self._validate_model_in_list(config.model_name, model_ids, messages)
            else:
                # API doesn't support /v1/models - fallback to completion test
                logger.info(
                    f"API at {config.base_url} doesn't support /v1/models, "
                    "falling back to completion test"
                )
                self._validate_via_completion(client, config.model_name, messages)
            
        except (AuthenticationError, PermissionDeniedError):
            messages.append(self._error(
                ValidationCode.INVALID_CREDENTIALS.value,
                "Authentication failed - check API key",
                field="api_key",
            ))
        except BadRequestError as e:
            messages.append(self._error(
                ValidationCode.INVALID_CREDENTIALS.value,
                f"Bad request - check API key and configuration: {e.message}",
                field="api_key",
            ))
        except RateLimitError:
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
        except APIConnectionError as e:
            messages.append(self._error(
                ValidationCode.ENDPOINT_UNREACHABLE.value,
                f"Cannot connect to API endpoint: {e.__cause__}",
                field="base_url",
            ))
        except APIStatusError as e:
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                f"API error (HTTP {e.status_code}): {e.message}",
                field="base_url",
            ))
        except Exception as e:
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                f"Unexpected error: {type(e).__name__}: {str(e)}",
                field="base_url",
            ))

        return self._build_report(messages=messages)
    
    def _try_list_models(self, client: OpenAI) -> Optional[Set[str]]:
        """
        Attempt to list available models.
        
        Returns:
            Set of model IDs if successful, None if endpoint not supported.
        """
        try:
            available_models = client.models.list()
            return {m.id for m in available_models.data}
        except (NotFoundError, APIStatusError) as e:
            # 404, 501, or other errors indicate /v1/models not supported
            status = getattr(e, 'status_code', None)
            logger.error(f"Models endpoint not available (HTTP {status}): {e}")
            if status in (404, 501, None):
                return None
            raise
        except Exception as e:
            logger.error(f"Exception in _try_list_models: {type(e).__name__}: {e}")
            logger.error(f"Falling back to completion test")
            return None
    
    def _validate_model_in_list(
        self,
        model_name: str,
        model_ids: Set[str],
        messages: List[ValidationMessage],
    ) -> None:
        """Validate that the model exists in the available models list."""
        if model_name in model_ids:
            messages.append(self._info(
                LLMValidationCode.MODEL_AVAILABLE.value,
                f"Successfully connected and found model '{model_name}'",
                field="model_name",
            ))
        else:
            messages.append(self._error(
                LLMValidationCode.MODEL_NOT_FOUND.value,
                f"Model '{model_name}' not found. Available: {sorted(model_ids)[:5]}...",
                field="model_name",
            ))
    
    def _validate_via_completion(
        self,
        client: OpenAI,
        model_name: str,
        messages: List[ValidationMessage],
    ) -> None:
        """
        Validate by attempting a minimal completion request.
        
        This is used as a fallback for OpenAI-compatible APIs
        that don't support the /v1/models endpoint.
        """
        try:
            client.completions.create(
                model=model_name,
                prompt="test",
                max_tokens=1,
            )
            messages.append(self._info(
                LLMValidationCode.MODEL_AVAILABLE.value,
                f"Successfully connected and validated model '{model_name}' via completion test",
                field="model_name",
            ))
        except NotFoundError:
            messages.append(self._error(
                LLMValidationCode.MODEL_NOT_FOUND.value,
                f"Model '{model_name}' not found",
                field="model_name",
            ))
        except BadRequestError as e:
            if "model" in str(e).lower():
                messages.append(self._error(
                    LLMValidationCode.MODEL_NOT_FOUND.value,
                    f"Model '{model_name}' not found or invalid",
                    field="model_name",
                ))
            else:
                messages.append(self._info(
                    LLMValidationCode.MODEL_AVAILABLE.value,
                    f"Successfully connected to API (model '{model_name}' accepted)",
                    field="model_name",
                ))

