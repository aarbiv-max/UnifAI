"""Validator for SSH Exec Tool using asyncssh."""
import asyncio
from typing import List
from socket import gaierror

import asyncssh

from elements.common.validator import (
    BaseElementValidator,
    ValidatorReport,
    ValidationContext,
    ValidationMessage,
    ValidationCode,
)
from elements.tools.ssh_exec.config import SshExecToolConfig


class SshExecToolValidator(BaseElementValidator):
    """Validates SSH connection by attempting an asyncssh connect."""

    def validate(
        self,
        config: SshExecToolConfig,
        context: ValidationContext,
    ) -> ValidatorReport:
        """
        Synchronous entry point required by the validator interface.
        Runs the async validation via asyncio.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # We're inside a running event loop — use a thread to avoid
            # deadlock, which mirrors how BaseTool.arun wraps sync calls.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, self._validate_async(config, context))
                return future.result(timeout=context.timeout_seconds + 5)
        else:
            return asyncio.run(self._validate_async(config, context))

    async def _validate_async(
        self,
        config: SshExecToolConfig,
        context: ValidationContext,
    ) -> ValidatorReport:
        """Perform the actual async SSH validation."""
        messages: List[ValidationMessage] = []
        conn = None

        try:
            conn = await asyncio.wait_for(
                asyncssh.connect(
                    config.host,
                    port=config.port,
                    username=config.username,
                    password=config.password,
                    known_hosts=None,
                    login_timeout=context.timeout_seconds,
                ),
                timeout=context.timeout_seconds,
            )

            # Connection succeeded — verify transport is alive.
            # asyncssh has no public is_closed(); check internal transport.
            # pylint: disable=protected-access
            transport_alive = getattr(conn, '_transport', None) is not None
            if transport_alive:
                messages.append(self._info(
                    "CONNECTION_OK",
                    f"Successfully connected to SSH server at {config.host}:{config.port}",
                    field="host",
                ))
            else:
                messages.append(self._error(
                    ValidationCode.ENDPOINT_UNREACHABLE.value,
                    "SSH connection closed unexpectedly after connect",
                    field="host",
                ))

        except asyncssh.PermissionDenied:
            messages.append(self._error(
                ValidationCode.INVALID_CREDENTIALS.value,
                f"Authentication failed for user '{config.username}'",
                field="password",
            ))
        except asyncssh.DisconnectError as e:
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                f"SSH disconnect error: {e}",
                field="host",
            ))
        except asyncssh.ConnectionLost as e:
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                f"SSH connection lost: {e}",
                field="host",
            ))
        except asyncio.TimeoutError:
            messages.append(self._error(
                ValidationCode.NETWORK_TIMEOUT.value,
                f"Connection timed out after {context.timeout_seconds}s",
                field="host",
            ))
        except gaierror as e:
            messages.append(self._error(
                ValidationCode.ENDPOINT_UNREACHABLE.value,
                f"Cannot resolve hostname '{config.host}': {e}",
                field="host",
            ))
        except ConnectionRefusedError:
            messages.append(self._error(
                ValidationCode.ENDPOINT_UNREACHABLE.value,
                f"Connection refused at {config.host}:{config.port}",
                field="host",
            ))
        except OSError as e:
            messages.append(self._error(
                ValidationCode.ENDPOINT_UNREACHABLE.value,
                f"Network error: {e}",
                field="host",
            ))
        except Exception as e:
            messages.append(self._error(
                ValidationCode.NETWORK_ERROR.value,
                f"Unexpected error: {type(e).__name__}: {e}",
                field="host",
            ))
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        return self._build_report(messages=messages)
