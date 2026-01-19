"""
Fluent builder for paginated MongoDB queries.

Single source of truth for all pagination logic.
Supports documents and distinct values modes.
"""
import re
from typing import Optional, Dict, Any, List

from pymongo.collection import Collection

from domain.pagination import PaginatedResult
from shared.logger import logger


class PaginatedQueryBuilder:
    """
    Fluent builder for paginated MongoDB queries.
    
    Single source of truth for all pagination logic across repositories.
    Supports two modes:
    - documents(): Return full documents
    - distinct(field): Return unique values from a field
    
    Example:
        result = (PaginatedQueryBuilder(collection)
            .with_filter({"source_type": "DOCUMENT"})
            .with_search("test", field="source_name")
            .with_sort("created_at", desc=True)
            .paginate(cursor="10", limit=50)
            .documents())
        
        # Returns PaginatedResult with data, next_cursor, has_more, total
    """

    def __init__(self, collection: Collection):
        """
        Create a PaginatedQueryBuilder bound to a PyMongo collection and initialize default pagination state.
        
        Parameters:
            collection (Collection): PyMongo collection used as the query target.
        """
        self._col = collection
        self._filters: List[Dict[str, Any]] = []
        self._sort_field = "_id"
        self._sort_order = -1
        self._cursor: Optional[str] = None
        self._limit = 50
        self._search_regex: Optional[str] = None
        self._search_field = "name"

    # ══════════════════════════════════════════════════════════════════════════
    # Fluent Configuration
    # ══════════════════════════════════════════════════════════════════════════

    def with_filter(self, filter_dict: Dict[str, Any]) -> "PaginatedQueryBuilder":
        """
        Add a MongoDB filter to the builder's criteria.
        
        Parameters:
            filter_dict (Dict[str, Any]): Query filter to append; ignored if falsy.
        
        Returns:
            self: The builder instance for chaining.
        """
        if filter_dict:
            self._filters.append(filter_dict)
        return self

    def with_search(
        self, 
        pattern: Optional[str], 
        field: str = "name"
    ) -> "PaginatedQueryBuilder":
        """
        Configure a start-anchored, case-insensitive regex search on a field.
        
        Parameters:
            pattern (Optional[str]): Search pattern to apply; if provided, it will be used as a regex (the raw string is stored and will be treated as a search pattern). Passing `None` disables the search.
            field (str): Document field to apply the search against. Defaults to `"name"`.
        
        Returns:
            PaginatedQueryBuilder: Self to allow method chaining.
        """
        self._search_regex = pattern
        self._search_field = field
        return self

    def with_sort(
        self, 
        field: str, 
        desc: bool = True
    ) -> "PaginatedQueryBuilder":
        """
        Configure the sort field and direction for subsequent queries.
        
        Parameters:
            field (str): The document field to sort by.
            desc (bool): If True, sort descending (newest first); if False, sort ascending.
        
        Returns:
            PaginatedQueryBuilder: The builder instance for method chaining.
        """
        self._sort_field = field
        self._sort_order = -1 if desc else 1
        return self

    def paginate(
        self, 
        cursor: Optional[str] = None, 
        limit: int = 50
    ) -> "PaginatedQueryBuilder":
        """
        Configure pagination parameters for the query builder.
        
        Parameters:
            cursor (Optional[str]): Opaque cursor from a previous response; interpreted as a numeric skip count when numeric.
            limit (int): Maximum number of items to return.
        
        Returns:
            PaginatedQueryBuilder: The builder instance for method chaining.
        """
        self._cursor = cursor
        self._limit = limit
        return self

    # ══════════════════════════════════════════════════════════════════════════
    # Execution Methods (terminal operations)
    # ══════════════════════════════════════════════════════════════════════════

    def documents(self) -> PaginatedResult[Dict[str, Any]]:
        """
        Return paginated full documents matching the configured query.
        
        Returns:
            PaginatedResult[Dict[str, Any]]: A paginated result containing the list of matching document dictionaries, the next cursor (string or None), a has_more flag, and the total matching count.
        """
        return self._execute(distinct_field=None)

    def distinct(self, field: str) -> PaginatedResult[str]:
        """
        Return distinct values for a specified field as a paginated result.
        
        Parameters:
            field (str): Dot-notation path to the target field (e.g., "tags" or "metadata.category").
        
        Returns:
            PaginatedResult[str]: Unique string values for the field along with pagination metadata (`next_cursor`, `has_more`, `total`).
        """
        return self._execute(distinct_field=field)

    # ══════════════════════════════════════════════════════════════════════════
    # Internal Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_cursor(self) -> int:
        """
        Convert the builder's cursor string to a numeric skip offset.
        
        Returns:
            skip (int): Numeric skip offset derived from the builder's `_cursor`; returns 0 if `_cursor` is absent or not composed solely of digits.
        """
        if self._cursor and self._cursor.isdigit():
            return int(self._cursor)
        return 0

    def _build_search_match(self, field: str) -> Dict[str, Any]:
        """
        Builds a MongoDB regex match for the configured search pattern on the given field.
        
        Parameters:
            field (str): Document field to apply the search regex against.
        
        Returns:
            dict: A MongoDB match expression that performs a start-anchored, case-insensitive regex on `field`, or an empty dict if no search pattern is configured.
        """
        if not self._search_regex:
            return {}
        pattern = f"^{re.escape(self._search_regex)}"
        return {field: {"$regex": pattern, "$options": "i"}}

    def _compute_pagination(
        self, 
        skip: int, 
        fetched_count: int, 
        total: int
    ) -> tuple:
        """
        Determine the next pagination cursor and whether more results remain.
        
        Returns:
            tuple: `next_cursor` is the string representation of `skip + fetched_count` when more results exist, `None` otherwise; `has_more` is `True` if `total` is greater than `skip + fetched_count`, `False` otherwise.
        """
        next_pos = skip + fetched_count
        if next_pos < total:
            return str(next_pos), True
        return None, False

    def _execute(self, distinct_field: Optional[str]) -> PaginatedResult:
        """
        Execute the configured query and return a paginated result of documents or distinct field values.
        
        When `distinct_field` is provided, the query returns unique, non-null, non-empty values for that field; otherwise it returns full documents matching the configured filters, search, and sort. The result includes a data slice, the total matching count, a next cursor for pagination, and a boolean indicating if more items remain.
        
        Parameters:
            distinct_field (Optional[str]): If set, return distinct values from this field instead of full documents.
        
        Returns:
            PaginatedResult: Contains:
                - data: list of documents (when `distinct_field` is None) or list of distinct field values (when provided).
                - next_cursor: string cursor for the next page, or `None` if there is no further data.
                - has_more: `true` if more items remain after this page, `false` otherwise.
                - total: integer total count of matching items.
        """
        skip = self._parse_cursor()
        pipeline = []

        # Merge all filters into single $match
        if self._filters:
            merged_filter = {}
            for f in self._filters:
                merged_filter.update(f)
            pipeline.append({"$match": merged_filter})

        if distinct_field:
            # ─── DISTINCT VALUES MODE ─────────────────────────────────────
            pipeline.append({"$unwind": f"${distinct_field}"})
            
            search_match = self._build_search_match(distinct_field)
            if search_match:
                pipeline.append({"$match": search_match})
            else:
                # Filter out null/empty values
                pipeline.append({"$match": {
                    distinct_field: {"$exists": True, "$ne": None, "$ne": ""}
                }})
            
            pipeline.append({"$group": {"_id": f"${distinct_field}"}})
            pipeline.append({"$sort": {"_id": self._sort_order}})
        else:
            # ─── FULL DOCUMENTS MODE ──────────────────────────────────────
            search_match = self._build_search_match(self._search_field)
            if search_match:
                pipeline.append({"$match": search_match})
            pipeline.append({"$sort": {self._sort_field: self._sort_order}})

        # Facet for efficient count + data in single query
        pipeline.append({
            "$facet": {
                "metadata": [{"$count": "total"}],
                "data": [{"$skip": skip}, {"$limit": self._limit}]
            }
        })

        try:
            result = list(self._col.aggregate(pipeline))

            # Parse aggregation result
            total = 0
            items = []
            if result and result[0]:
                facet = result[0]
                if facet.get("metadata"):
                    total = facet["metadata"][0]["total"]
                
                if distinct_field:
                    items = [item["_id"] for item in facet.get("data", [])]
                else:
                    items = facet.get("data", [])

            next_cursor, has_more = self._compute_pagination(skip, len(items), total)

            return PaginatedResult(
                data=items,
                next_cursor=next_cursor,
                has_more=has_more,
                total=total
            )
        except Exception as e:
            logger.error(f"Error in paginated query: {e}")
            return PaginatedResult(data=[], next_cursor=None, has_more=False, total=0)
