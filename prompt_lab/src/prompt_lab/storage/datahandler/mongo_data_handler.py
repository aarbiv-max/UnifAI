"""
mongo_data_handler.py

A DataHandler implementation that stores and retrieves data from MongoDB.
"""

from typing import Any, Dict, Iterator, List, Optional
from pymongo import MongoClient
from .data_handler import DataHandler


class MongoDataHandler(DataHandler):
    """
    A DataHandler that uses a MongoDB collection to store records.
    Each call to append_record inserts a document.
    read_data iterates over all documents in the collection.
    """

    def append_to_object(self, key: str, val: Any) -> None:
        pass

    def __init__(
            self,
            uri: str,
            db_name: str,
            collection_name: str,
            query: Dict[str, Any] = None
    ):
        """
        :param uri: MongoDB connection URI (e.g., "mongodb://localhost:27017/").
        :param db_name: Name of the MongoDB database.
        :param collection_name: Name of the collection to store/retrieve records.
        :param query: (Optional) A default MongoDB filter to apply when reading data.
        """
        self.uri = uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.query = query or {}
        self.client = MongoClient(self.uri)
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def read_data(self,
                  query: Optional[Dict[str, Any]] = None,
                  projection: Optional[Dict[str, int]] = None) -> Iterator[Dict[str, Any]]:
        """
        Stream data from the MongoDB collection as dictionaries.

        :param query: Optional MongoDB query filter.
        :param projection: Optional MongoDB projection to specify fields to retrieve.
        :return: Iterator of dictionaries representing the documents.
        """
        query = query or {}  # Default to an empty query if none provided
        cursor = self.collection.find(query, projection)
        for doc in cursor:
            # If _id is present, convert it to string for convenience
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            yield doc

    def append_record(self, record: Dict[str, Any]) -> None:
        """
        Insert a single record (document) into the collection.
        """
        id = self.collection.insert_one(record)
        return id

    def append_records(self, records: List[Dict[str, Any]]) -> None:
        """
        Insert multiple records at once for efficiency.
        """
        if records:
            self.collection.insert_many(records, ordered=False)

    def update_record(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> None:
        """
        Update a single record in the collection based on a query.

        :param query: MongoDB query filter to find the record to update.
        :param update: MongoDB update document specifying the updates.
        :param upsert: If True, create a new document if no document matches the query.
        """
        self.collection.update_one(query, update, upsert=upsert)

    def close(self) -> None:
        """
        Close the MongoDB client connection.
        """
        self.client.close()
