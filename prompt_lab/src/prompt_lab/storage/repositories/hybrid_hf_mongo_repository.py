"""
hybrid_hf_mongo_repository.py

Uses a HuggingFaceDataHandler for input, MongoDataHandler for processed/skipped/progress,
and defers export logic to an HFExporter.
"""

from typing import Dict, Any, Iterator, Set, List

from .data_repository import DataRepository
from ..datahandler import HuggingFaceDataHandler, MongoDataHandler
from ..exporters import HFExporter
from ..stats import Stats
from pymongo import errors
from prompt_lab.utils import logger
from prompt_lab.prompt import Prompt
from bson import ObjectId


class HybridHFMongoRepository(DataRepository):
    """
    Hybrid repository:
      - input: HuggingFaceDataHandler
      - processed/skipped/progress: MongoDataHandler
      - delegates export to HFExporter
    """

    def __init__(
            self,
            input_handler: HuggingFaceDataHandler,
            processed_handler: MongoDataHandler,
            stats_handler: MongoDataHandler,
            exporter: HFExporter,
            process_id: str = None
    ):
        self.input_handler = input_handler
        self.processed_handler = processed_handler
        self.stats_handler = Stats(stats_handler, process_id=ObjectId(process_id) if process_id else None)
        self.exporter = exporter
        
    # input handler
    def load_input_data(self) -> Iterator[Dict[str, Any]]:
        return self.input_handler.read_data()

    # processed handler
    def save_prompts(self, prompts: List[Dict[str, Any]], increment_callback: callable) -> None:
        """
        Save data to the MongoDB collection with error handling for duplicate keys.

        :param prompts: A list of dictionaries representing the records to save.
        :param increment_callback: A callback to increment the appropriate stats counter.
        """
        # Transform records to use `uuid` as `_id`
        transformed_data = [{**record, "_id": record["uuid"]} for record in prompts]

        for record in transformed_data:
            try:
                self.processed_handler.update_record({"_id": record["_id"]}, {"$set": record}, upsert=True)
                increment_callback()
            except errors.DuplicateKeyError:
                logger.warning(f"DuplicateKeyError: Prompt with _id {record['_id']} already exists. Skipping.")


    def save_pass_prompts(self, prompts: List[Dict[str, Any]]) -> None:
        """
        Save processed pass prompts.
        """
        self.save_prompts(prompts=prompts,
                          increment_callback=self.stats_handler.increment_prompts_pass)

    def save_fail_prompts(self, prompts: List[Dict[str, Any]]) -> None:
        """
        Save processed fail prompts.
        """
        self.save_prompts(prompts=prompts,
                          increment_callback=self.stats_handler.increment_prompts_failed)

    def load_prompts_uuids(self) -> Set[str]:
        """
        Load and return a set of processed UUIDs from the progress handler.

        :return: A set of UUID strings that have been processed.
        """
        # Use projection to fetch only the uuid field
        pass_processed_uuid = {
            uuid_obj["uuid"] for uuid_obj in self.processed_handler.read_data(projection={"uuid": 1, "_id": 0})
        }
        return pass_processed_uuid

    # stats handler
    def update_retry_counter(self, count: int):
        self.stats_handler.increment_prompts_retried(count)

    def update_prompt_generation_counter(self, count: int = 1):
        self.stats_handler.increment_prompts_generated(count)

    def get_elements_size(self) -> int:
        logger.info("[HybridHFMongoRepository] getting number of elements.")
        return self.stats_handler.get_number_of_elements()

    def set_elements_size(self, size) -> None:
        self.stats_handler.set_number_of_elements(size)

    def get_prompts_size(self) -> int:
        logger.info("[HybridHFMongoRepository] getting number of prompts.")
        return self.stats_handler.get_number_of_prompts()

    def get_processed_num(self) -> int:
        return self.stats_handler.get_processed_num()

    def set_prompts_size(self, size) -> None:
        self.stats_handler.set_number_of_prompts(size)

    # output
    def export(self):
        if self.stats_handler.is_done() and not self.stats_handler.is_exported():
            logger.info("All prompts processed - exporting data...")

            # Define a query to filter for documents where "failed" is False
            query = {"failed": False}

            # Retrieve the filtered data and pass it to the exporter
            prompts_iterator = self._iterator_prompts_export(self.processed_handler.read_data(query=query))
            url = self.exporter.export(prompts_iterator)
            self.stats_handler.set_exported(url)

    @classmethod
    def _iterator_prompts_export(cls, record_generator: Iterator[Dict[str, Any]]):
        for record in record_generator:
            record.pop("_id", None)
            yield Prompt.from_dict(**record).export()

    def close(self) -> None:
        self.input_handler.close()
        self.processed_handler.close()
        self.stats_handler.close()
