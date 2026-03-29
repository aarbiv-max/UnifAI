from typing import Optional

from pydantic import BaseModel

from multi_agent.lib.mas.types import RetrieverRef


class CustomAgentNodeConfig(BaseModel):
    llm: str
    prompt: str
    code: str
    retriever: Optional[RetrieverRef] = None
    summary_enabled: bool = False