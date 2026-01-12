"""
resources/validation/

DEPRECATED: DependencyResolver has been moved to resources/resolver.py

This package is kept for backwards compatibility only.
Please update imports to use: from resources.resolver import DependencyResolver
"""

# Re-export from new location for backwards compatibility
from resources.resolver import DependencyResolver

__all__ = ["DependencyResolver"]
