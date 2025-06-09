import os
from typing import Iterator, Dict, Any
from huggingface_hub import HfApi, HfFolder
import pandas as pd
from datasets import Dataset
import tempfile
import json
from prompt_lab.utils import logger


class HFExporter:
    """
    Class for exporting data to Hugging Face Hub.
    Supports uploading datasets in chunks and optionally naming the file in the repository.
    """

    def __init__(self, repo_id: str, file_name: str = None, token: str = None, batch_size: int = 1000,
                 export_format: str = "json"):
        """
        Initialize the HFExporter.

        Args:
            repo_id (str): The Hugging Face repo ID in the format <user>/<dataset_name>.
            file_name (str, optional): File name for the dataset in the repository.
            token (str, optional): Authentication token for Hugging Face.
            batch_size (int, optional): Number of records to process in each batch. Defaults to 1000.
            export_format (str, optional): Format for exporting the dataset ("parquet" or "json"). Defaults to "parquet".
        """
        self.repo_id = repo_id
        self.file_name = file_name
        self.token = token or HfFolder.get_token()
        if not self.token:
            raise RuntimeError("No Hugging Face token found. Please login with `huggingface-cli login`.")
        self.batch_size = batch_size
        self.export_format = export_format.lower()
        if self.export_format not in ["parquet", "json"]:
            raise ValueError("export_format must be either 'parquet' or 'json'.")
        self.api = HfApi()

    def _chunked_generator(self, generator: Iterator[Dict[str, Any]], size: int):
        """
        Yield chunks of data from a generator.

        Args:
            generator (Iterator[Dict[str, Any]]): The record generator.
            size (int): Size of each chunk.
        """
        chunk = []
        for record in generator:
            chunk.append(record)
            if len(chunk) == size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def _save_to_tempfile(self, dataset: Dataset) -> str:
        """
        Save the dataset to a temporary file in the specified format.

        Args:
            dataset (Dataset): The Hugging Face dataset to save.

        Returns:
            str: Path to the temporary file.
        """
        temp_file = tempfile.NamedTemporaryFile(suffix=f".{self.export_format}", delete=False)

        if self.export_format == "parquet":
            dataset.to_parquet(temp_file.name)
        elif self.export_format == "json":
            with open(temp_file.name, "w", encoding="utf-8") as f:
                f.write("[\n")
                first = True
                for record in dataset:
                    clean_record = {k: v for k, v in record.items() if v is not None}
                    if not first:
                        f.write(",\n")
                    f.write(json.dumps(clean_record, indent=4, ensure_ascii=False))
                    first = False
                f.write("\n]")

        logger.debug(f"Dataset saved locally to {temp_file.name}.")
        return temp_file.name

    def _upload_to_hub(self, file_path: str):
        """
        Upload the file to the Hugging Face Hub.

        Args:
            file_path (str): Path to the file.
        """
        if not self.file_name:
            raise ValueError("file_name must be specified to upload the file to the repository with its extension.")

        # Ensure the file name has the correct extension
        if not self.file_name.endswith(f".{self.export_format}"):
            self.file_name += f".{self.export_format}"

        logger.info(f"Uploading dataset to {self.repo_id} with file name: {self.file_name}.")

        # Upload the file to the repository
        self.api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=self.file_name,
            repo_id=self.repo_id,
            repo_type="dataset",
            token=self.token,
            commit_message=f"Upload {self.file_name}",
        )
        url = f"https://huggingface.co/datasets/{self.repo_id}/blob/main/{self.file_name}"
        logger.info(
            f"Dataset uploaded to {url}")
        return url

    def export(self, record_generator: Iterator[Dict[str, Any]]) -> str:
        """
        Export records from a generator to the Hugging Face Hub.

        Args:
            record_generator (Iterator[Dict[str, Any]]): A generator yielding records.
        """
        logger.info("Starting dataset export...")
        full_dataset = None

        for i, batch in enumerate(self._chunked_generator(record_generator, self.batch_size), start=1):
            logger.debug(f"Processing batch {i} with size {len(batch)}.")
            batch_df = pd.DataFrame(batch)
            batch_dataset = Dataset.from_pandas(batch_df)

            if full_dataset is None:
                full_dataset = batch_dataset
            else:
                full_dataset = Dataset.from_pandas(
                    pd.concat([full_dataset.to_pandas(), batch_df], ignore_index=True)
                )

        if full_dataset is None:
            logger.info("No records to export.")
            return ""

        temp_file_path = self._save_to_tempfile(full_dataset)
        try:
            return self._upload_to_hub(temp_file_path)
        finally:
            logger.debug(f"Cleaning up temporary file: {temp_file_path}")
            os.remove(temp_file_path)  # Correctly use os.remove
