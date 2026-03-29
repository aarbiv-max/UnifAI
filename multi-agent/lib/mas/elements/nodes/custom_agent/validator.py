from pydantic import BaseModel, validator


class CustomAgentValidator(BaseModel):
    model_name: str
    prompt_template: str
    retriever: str | None
    tools: list[str]

    @validator("model_name")
    def model_name_must_not_be_blank(cls, v):
        if not v or v.isspace():
            raise ValueError("Model name cannot be blank.")
        return v

    @validator("prompt_template")
    def prompt_template_must_not_be_blank(cls, v):
        if not v or v.isspace():
            raise ValueError("Prompt template cannot be blank.")
        return v