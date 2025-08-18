from typing import Literal
from pydantic import Field
from elements.tools.common.base_config import BaseToolConfig
from .identifiers import Identifier


class SshExecToolConfig(BaseToolConfig):
    """
    Configuration for the SSH-execution tool.
    """
    type: Literal[Identifier.TYPE] = Identifier.TYPE
    host: str = Field(..., description="IP or DNS name of the target VM")
    port: int = Field(22, description="SSH port")
    username: str = Field(..., description="SSH user name")
    password: str = Field(..., description="SSH password (store in secret manager!)")
