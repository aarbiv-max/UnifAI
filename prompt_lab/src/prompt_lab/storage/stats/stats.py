from typing import Dict, Any


class Stats:
    """
    Generic tracker for prompts progress, independent of the underlying storage.
    """

    DEFAULT_VALUES = {
        "type": "progress_data",
        "number_of_elements": 0,
        "number_of_prompts": 0,
        "prompts_retried": 0,
        "prompts_failed": 0,
        "prompts_pass": 0,
        "prompts_processed": 0,
        "exported": "",
    }

    def __init__(self, statistics_handler, process_id):
        """
        :param statistics_handler: A MongoDataHandler instance for managing progress data.
        """
        self.statistics_handler = statistics_handler
        self.process_id = process_id
        self._initialize_progress_data()

    def _initialize_progress_data(self) -> None:
        """
        Ensure progress data exists in the storage, initializing it if necessary.
        """        
        existing_data = list(self.statistics_handler.read_data(query={"_id": self.process_id}))

        if not existing_data:
            # Generate a new document with self.process_id as _id
            new_record = {"_id": self.process_id, **self.DEFAULT_VALUES}
            self.statistics_handler.append_record(new_record)


    def _validate_key(self, key: str) -> None:
        """
        Validate if a key is part of the default values.

        :param key: The key to validate.
        :raises ValueError: If the key is invalid.
        """
        if key not in self.DEFAULT_VALUES:
            raise ValueError(f"Invalid progress key: {key}")

    def sync_prompts_generated_with_processed(self) -> None:
        """
        Sync `prompts_generated` to be equal to `prompts_processed` in the database.
        """
        progress_data = self.get_stats()
        prompts_processed = progress_data.get("prompts_processed", 0)

        self.statistics_handler.update_record(
            query={"_id": self.process_id},
            update={"$set": {"prompts_generated": prompts_processed}}
        )

    def increment(self, key: str, amount: int = 1) -> None:
        """
        Increment a specific progress key directly in the database.
        """
        self._validate_key(key)
        self.statistics_handler.update_record(
            query={"_id": self.process_id},
            update={"$inc": {key: amount}}
        )

    def set_value(self, key: str, value: Any) -> None:
        """
        Set a specific progress key to a specific value directly in the database.
        """
        self._validate_key(key)
        self.statistics_handler.update_record(
            query={"_id": self.process_id},
            update={"$set": {key: value}}
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Retrieve the current progress data directly from the database.
        """
        
        progress_data = list(self.statistics_handler.read_data(query={"_id": self.process_id}))

        if not progress_data:
            raise RuntimeError("Progress data not found in the database.")

        return progress_data[0]

    def reset_progress(self) -> None:
        """
        Reset all progress values to their default state directly in the database.
        """
        self.statistics_handler.update_record(
            query={"_id": self.process_id},
            update={"$set": self.DEFAULT_VALUES}
        )

    def increment_with_processed(self, key: str, amount: int = 1) -> None:
        """
        Increment a specific key and also increment `prompts_processed`.
        
        :param key: The key to increment.
        :param amount: The amount to increment by.
        """
        self.increment(key, amount)
        self.increment("prompts_processed", amount)

    # Convenience increment methods
    def increment_prompts_failed(self, amount: int = 1) -> None:
        self.increment_with_processed("prompts_failed", amount)

    def increment_prompts_pass(self, amount: int = 1) -> None:
        self.increment_with_processed("prompts_pass", amount)

    def increment_prompts_generated(self, amount: int = 1) -> None:
        self.increment("prompts_generated", amount)

    def increment_prompts_retried(self, amount: int = 1) -> None:
        self.increment("prompts_retried", amount)

    def set_number_of_elements(self, value: int) -> None:
        self.set_value("number_of_elements", value)

    def set_number_of_prompts(self, value: int) -> None:
        self.set_value("number_of_prompts", value)

    def set_exported(self, url: str) -> None:
        self.set_value("exported", url)

    def is_done(self) -> bool:
        """
        Check if all generated prompts have been processed.
        
        This queries the database to ensure the latest data is used.
        
        :return: True if done, False otherwise.
        """
        progress_data = self.get_stats()
        number_of_prompts = progress_data.get("number_of_prompts", 0)
        prompts_processed = progress_data.get("prompts_processed", 0)

        return number_of_prompts == prompts_processed and number_of_prompts != 0

    def get_number_of_elements(self) -> int:
        """
        Retrieve the current value of 'number_of_elements' directly from the database.
        
        :return: The value of 'number_of_elements'.
        """
        return self.get_stats().get("number_of_elements", 0)

    def get_number_of_prompts(self) -> int:
        """
        Retrieve the current value of 'number_of_prompts' directly from the database.
        
        :return: The value of 'number_of_prompts'.
        """
        return self.get_stats().get("number_of_prompts", 0)

    def get_processed_num(self) -> int:
        """
        Retrieve the current value of 'prompts_processed' directly from the database.
        
        :return: The value of 'prompts_processed'.
        """
        return self.get_stats().get("prompts_processed", 0)

    def is_exported(self) -> bool:
        return bool(self.get_stats().get("exported", ""))

    def close(self):
        """
        Close the MongoDataHandler.
        """
        self.statistics_handler.close()
