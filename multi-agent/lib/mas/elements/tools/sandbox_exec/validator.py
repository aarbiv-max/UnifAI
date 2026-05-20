"""Validator for Sandbox Exec Tool.

Checks SSH connectivity, workspace permissions, and availability of
git and podman on the target VM.
"""
import paramiko
from typing import List
from socket import timeout as SocketTimeout, gaierror

from mas.elements.common.validator import (
    BaseElementValidator,
    ValidatorReport,
    ValidationContext,
    ValidationMessage,
    ValidationCode,
)
from .config import SandboxExecToolConfig


class SandboxExecToolValidator(BaseElementValidator):
    """Validates SSH connectivity, workspace access, and required binaries."""

    def validate(
        self,
        config: SandboxExecToolConfig,
        context: ValidationContext,
    ) -> ValidatorReport:
        messages: List[ValidationMessage] = []

        ssh_client = None
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(
                hostname=config.vm_host,
                port=config.vm_port,
                username=config.vm_username,
                password=config.vm_password,
                look_for_keys=False,
                allow_agent=False,
                timeout=context.timeout_seconds,
            )

            transport = ssh_client.get_transport()
            if transport is None or not transport.is_active():
                messages.append(self._error(
                    ValidationCode.ENDPOINT_UNREACHABLE.value,
                    "SSH transport not active after connection",
                    field="vm_host",
                ))
                return self._build_report(messages=messages)

            messages.append(self._info(
                "CONNECTION_OK",
                f"SSH connected to {config.vm_host}:{config.vm_port}",
                field="vm_host",
            ))

            self._check_workspace(ssh_client, config, messages)
            self._check_binary(ssh_client, "git", messages)
            self._check_binary(ssh_client, "podman", messages)
            self._check_image_cache(ssh_client, config, messages)

        except paramiko.AuthenticationException:
            messages.append(self._error(
                ValidationCode.INVALID_CREDENTIALS.value,
                f"Authentication failed for user '{config.vm_username}'",
                field="vm_password",
            ))
        except paramiko.SSHException as e:
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                f"SSH error: {e}",
                field="vm_host",
            ))
        except SocketTimeout:
            messages.append(self._error(
                ValidationCode.NETWORK_TIMEOUT.value,
                f"Connection timed out after {context.timeout_seconds}s",
                field="vm_host",
            ))
        except gaierror as e:
            messages.append(self._error(
                ValidationCode.ENDPOINT_UNREACHABLE.value,
                f"Cannot resolve hostname '{config.vm_host}': {e}",
                field="vm_host",
            ))
        except ConnectionRefusedError:
            messages.append(self._error(
                ValidationCode.ENDPOINT_UNREACHABLE.value,
                f"Connection refused at {config.vm_host}:{config.vm_port}",
                field="vm_host",
            ))
        except OSError as e:
            messages.append(self._error(
                ValidationCode.ENDPOINT_UNREACHABLE.value,
                f"Network error: {e}",
                field="vm_host",
            ))
        except Exception as e:
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                f"Unexpected error: {type(e).__name__}: {e}",
                field="vm_host",
            ))
        finally:
            if ssh_client is not None:
                try:
                    ssh_client.close()
                except Exception:
                    pass

        return self._build_report(messages=messages)

    # ── Checks ──────────────────────────────────────────────────

    @staticmethod
    def _exec(ssh_client: paramiko.SSHClient, cmd: str) -> tuple:
        _, stdout, stderr = ssh_client.exec_command(cmd, timeout=10)
        return stdout.read().decode().strip(), stderr.read().decode().strip()

    def _check_workspace(
        self,
        ssh_client: paramiko.SSHClient,
        config: SandboxExecToolConfig,
        messages: List[ValidationMessage],
    ) -> None:
        path = config.vm_workspace_path
        out, _ = self._exec(
            ssh_client,
            f"mkdir -p {path} && test -w {path} && echo OK",
        )
        if "OK" in out:
            messages.append(self._info(
                "WORKSPACE_OK",
                f"Workspace writable at {path}",
                field="vm_workspace_path",
            ))
        else:
            messages.append(self._error(
                "WORKSPACE_NOT_WRITABLE",
                f"Cannot write to workspace path {path}",
                field="vm_workspace_path",
            ))

    def _check_binary(
        self,
        ssh_client: paramiko.SSHClient,
        binary: str,
        messages: List[ValidationMessage],
    ) -> None:
        out, _ = self._exec(ssh_client, f"command -v {binary}")
        if out:
            messages.append(self._info(
                f"{binary.upper()}_OK",
                f"{binary} found at {out}",
            ))
        else:
            messages.append(self._error(
                "MISSING_BINARY",
                f"Required binary '{binary}' not found on the VM",
            ))

    def _check_image_cache(
        self,
        ssh_client: paramiko.SSHClient,
        config: SandboxExecToolConfig,
        messages: List[ValidationMessage],
    ) -> None:
        image = config.vm_container_image
        out, _ = self._exec(
            ssh_client,
            f"podman image exists {image} && echo CACHED || echo MISSING",
        )
        if "CACHED" in out:
            messages.append(self._info(
                "IMAGE_CACHED",
                f"Container image '{image}' is already cached",
            ))
        else:
            messages.append(self._warning(
                "IMAGE_NOT_CACHED",
                f"Image '{image}' not cached — first run will pull (adds latency)",
            ))
