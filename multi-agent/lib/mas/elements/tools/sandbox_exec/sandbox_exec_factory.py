"""Factory for SandboxExecTool.

Reads ``sandbox_manager`` and ``execution_ctx`` from ``ElementDeps``
following the same pattern as ``SlackRetrieverFactory``.
"""
from typing import Any

from mas.core.element_deps import ElementDeps
from mas.elements.common.base_factory import BaseFactory
from mas.elements.common.exceptions import PluginConfigurationError
from .config import SandboxExecToolConfig
from .identifiers import Identifier
from .sandbox_exec import SandboxExecTool


class SandboxExecToolFactory(BaseFactory[SandboxExecToolConfig, SandboxExecTool]):
    """Creates SandboxExecTool instances."""

    def accepts(self, cfg: SandboxExecToolConfig, element_type: str) -> bool:
        return element_type == Identifier.TYPE

    def create(self, cfg: SandboxExecToolConfig, **kwargs: Any) -> SandboxExecTool:
        """Create a SandboxExecTool with injected deps."""
        deps: ElementDeps | None = kwargs.get("deps")
        try:
            return SandboxExecTool(
                sandbox_manager=deps.sandbox_manager if deps else None,
                config=cfg,
                execution_ctx=deps.execution_ctx if deps else None,
            )
        except Exception as e:
            raise PluginConfigurationError(
                f"Failed to create SandboxExecTool: {e}",
                cfg.model_dump(),
            ) from e
