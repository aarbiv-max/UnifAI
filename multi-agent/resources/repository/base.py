from abc import ABC, abstractmethod
from typing import List
from resources.models import ResourceDoc, ResourceQuery


class ResourceRepository(ABC):
    @abstractmethod
    def save(self, doc: ResourceDoc) -> str:
        """Insert a new resource document."""
        ...

    @abstractmethod
    def update(self, doc: ResourceDoc) -> str:
        """Update an existing resource document."""
        ...

    @abstractmethod
    def get(self, rid: str) -> ResourceDoc:
        """Retrieve a resource document by ID."""
        ...

    @abstractmethod
    def delete(self, rid: str) -> None:
        """Delete a resource document by ID."""
        ...

    @abstractmethod
    def find_by_name(self, user_id: str, category: str, type: str, name: str) -> ResourceDoc | None:
        """Find a resource document by alias."""
        ...

    @abstractmethod
    def find_resources(self, query: ResourceQuery) -> List[ResourceDoc]:
        """Find resources based on query criteria with pagination."""
        ...

    @abstractmethod
    def count_resources(self, query: ResourceQuery) -> int:
        """Count resources matching query criteria."""
        ...

    @abstractmethod
    def count(self, user_id: str, filter: dict) -> int:
        """Count documents matching a filter."""
        ...

    @abstractmethod
    def meta(self, rid: str) -> tuple[str, str]: ...

    @abstractmethod
    def count_nested(self, rid: str) -> int: ...

    @abstractmethod
    def list_nested_usage(self, rid: str) -> List[str]:
        """
        Return resource IDs whose `nested_refs` array contains `rid`
        (i.e. the resource depends on `rid` inside its own config).
        """

    @abstractmethod
    def exists(self, rid: str) -> bool: ...
