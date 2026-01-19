"""MongoDB adapter for SlackChannelRepository port."""
from typing import Optional, List, Dict, Any

from pymongo.collection import Collection

from domain.slack_channel.model import SlackChannel
from domain.slack_channel.repository import SlackChannelRepository
from domain.pagination import PaginatedResult
from infrastructure.mongo.pagination_builder import PaginatedQueryBuilder
from shared.logger import logger


class MongoSlackChannelRepository(SlackChannelRepository):
    """MongoDB implementation of the SlackChannelRepository port."""

    # Mapping from API types to internal types
    _TYPE_MAP = {
        "private_channel": "Private",
        "public_channel": "Public",
    }

    def __init__(self, collection: Collection):
        """
        Initialize the repository with a PyMongo collection.
        
        Parameters:
            collection (Collection): PyMongo Collection used to persist and query Slack channel documents.
        """
        self._col = collection

    def find_by_channel_id(self, channel_id: str) -> Optional[SlackChannel]:
        """
        Retrieve a SlackChannel by its Slack channel identifier.
        
        Parameters:
            channel_id (str): The Slack channel's unique identifier.
        
        Returns:
            SlackChannel: The channel object if found, `None` if no matching document exists or an error occurred.
        """
        try:
            doc = self._col.find_one({"channel_id": channel_id})
            return SlackChannel.from_dict(doc) if doc else None
        except Exception as e:
            logger.error(f"Error finding channel {channel_id}: {e}")
            return None

    def find_paginated(
        self,
        project_id: str,
        types: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> PaginatedResult[Dict[str, Any]]:
        """
        Retrieve a paginated list of channel documents for a project.
        
        Performs a paginated query filtered by the given project_id, optionally restricted to channel types (comma-separated, mapped via internal type map) and/or text-searched against channel_name. Results are sorted alphabetically by channel_name and paginated using the provided cursor and limit.
        
        Parameters:
            project_id (str): ID of the project whose channels to query.
            types (Optional[str]): Comma-separated external channel types to include; each value is trimmed and mapped to the repository's internal type names.
            cursor (Optional[str]): Pagination cursor identifying the page start.
            limit (int): Maximum number of documents to return.
            search (Optional[str]): Text to match against the channel_name field.
        
        Returns:
            PaginatedResult[Dict[str, Any]]: Paginated result containing channel documents and pagination metadata.
        """
        builder = (PaginatedQueryBuilder(self._col)
            .with_filter({"project_id": project_id})
            .with_search(search, field="channel_name")
            .with_sort("channel_name", desc=False)  # Alphabetical
            .paginate(cursor, limit))
        
        if types:
            type_list = [self._TYPE_MAP.get(t.strip(), t.strip()) 
                        for t in types.split(",")]
            builder.with_filter({"type": {"$in": type_list}})
        
        return builder.documents()

    def exists_for_project(self, project_id: str) -> bool:
        """
        Determine whether any channels exist for the given project.
        
        Returns:
            `true` if at least one channel document with the provided `project_id` exists, `false` otherwise.
        """
        return self._col.count_documents({"project_id": project_id}) > 0

    def save(self, channel: SlackChannel) -> bool:
        """
        Insert the given SlackChannel into the repository collection.
        
        Parameters:
            channel (SlackChannel): Channel to persist.
        
        Returns:
            bool: True if the channel was successfully inserted, False otherwise.
        """
        try:
            self._col.insert_one(channel.to_dict())
            return True
        except Exception as e:
            logger.error(f"Error inserting channel {channel.channel_id}: {e}")
            return False

    def save_many(self, channels: List[SlackChannel]) -> None:
        """
        Insert multiple SlackChannel records into the MongoDB collection in a single batch.
        
        Parameters:
            channels (List[SlackChannel]): Channels to insert; if empty, no operation is performed.
        """
        if channels:
            docs = [ch.to_dict() for ch in channels]
            self._col.insert_many(docs)
            logger.info(f"Cached {len(channels)} channels to MongoDB")

    def update_membership(self, channel_id: str, is_member: bool, timestamp: float) -> bool:
        """
        Set the repository membership status and update the last-updated timestamp for a Slack channel.
        
        Parameters:
            channel_id (str): Slack channel identifier to update.
            is_member (bool): Whether the app is a member of the channel.
            timestamp (float): POSIX timestamp to store as the channel's last updated time.
        
        Returns:
            bool: `True` if a document was modified, `False` otherwise.
        """
        try:
            result = self._col.update_one(
                {"channel_id": channel_id},
                {"$set": {"is_app_member": is_member, "last_updated": timestamp}},
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating membership for channel {channel_id}: {e}")
            return False

    def delete_by_project(self, project_id: str) -> int:
        """
        Delete all Slack channel documents belonging to the given project.
        
        Parameters:
            project_id (str): Identifier of the project whose channels should be removed.
        
        Returns:
            int: Number of documents deleted.
        """
        result = self._col.delete_many({"project_id": project_id})
        logger.info(f"Cleared {result.deleted_count} existing channels for project {project_id}")
        return result.deleted_count