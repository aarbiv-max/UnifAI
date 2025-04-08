from prompt_lab.core import PromptLaunchpad, PromptOrbiter, PromptLanding
from prompt_lab.config import ConfigManager
from prompt_lab.utils import TokenizerUtils
from prompt_lab.utils.util import get_mongo_url
from prompt_lab.storage import HybridHFMongoRepository, HuggingFaceDataHandler, MongoDataHandler, HFExporter
from prompt_lab.llm import VLLMClient
from typing import List


def initialize_config():
    return ConfigManager()


def initialize_tokenizer():
    """Initialize and return configuration and tokenizer."""
    config = initialize_config()
    tokenizer = TokenizerUtils(
        tokenizer_path=config.get("tokenizer_path"),
        max_context_length=config.get_as_int("model_max_context_length"),
        max_generation_length=config.get_as_int("model_max_generation_length"),
    )
    return tokenizer


def initialize_mongo_handlers_and_repository(config, db_name):
    """Initialize MongoDB data handlers and repository."""
    mongo_uri = get_mongo_url()
    processed_handler = MongoDataHandler(uri=mongo_uri, db_name=db_name, collection_name="processedPrompts")
    stats_handler = MongoDataHandler(uri=mongo_uri, db_name=db_name, collection_name="statistics")

    repository = HybridHFMongoRepository(
        input_handler=HuggingFaceDataHandler(
            repo_id=config.get("input_dataset_repo"),
            file_name=config.get("input_dataset_file_name"),
            split="train",
            streaming=True
        ) if config.get("input_dataset_repo") else None,
        processed_handler=processed_handler,
        stats_handler=stats_handler,
        exporter=HFExporter(
            repo_id=config.get("output_dataset_repo"),
            file_name=config.get("output_dataset_file_name")
        ),
        process_id=config.get("process_id")
    )
    return repository


def run_launchpad():
    """Run the 'launchpad' command logic."""
    config = initialize_config()
    tokenizer = initialize_tokenizer()
    repository = initialize_mongo_handlers_and_repository(config, db_name="promptLab")

    PromptLaunchpad(
        repository=repository,
        tokenizer=tokenizer,
        orbiter_task_name=config.get("orbiter_task_name"),
        orbiter_queue_name=config.get("orbiter_queue_name"),
        orbiter_queue_target_size=config.get_as_int("orbiter_queue_target_size"),
        batch_size=config.get_as_int("batch_size"),
    ).run()


def run_orbiter(batch: List[dict]):
    """Run the 'orbiter' command logic."""
    config = initialize_config()
    tokenizer = initialize_tokenizer()
    repository = initialize_mongo_handlers_and_repository(config, db_name="promptLab")
    llm_client = VLLMClient(
        api_url=config.get("model_api_url"),
        model_name=config.get("model_name"),
        max_context_length=config.get_as_int("model_max_context_length")
    )

    PromptOrbiter(
        llm_client=llm_client,
        repository=repository,
        tokenizer=tokenizer,
        review_queue_name=config.get("reviewer_queue_name"),
        reviewer_task_name=config.get("reviewer_task_name"),
        reviewed_prompts_queue_name=config.get("reviewed_prompts_queue_name"),
        landing_task_name=config.get("landing_task_name"),
        reviewer=config.get_as_bool("reviewer")
    ).run(batch)


def run_landing(batch: List[dict]):
    """Run the 'landing' command logic."""
    config = initialize_config()
    repository = initialize_mongo_handlers_and_repository(config, db_name="promptLab")

    PromptLanding(
        repository=repository,
        orbiter_queue_name=config.get("orbiter_queue_name"),
        orbiter_task_name=config.get("orbiter_task_name"),
        max_retry=config.get_as_int("max_retry"),
    ).run(batch)


def run_export():
    config = initialize_config()
    repository = initialize_mongo_handlers_and_repository(config, db_name="promptLab")
    repository.export()
