from typing import Any
from mas.elements.common.base_factory import BaseFactory
from mas.elements.common.exceptions import PluginConfigurationError
from mas.core.element_deps import ElementDeps
from .config import SandboxExecToolConfig
from .sandbox_exec import SandboxExecTool
from .identifiers import Identifier


class SandboxExecToolFactory(
    BaseFactory[SandboxExecToolConfig, SandboxExecTool],
):
    """Factory for creating SandboxExecTool instances."""

    def accepts(
        self, cfg: SandboxExecToolConfig, element_type: str,
    ) -> bool:
        return element_type == Identifier.TYPE

    def create(
        self, cfg: SandboxExecToolConfig, **kwargs: Any,
    ) -> SandboxExecTool:
        deps: ElementDeps | None = kwargs.get("deps")

        if deps is None or deps.vm_sandbox_manager is None:
            raise PluginConfigurationError(
                "SandboxExecToolFactory requires a "
                "vm_sandbox_manager in ElementDeps",
                cfg.dict(),
            )

        try:
            return SandboxExecTool(
                host=cfg.vm_host,
                port=cfg.vm_port,
                username=cfg.vm_username,
                password=cfg.vm_password,
                workspace_path=cfg.vm_workspace_path,
                sandbox_manager=deps.vm_sandbox_manager,
                execution_ctx=deps.execution_ctx,
            )
        except Exception as e:
            raise PluginConfigurationError(
                f"SandboxExecToolFactory.create() failed: {e}",
                cfg.dict(),
            ) from e
