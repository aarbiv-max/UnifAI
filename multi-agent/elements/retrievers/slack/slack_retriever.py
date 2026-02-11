import requests
from typing import Any, Dict, List, Optional
from elements.retrievers.common.base_retriever import BaseRetriever
from pydantic import HttpUrl
from core.context import get_current_context


class SlackRetriever(BaseRetriever):
    """
    Calls an external Slack‐query API to fetch matching messages.
    """

    def __init__(self, api_url: HttpUrl,
                 top_k_results: int,
                 threshold: float,
                 channels: Optional[List[Dict]] = None,
                 tags: Optional[List[str]] = None):
        self.api_url = str(api_url)
        self.top_k = top_k_results
        self.threshold = threshold
        self.channels = channels
        self.tags = tags

    def retrieve(self, query: str) -> Any:
        context = get_current_context()

        params = {
            "query": query,
            "top_k_results": self.top_k,
            "scope": context.scope,
            "loggedInUser": context.logged_in_user
        }

        # Extract channel IDs from channels list
        channel_ids = [ch['id'] for ch in self.channels] if self.channels else None
        if channel_ids:
            params["channelIds"] = channel_ids
        if self.tags:
            params["tags"] = self.tags

        resp = requests.get(self.api_url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if "search_results" in data:
            data = data["search_results"]
        if isinstance(data, list):
            return [item for item in data if item.get("score", 0.0) >= self.threshold]
        return data
