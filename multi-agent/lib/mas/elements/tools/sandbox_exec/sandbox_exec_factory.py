"""Factory for SandboxExecTool.

Reads ``sandbox_manager`` and ``execution_ctx`` from ``ElementDeps``
following the same injection pattern as other tool factories.
"""
from typing import Any

from mas.elements.common.base_factory import BaseFactory
from mas.elements.common.exceptions import PluginConfigurationError
from .config import SandboxExecToolConfig
from .identifiers import Identifier
from .sandbox_exec import SandboxExecTool


class SandboxExecToolFactory(BaseFactory[SandboxExecToolConfig, SandboxExecTool]):
    """Creates SandboxExecTool instances with injected deps."""

    def accepts(self, cfg: SandboxExecToolConfig, element_type: str) -> bool:
        return element_type == Identifier.TYPE

    def create(self, cfg: SandboxExecToolConfig, **kwargs: Any) -> SandboxExecTool:
        """Create a SandboxExecTool with injected deps."""
        deps = kwargs.get("deps")

        sandbox_manager = getattr(deps, "vm_sandbox_manager", None) if deps else None
        if sandbox_manager is None:
            raise PluginConfigurationError(
                "SandboxExecTool requires a VmSandboxManager — "
                "ensure the adapter is configured in bootstrap/container.py",
                cfg.dict(),
            )

        execution_ctx = getattr(deps, "execution_ctx", None) if deps else None
        if execution_ctx is None:
            raise PluginConfigurationError(
                "SandboxExecTool requires an ExecutionContextHolder — "
                "ensure deps.execution_ctx is set",
                cfg.dict(),
            )

        try:
            return SandboxExecTool(
                sandbox_manager=sandbox_manager,
                config=cfg,
                execution_ctx=execution_ctx,
            )
        except Exception as e:
            raise PluginConfigurationError(
                f"SandboxExecToolFactory.create() failed: {e}",
                cfg.dict(),
            ) from e
