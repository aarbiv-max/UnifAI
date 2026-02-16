"""
Database-agnostic DTOs for repository operations.
These models abstract away database-specific formats from business logic.
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class GroupedCount(BaseModel):
    """
    Database-agnostic grouped count result.
    
    Abstracts MongoDB's {"_id": {...}, "count": N} format into a clean DTO
    that can work with any database backend.
    
    Example:
        # MongoDB returns: {"_id": {"category": "llm", "type": "openai"}, "count": 5}
        # DTO provides:    GroupedCount(fields={"category": "llm", "type": "openai"}, count=5)
    """
    fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Grouped field values (e.g., {'category': 'llm', 'type': 'openai'})"
    )
    count: int = Field(
        ...,
        description="Count of documents matching the grouped fields"
    )
    
    def get(self, field: str, default: Any = None) -> Any:
        """
        Get a grouped field value.
        
        Args:
            field: The field name to retrieve
            default: Default value if field doesn't exist
            
        Returns:
            The field value or default
        """
        return self.fields.get(field, default)
    
    def __getitem__(self, field: str) -> Any:
        """Allow dict-like access to fields."""
        return self.fields[field]
    
    def __contains__(self, field: str) -> bool:
        """Allow 'in' operator for checking field existence."""
        return field in self.fields


class TimeSeriesPoint(BaseModel):
    """
    Single data point in a time series.
    
    Used for session activity charts on admin dashboards.
    The period granularity (hourly, daily, monthly) is determined
    by the repository implementation based on the requested time range.
    """
    period: str = Field(
        ...,
        description="Time period label (e.g., '2024-01-15', '2024-01-15 14:00', '2024-01')"
    )
    count: int = Field(
        ...,
        description="Number of sessions in this period"
    )


class SystemAnalyticsData(BaseModel):
    """
    Aggregated system analytics data returned by the repository layer.
    
    Groups session data by user+status and user+blueprint for building
    admin dashboard views (active users, top blueprints, etc.).
    
    The user_blueprint_counts field serves double duty:
    - User perspective: which blueprints did each user run?
    - Blueprint perspective: which users ran each blueprint?
    Both views are derived from the same (user_id, blueprint_id) grouping.
    
    Implementations should optimize for efficiency (e.g., batching
    multiple aggregations into a single database operation).
    """
    user_status_counts: List[GroupedCount] = Field(
        default_factory=list,
        description="Sessions grouped by user_id and status"
    )
    user_blueprint_counts: List[GroupedCount] = Field(
        default_factory=list,
        description="Sessions grouped by user_id and blueprint_id (used for both user and blueprint views)"
    )

