from typing import Optional

from pydantic import BaseModel, Field


class A2AAgentConfig(BaseModel):
    model_name: str = Field(..., description="The name of the language model to use.")
    prompt_template: str = Field(..., description="The prompt template to use for the agent.")
    retriever: Optional[str] = Field(None, description="The retriever to use for the agent.")
    number_of_conversations: int = Field(3, description="Number of conversations to use for context.")