"""Template repository package."""

from templates.repository.repository import TemplateRepository
from templates.repository.mongo_repository import MongoTemplateRepository

__all__ = [
    "TemplateRepository",
    "MongoTemplateRepository",
]
