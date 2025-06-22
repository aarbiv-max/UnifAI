# mongo_blueprint_repository.py

import pymongo
from uuid import uuid4
from datetime import datetime
from typing import List
from pydantic import ValidationError
from schemas.blueprint.blueprint import BlueprintSpec
from .repository import BlueprintRepository


class MongoBlueprintRepository(BlueprintRepository):
    def __init__(self,
                 mongodb_port: str = "27017",
                 mongodb_ip: str = "localhost",
                 db_name="UnifAI",
                 coll_name="blueprints"):

        mongo_uri = f"mongodb://{mongodb_ip}:{mongodb_port}/"
        client = pymongo.MongoClient(mongo_uri)
        self._col = client[db_name][coll_name]
        # Unique on blueprint_id alone now
        self._col.create_index([("blueprint_id", pymongo.ASCENDING)], unique=True)

    def save(self, spec: BlueprintSpec) -> str:
        new_id = str(uuid4())
        doc = {
            "blueprint_id": new_id,
            "created_at": getattr(spec, "created_at", datetime.utcnow()),
            "updated_at": datetime.utcnow(),
            "spec_dict": spec.model_dump(mode="json"),
        }
        self._col.insert_one(doc)
        return new_id

    def load(self, blueprint_id: str) -> BlueprintSpec:
        doc = self._col.find_one({"blueprint_id": blueprint_id})
        if not doc:
            raise KeyError(f"No blueprint with id={blueprint_id}")
        try:
            return BlueprintSpec.model_validate(doc["spec_dict"])
        except ValidationError as ve:
            raise RuntimeError(f"Corrupt blueprint {blueprint_id}: {ve}")

    def delete(self, blueprint_id: str) -> bool:
        res = self._col.delete_one({"blueprint_id": blueprint_id})
        return res.deleted_count == 1

    def exists(self, blueprint_id: str) -> bool:
        return self._col.count_documents({"blueprint_id": blueprint_id}, limit=1) == 1

    def list_ids(self, skip=0, limit=100, sort_desc=True) -> List[str]:
        cursor = (
            self._col
                .find({}, {"blueprint_id": 1})
                .sort("updated_at", pymongo.DESCENDING if sort_desc else pymongo.ASCENDING)
                .skip(skip)
                .limit(limit)
        )
        return [d["blueprint_id"] for d in cursor]

    def list_specs(self, skip=0, limit=100, sort_desc=True) -> List[BlueprintSpec]:
        cursor = (
            self._col
                .find({})
                .sort("updated_at", pymongo.DESCENDING if sort_desc else pymongo.ASCENDING)
                .skip(skip)
                .limit(limit)
        )
        specs = []
        for d in cursor:
            try:
                specs.append(BlueprintSpec.model_validate(d["spec_dict"]))
            except ValidationError:
                continue
        return specs

    def count(self) -> int:
        return self._col.count_documents({})
