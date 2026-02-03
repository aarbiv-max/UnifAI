"""
Analytics data models.

Pydantic models for analytics response structures.
"""
from typing import Dict, List, Any
from pydantic import BaseModel, Field


class TotalStats(BaseModel):
    """Total statistics for overview."""
    total_runs: int = Field(..., description="Total number of workflow runs")
    unique_users: int = Field(..., description="Number of unique users")
    avg_runs_per_user: float = Field(..., description="Average runs per user (can be fractional)")


class OverviewStatisticsResponse(BaseModel):
    """Response model for system-wide overview statistics."""
    total_stats: TotalStats = Field(..., description="Total statistics: total_runs, unique_users, avg_runs_per_user")
    status_breakdown: Dict[str, int] = Field(default_factory=dict, description="Breakdown of runs by status")
    active_today: List[Dict[str, Any]] = Field(default_factory=list, description="Users active today")
    active_7days: List[Dict[str, Any]] = Field(default_factory=list, description="Users active in last 7 days")
    active_30days: List[Dict[str, Any]] = Field(default_factory=list, description="Users active in last 30 days")
    top_users: List[Dict[str, Any]] = Field(default_factory=list, description="Top users by total runs")
    top_blueprints: List[Dict[str, Any]] = Field(default_factory=list, description="Most used blueprints")
    time_series: List[Dict[str, Any]] = Field(default_factory=list, description="Time series activity data")
    generated_at: str = Field(..., description="ISO timestamp when statistics were generated")
