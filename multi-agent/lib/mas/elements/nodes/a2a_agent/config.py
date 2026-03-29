from typing import Optional

from pydantic import BaseModel

from multi_agent.lib.mas.types import RetrieverRef


class A2AAgentNodeConfig(BaseModel):
    llm: str
    prompt: str
    retriever: Optional[RetrieverRef] = None
    summary_enabled: bool = False