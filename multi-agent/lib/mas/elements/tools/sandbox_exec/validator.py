"""Validator for SandboxExecTool — checks cluster connectivity and namespace access."""
from typing import List

import openshift_client as oc

from mas.elements.common.validator import (
    BaseElementValidator,
    ValidationCode,
    ValidationContext,
    ValidationMessage,
    ValidatorReport,
)
from .config import SandboxExecToolConfig


class SandboxExecToolValidator(BaseElementValidator):
    """Validates OpenShift cluster reachability and namespace access."""

    def validate(
        self,
        config: SandboxExecToolConfig,
        context: ValidationContext,
    ) -> ValidatorReport:
        messages: List[ValidationMessage] = []

        try:
            with oc.api_server(config.cluster_api):
                with oc.token(config.cluster_token):
                    with oc.tls_verify(enable=not config.skip_tls_verify):
                        whoami = oc.invoke("whoami")

            stdout = (whoami.out() or "").strip()
            if whoami.status() != 0:
                messages.append(self._error(
                    ValidationCode.INVALID_CREDENTIALS.value,
                    (whoami.err() or "").strip() or "Authentication failed",
                    field="cluster_token",
                ))
                return self._build_report(messages=messages)

            messages.append(self._info(
                "CONNECTION_OK",
                f"Connected as: {stdout}",
                field="cluster_api",
            ))

            with oc.api_server(config.cluster_api):
                with oc.token(config.cluster_token):
                    with oc.tls_verify(enable=not config.skip_tls_verify):
                        ns_result = oc.invoke("get", ["namespace", config.namespace])

            if ns_result.status() != 0:
                messages.append(self._error(
                    ValidationCode.NETWORK_ERROR.value,
                    f"Namespace '{config.namespace}' not found or inaccessible",
                    field="namespace",
                ))
            else:
                messages.append(self._info(
                    "NAMESPACE_OK",
                    f"Namespace '{config.namespace}' is accessible",
                    field="namespace",
                ))

        except oc.OpenShiftPythonException as e:
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                str(e),
                field="cluster_api",
            ))
        except Exception as e:
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                str(e),
                field="cluster_api",
            ))

        return self._build_report(messages=messages)
