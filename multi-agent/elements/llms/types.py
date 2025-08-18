from typing import Union, Annotated
from pydantic import Field
from elements.llms.openai.config import OpenAIConfig
from elements.llms.mock.config import MockLLMConfig

# Union type for backward compatibility with blueprints
LLMsSpec = Annotated[
    Union[
        OpenAIConfig,
        MockLLMConfig,
    ],
    Field(discriminator="type")
]
