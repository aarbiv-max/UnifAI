from enum import Enum
from dataclasses import dataclass
from typing import List


class Identifier(str, Enum):
    """Machine-readable key for the Docs Retriever."""
    TYPE = "docs"


@dataclass(frozen=True)
class Meta:
    name: str
    description: str
    tags: List[str]


META = Meta(
    name="Docs Retriever",
    description="Fetches relevant document passages for a query",
    tags=["retriever", "docs", "search", "query", "information retrieval"],
)
