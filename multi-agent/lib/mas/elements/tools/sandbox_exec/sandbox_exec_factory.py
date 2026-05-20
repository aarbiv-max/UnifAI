from typing import Any
from uuid import uuid4

from mas.elements.common.base_factory import BaseFactory
from mas.elements.common.exceptions import PluginConfigurationError
from .config import SandboxExecToolConfig
from .sandbox_exec import SandboxExecTool
from .identifiers import Identifier


class SandboxExecToolFactory(BaseFactory[SandboxExecToolConfig, SandboxExecTool]):
    """Factory for creating SandboxExecTool instances."""

    def accepts(self, cfg: SandboxExecToolConfig, element_type: str) -> bool:
        return element_type == Identifier.TYPE

    def create(self, cfg: SandboxExecToolConfig, **kwargs: Any) -> SandboxExecTool:
        """Create a SandboxExecTool from validated config + injected deps.

        Reads ``vm_sandbox_manager`` and ``run_id`` from ElementDeps.
        Falls back to uuid4 for run_id when deps are unavailable.
        """
        deps = kwargs.get("deps")

        vm_sandbox_manager = getattr(deps, "vm_sandbox_manager", None) if deps else None
        if vm_sandbox_manager is None:
            raise PluginConfigurationError(
                "SandboxExecTool requires a VmSandboxManager — "
                "ensure the adapter is configured in bootstrap/container.py",
                cfg.dict(),
            )

        run_id = getattr(deps, "run_id", None) if deps else None
        if not run_id:
            run_id = str(uuid4())[:8]

        try:
            return SandboxExecTool(
                config=cfg,
                vm_sandbox_manager=vm_sandbox_manager,
                run_id=run_id,
            )
        except Exception as e:
            raise PluginConfigurationError(
                f"SandboxExecToolFactory.create() failed: {e}",
                cfg.dict(),
            ) from e
