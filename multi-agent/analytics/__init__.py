"""
Analytics module for system-wide workflow statistics and insights.

This module provides comprehensive analytics for:
- Workflow execution statistics
- User activity tracking
- Blueprint usage metrics
- Time series activity data

Follows the ShareService pattern with dedicated repository and service layers.
"""
from .service import AnalyticsService
from .repository.mongo_repository import MongoAnalyticsRepository
from .models import OverviewStatisticsResponse, TotalStats

__all__ = [
    'AnalyticsService',
    'MongoAnalyticsRepository',
    'OverviewStatisticsResponse',
    'TotalStats',
]
