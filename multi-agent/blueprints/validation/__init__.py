"""
blueprints/validation/

DEPRECATED: BlueprintConfigCollector has been moved to blueprints/collector.py

This package is kept for backwards compatibility only.
Please update imports to use: from blueprints.collector import BlueprintConfigCollector
"""

# Re-export from new location for backwards compatibility
from blueprints.collector import BlueprintConfigCollector

__all__ = ["BlueprintConfigCollector"]
