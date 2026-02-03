"""
Analytics repository implementations.
"""
from .base import AnalyticsRepository
from .mongo_repository import MongoAnalyticsRepository

__all__ = ['AnalyticsRepository', 'MongoAnalyticsRepository']
