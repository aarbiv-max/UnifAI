import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil
from utils.storage.mongo.mongo_helpers import get_source_service


class SlackStatsProvider:
    def __init__(self):
        # source_service implements both SourceRepository & PipelineRepository
        self._service = get_source_service()

    def _fetch_slack_sources(self) -> List[Dict[str, Any]]:
        """Fetch all SLACK sources enriched with their last pipeline status."""
        return self._service.list_sources_with_status(source_type="SLACK")

    def _aggregate_counts(
        self, sources: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Compute channel counts, message totals, and api calls."""
        total_channels  = len(sources)
        active_channels = sum(1 for s in sources if s.get("status") == "ACTIVE")
        total_messages  = sum(
            s.get("type_data", {}).get("message_count", 0) for s in sources
        )
        api_calls_count = sum(
            s.get("type_data", {}).get("api_calls", 0) for s in sources
        )
        return {
            "totalChannels":   total_channels,
            "activeChannels":  active_channels,
            "totalMessages":   total_messages,
            "apiCallsCount":   api_calls_count,
        }

    def _get_last_sync_at(self, sources: List[Dict[str, Any]]) -> Optional[str]:
        """Return the most recent last_sync_at timestamp (ISO string)."""
        timestamps = [
            s.get("last_sync_at")
            for s in sources
            if s.get("last_sync_at") is not None
        ]
        return max(timestamps) if timestamps else None

    def _get_system_uptime(self) -> str:
        """Format system uptime as "<days>d <hours>h <minutes>m"."""
        # Try /proc/uptime first (Linux), fallback to psutil if available
        try:
            with open("/proc/uptime") as f:
                secs = float(f.readline().split()[0])
        except Exception:
            secs = time.time() - psutil.boot_time()
        days, rem = divmod(int(secs), 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        return f"{days}d {hours}h {minutes}m"

    def get_stats(self) -> Dict[str, Any]:
        """Public method: gather everything into a single dict."""
        sources = self._fetch_slack_sources()
        counts = self._aggregate_counts(sources)
        last_sync = self._get_last_sync_at(sources)
        uptime    = self._get_system_uptime()
        return {
            "id":               1,
            **counts,
            "lastSyncAt":       last_sync,
            "systemUptime":     uptime,
            "updatedAt":        datetime.utcnow().isoformat() + "Z",
        }
