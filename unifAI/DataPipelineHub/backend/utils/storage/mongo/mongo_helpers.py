from flask import current_app
from utils.storage.mongo.mongo_storage import MongoStorage, SourceService 

mongo_uri = "mongodb://ae8f0dd8e6cd046539c3f0b7c6a75f13-508991814.us-east-1.elb.amazonaws.com:27017"

def get_mongo_storage() -> MongoStorage:
    try:
        return current_app.mongo_storage
    except RuntimeError:
        return MongoStorage(mongo_uri)


def get_source_service() -> SourceService:
    try:
        return current_app.source_service
    except RuntimeError:
        store = MongoStorage(mongo_uri)
        return SourceService(store, store)
