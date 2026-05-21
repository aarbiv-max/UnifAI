"""Validator for Sandbox Exec Tool."""
from typing import List
from socket import timeout as SocketTimeout, gaierror

from mas.elements.common.validator import (
    BaseElementValidator,
    ValidatorReport,
    ValidationContext,
    ValidationMessage,
    ValidationCode,
)
from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig


class SandboxExecToolValidator(BaseElementValidator):
    """Validates VM connectivity, workspace, and podman availability."""

    def validate(
        self,
        config: SandboxExecToolConfig,
        context: ValidationContext,
    ) -> ValidatorReport:
        messages: List[ValidationMessage] = []

        try:
            import paramiko
        except ImportError:
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                "paramiko is not installed; cannot validate SSH",
                field="vm_host",
            ))
            return self._build_report(messages=messages)

        ssh_client = None
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy()
            )
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
            if transport is not None and transport.is_active():
                messages.append(self._info(
                    "CONNECTION_OK",
                    f"Successfully connected to SSH server "
                    f"at {config.vm_host}:{config.vm_port}",
                    field="vm_host",
                ))
            else:
                messages.append(self._error(
                    ValidationCode.ENDPOINT_UNREACHABLE.value,
                    "SSH transport not active after connection",
                    field="vm_host",
                ))
                return self._build_report(messages=messages)

            self._check_workspace(
                ssh_client, config.vm_workspace_path, messages,
            )
            self._check_podman(ssh_client, messages)
            self._check_git(ssh_client, config, messages)

        except paramiko.AuthenticationException:
            messages.append(self._error(
                ValidationCode.INVALID_CREDENTIALS.value,
                f"Authentication failed for user "
                f"'{config.vm_username}'",
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
                f"Connection timed out after "
                f"{context.timeout_seconds}s",
                field="vm_host",
            ))
        except gaierror as e:
            messages.append(self._error(
                ValidationCode.ENDPOINT_UNREACHABLE.value,
                f"Cannot resolve hostname "
                f"'{config.vm_host}': {e}",
                field="vm_host",
            ))
        except ConnectionRefusedError:
            messages.append(self._error(
                ValidationCode.ENDPOINT_UNREACHABLE.value,
                f"Connection refused at "
                f"{config.vm_host}:{config.vm_port}",
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

    def _check_workspace(
        self,
        ssh_client: "paramiko.SSHClient",
        workspace_path: str,
        messages: List[ValidationMessage],
    ) -> None:
        """Verify the workspace directory exists and is writable."""
        import shlex
        _, stdout, stderr = ssh_client.exec_command(
            f"test -w {shlex.quote(workspace_path)} && echo OK"
        )
        out = stdout.read().decode().strip()
        if out == "OK":
            messages.append(self._info(
                "WORKSPACE_OK",
                f"Workspace '{workspace_path}' is writable",
                field="vm_workspace_path",
            ))
        else:
            err = stderr.read().decode().strip()
            messages.append(self._error(
                "WORKSPACE_NOT_WRITABLE",
                f"Workspace '{workspace_path}' is not writable"
                + (f": {err}" if err else ""),
                field="vm_workspace_path",
            ))

    def _check_podman(
        self,
        ssh_client: "paramiko.SSHClient",
        messages: List[ValidationMessage],
    ) -> None:
        """Verify that podman is available on the VM."""
        _, stdout, stderr = ssh_client.exec_command("which podman")
        out = stdout.read().decode().strip()
        if out:
            messages.append(self._info(
                "PODMAN_OK",
                f"Podman found at {out}",
                field="vm_host",
            ))
        else:
            messages.append(self._error(
                "PODMAN_NOT_FOUND",
                "podman binary not found on the VM",
                field="vm_host",
            ))

    def _check_git(
        self,
        ssh_client: "paramiko.SSHClient",
        config: SandboxExecToolConfig,
        messages: List[ValidationMessage],
    ) -> None:
        """Verify git is available and optionally clone the repo."""
        _, stdout, stderr = ssh_client.exec_command("which git")
        out = stdout.read().decode().strip()
        if not out:
            messages.append(self._error(
                "GIT_NOT_FOUND",
                "git binary not found on the VM",
                field="vm_host",
            ))
            return

        messages.append(self._info(
            "GIT_OK",
            f"Git found at {out}",
            field="vm_host",
        ))

        if not config.git_repo_url:
            return

        import shlex
        ws = shlex.quote(config.vm_workspace_path)
        url = config.git_repo_url
        if config.git_token:
            url = url.replace("://", f"://oauth2:{config.git_token}@")

        cmd = (
            f"mkdir -p {ws} && cd {ws} && "
            f"if [ -d repo.git ]; then "
            f"cd repo.git && git fetch --all 2>&1; "
            f"else git clone --bare {shlex.quote(url)} repo.git 2>&1; fi"
        )
        _, stdout, stderr = ssh_client.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        clone_out = stdout.read().decode().strip()
        clone_err = stderr.read().decode().strip()

        if config.git_token:
            clone_out = clone_out.replace(config.git_token, "***")
            clone_err = clone_err.replace(config.git_token, "***")

        if exit_code == 0:
            messages.append(self._info(
                "GIT_REPO_OK",
                f"Repository cloned/fetched to "
                f"{config.vm_workspace_path}/repo.git",
                field="git_repo_url",
            ))
        else:
            detail = clone_err or clone_out
            messages.append(self._error(
                "GIT_REPO_FAILED",
                f"Failed to clone/fetch repository: {detail}",
                field="git_repo_url",
            ))
