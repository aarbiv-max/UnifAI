from typing import List

from pydantic import BaseModel, validator


class A2AAgentNodeValidator(BaseModel):
    llm: str
    prompt: str
    retriever: str | None = None

    @validator("llm")
    def llm_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("llm must not be empty")
        return v

    @validator("prompt")
    def prompt_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("prompt must not be empty")
        return v