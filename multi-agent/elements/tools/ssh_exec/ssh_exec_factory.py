from typing import Any
from elements.common.base_factory import BaseFactory
from elements.common.exceptions import PluginConfigurationError
from .config import SshExecToolConfig
from .ssh_exec import SshExecTool
from .identifiers import Identifier


class SshExecToolFactory(BaseFactory[SshExecToolConfig, SshExecTool]):
    """
    Factory for creating SshExecTool instances from an SshExecToolConfig.

    The tool uses lazy async connection, so instantiation is lightweight
    and cannot fail due to network issues. Connectivity is verified
    separately by the validator.
    """

    def accepts(self, cfg: SshExecToolConfig, element_type: str) -> bool:
        return element_type == Identifier.TYPE

    def create(self, cfg: SshExecToolConfig, **kwargs: Any) -> SshExecTool:
        """
        Instantiate an SshExecTool using validated config values.

        :param cfg: Fully-validated SshExecToolConfig
        :raises PluginConfigurationError: if instantiation fails
        """
        try:
            return SshExecTool(
                host=cfg.host,
                port=cfg.port,
                username=cfg.username,
                password=cfg.password,
            )
        except Exception as e:
            raise PluginConfigurationError(
                f"SshExecToolFactory.create() failed: {e}",
                cfg.dict()
            ) from e
