from typing import Union, Annotated
from pydantic import Field
from elements.retrievers.docs.config import DocsRetrieverConfig
from elements.retrievers.slack.config import SlackRetrieverConfig

# Union type for backward compatibility with blueprints
RetrieversSpec = Annotated[
    Union[
        DocsRetrieverConfig,
        SlackRetrieverConfig,
    ],
    Field(discriminator="type")
]
