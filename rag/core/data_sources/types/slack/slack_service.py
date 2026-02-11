"""Slack-specific application service."""
from typing import Dict, List, Optional, Any

from core.data_sources.service import DataSourceService
from core.data_sources.domain.repository import DataSourceRepository
from core.pagination.domain.model import PaginatedResult


class SlackService:
    """
    Application service for Slack-specific operations.
    
    Handles queries and business logic specific to SLACK sources,
    such as retrieving tags from successfully processed channels.
    
    Uses DataSourceService for shared functionality like pipeline stats enrichment.
    """

    def __init__(
        self,
        data_source_service: DataSourceService,
        source_repo: DataSourceRepository,
    ):
        self._data_source_service = data_source_service
        self._source_repo = source_repo

    def get_available_tags(
        self,
        cursor: Optional[str] = None,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> PaginatedResult[Dict[str, str]]:
        """
        Get tags from DONE Slack channels only (for UI dropdowns / retriever config).
        
        Filters to only include tags from successfully processed Slack sources.
        
        Args:
            cursor: Pagination cursor
            limit: Max tags to return
            search: Filter tags by prefix (case-insensitive)
            
        Returns:
            PaginatedResult with tag options [{label, value}]
        """
        # Get all DONE sources
        all_sources = self._source_repo.find_all(source_type="SLACK")
        enriched = self._data_source_service.enrich_with_pipeline_stats(all_sources)
        done_sources = [s for s in enriched if s.get("status") == "DONE"]
        
        # Extract unique tags from DONE sources
        all_tags: set = set()
        for s in done_sources:
            all_tags.update(s.get("tags", []))
        
        # Apply search filter (case-insensitive prefix match)
        if search:
            search_lower = search.lower()
            all_tags = {t for t in all_tags if t.lower().startswith(search_lower)}
        
        # Sort alphabetically and paginate
        sorted_tags = sorted(all_tags)
        skip = int(cursor) if cursor and cursor.isdigit() else 0
        page = sorted_tags[skip:skip + limit]
        
        next_cursor = str(skip + len(page)) if skip + len(page) < len(sorted_tags) else None
        
        return PaginatedResult(
            data=[{"label": t, "value": t} for t in page],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            total=len(sorted_tags),
        )

    def get_available_channels(
        self,
        cursor: Optional[str] = None,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> PaginatedResult[Dict[str, str]]:
        """
        Get embedded Slack channels (DONE status) for UI dropdowns / retriever config.
        
        Args:
            cursor: Pagination cursor
            limit: Max channels to return
            search: Filter channels by name (case-insensitive prefix match)
            
        Returns:
            PaginatedResult with channel options [{name, id}]
        """
        all_sources = self._source_repo.find_all(source_type="SLACK")
        enriched = self._data_source_service.enrich_with_pipeline_stats(all_sources)
        done_sources = [s for s in enriched if s.get("status") == "DONE"]
        
        # Build channel list
        channels = [
            {"name": s.get("source_name", ""), "id": s.get("source_id", "")}
            for s in done_sources
        ]
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            channels = [c for c in channels if c["name"].lower().startswith(search_lower)]
        
        # Sort by name
        channels.sort(key=lambda c: c["name"].lower())
        
        skip = int(cursor) if cursor and cursor.isdigit() else 0
        page = channels[skip:skip + limit]
        
        next_cursor = str(skip + len(page)) if skip + len(page) < len(channels) else None
        
        return PaginatedResult(
            data=page,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            total=len(channels),
        )
