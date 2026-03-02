from typing import Union, Annotated
from pydantic import Field
from elements.tools.ssh_exec.config import SshExecToolConfig
from elements.tools.mcp_proxy.config import McpProxyToolConfig
from elements.tools.oc_exec.config import OcExecToolConfig
from elements.tools.web_fetch.config import WebFetchToolConfig

ToolsSpec = Annotated[
    Union[
        SshExecToolConfig,
        McpProxyToolConfig,
        OcExecToolConfig,
        WebFetchToolConfig,
    ],
    Field(discriminator="type")
]
