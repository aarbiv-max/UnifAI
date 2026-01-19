"""Pagination domain models."""
from dataclasses import dataclass
from typing import TypeVar, Generic, List, Optional, Dict, Any

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    """
    Standardized paginated response.
    
    Generic over the data type for type safety.
    Provides consistent structure across all paginated endpoints.
    """
    data: List[T]
    next_cursor: Optional[str]
    has_more: bool
    total: int

    def to_dict(self, data_key: str = "data") -> Dict[str, Any]:
        """
        Serialize the paginated result into a dictionary using a customizable key for the items.
        
        Parameters:
            data_key (str): Key name to use for the items list in the resulting dictionary (e.g., "data", "channels", "documents").
        
        Returns:
            Dict[str, Any]: Dictionary with keys:
                - the provided `data_key`: the page's item list
                - "nextCursor": cursor token for the next page or `None`
                - "hasMore": `True` if more pages are available, `False` otherwise
                - "total": total number of items in the current context
        """
        return {
            data_key: self.data,
            "nextCursor": self.next_cursor,
            "hasMore": self.has_more,
            "total": self.total,
        }

    def map(self, fn) -> "PaginatedResult":
        """
        Apply a function to each item in the paginated data, returning a new PaginatedResult with transformed items while preserving pagination metadata.
        
        Parameters:
            fn (Callable): Function applied to each item in `data`; may change the item type.
        
        Returns:
            PaginatedResult: A new PaginatedResult containing the transformed `data` and the original `next_cursor`, `has_more`, and `total`.
        """
        return PaginatedResult(
            data=[fn(item) for item in self.data],
            next_cursor=self.next_cursor,
            has_more=self.has_more,
            total=self.total,
        )

    def filter(self, predicate) -> "PaginatedResult":
        """
        Create a PaginatedResult containing only items that satisfy the given predicate while preserving pagination metadata.
        
        Parameters:
            predicate (Callable[[T], bool]): Function that returns `True` for items to keep.
        
        Returns:
            PaginatedResult[T]: New paginated result with filtered data and `total` set to the number of retained items.
        """
        filtered = [item for item in self.data if predicate(item)]
        return PaginatedResult(
            data=filtered,
            next_cursor=self.next_cursor,
            has_more=self.has_more,
            total=len(filtered),
        )
