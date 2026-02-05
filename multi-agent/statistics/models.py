from typing import Dict, List, Any
from pydantic import BaseModel, Field


class ResourceCategoryStats(BaseModel):
    """Statistics for resources grouped by category."""
    category: str = Field(..., description="Resource category")
    count: int = Field(..., description="Total count of resources in this category")
    types: Dict[str, int] = Field(default_factory=dict, description="Count of resources by type within this category")


class StatisticsResponse(BaseModel):
    """Response model for aggregated statistics (user-scoped)."""
    totalWorkflows: int = Field(..., description="Total number of workflows/blueprints")
    activeSessions: int = Field(..., description="Number of active sessions")
    totalResources: int = Field(..., description="Total number of resources")
    categoriesInUse: int = Field(..., description="Number of categories with at least one configured resource")
    blueprintSessionCounts: Dict[str, int] = Field(default_factory=dict, description="Dictionary mapping blueprint_id to session count")
    resourcesByCategory: List[ResourceCategoryStats] = Field(default_factory=list, description="List of resource statistics grouped by category")


# ---------- System-wide Statistics Models (for admin dashboard) ----------

class TotalStats(BaseModel):
    """Total statistics for system-wide overview."""
    total_runs: int = Field(..., description="Total number of workflow runs")
    unique_users: int = Field(..., description="Number of unique users")
    avg_runs_per_user: float = Field(..., description="Average runs per user (can be fractional)")


class SystemStatsResponse(BaseModel):
    """Response model for system-wide statistics (admin dashboard)."""
    total_stats: TotalStats = Field(..., description="Total statistics: total_runs, unique_users, avg_runs_per_user")
    status_breakdown: Dict[str, int] = Field(default_factory=dict, description="Breakdown of runs by status")
    active_today: List[Dict[str, Any]] = Field(default_factory=list, description="Users active today")
    active_7days: List[Dict[str, Any]] = Field(default_factory=list, description="Users active in last 7 days")
    active_30days: List[Dict[str, Any]] = Field(default_factory=list, description="Users active in last 30 days")
    top_users: List[Dict[str, Any]] = Field(default_factory=list, description="Top users by total runs")
    top_blueprints: List[Dict[str, Any]] = Field(default_factory=list, description="Most used blueprints")
    time_series: List[Dict[str, Any]] = Field(default_factory=list, description="Time series activity data")
    generated_at: str = Field(..., description="ISO timestamp when statistics were generated")

