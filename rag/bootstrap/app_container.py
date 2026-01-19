"""
RAG Application Container - Composition root with singleton instances via lru_cache.

Each function creates a singleton instance on first call, then returns the cached
instance on subsequent calls. Dependencies are wired here, not scattered across
the codebase.

Usage:
    from bootstrap.app_container import pipeline_service, monitoring_service
    
    # Services are singleton - same instance returned on every call
    svc = pipeline_service()
    svc.register(pipeline_id, source_type)
"""

from functools import lru_cache
from pymongo import MongoClient

from global_utils.utils.util import get_mongo_url


# ══════════════════════════════════════════════════════════════════════════════
# INFRASTRUCTURE - Shared resources
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def mongo_client() -> MongoClient:
    """
    Provide a shared MongoDB client for the application.
    
    Returns:
        MongoClient: A MongoClient connected using the configured MongoDB URL.
    """
    return MongoClient(get_mongo_url())


@lru_cache(maxsize=1)
def pipeline_monitoring_db():
    """
    Provide the MongoDB database handle for pipeline monitoring.
    
    Returns:
        Database: The `pipeline_monitoring` database handle.
    """
    return mongo_client()["pipeline_monitoring"]


@lru_cache(maxsize=1)
def data_sources_db():
    """
    Provide the MongoDB database handle for the "data_sources" database.
    
    Returns:
        Database: The `data_sources` database handle from the shared Mongo client.
    """
    return mongo_client()["data_sources"]


@lru_cache(maxsize=1)
def users_db():
    """
    Provides the MongoDB database handle for application user data such as terms approvals.
    
    Returns:
        Database: The "users" database handle from the shared MongoDB client.
    """
    return mongo_client()["users"]


@lru_cache(maxsize=1)
def file_storage():
    """
    Provides a LocalFileStorage instance configured for the application's upload folder.
    
    Returns:
        LocalFileStorage: An instance configured to use the upload folder path from AppConfig.
    """
    from infrastructure.storage.local_file_storage import LocalFileStorage
    from config.app_config import AppConfig
    return LocalFileStorage(AppConfig.get_instance().upload_folder)


@lru_cache(maxsize=1)
def umami_client():
    """
    Create a configured UmamiClient for website analytics.
    
    Reads 'umami_url', 'umami_username', and 'umami_password' from AppConfig and returns an UmamiClient initialized with those values.
    
    Returns:
        UmamiClient: An UmamiClient configured with URL, username, and password from AppConfig.
    """
    from infrastructure.umami.umami_client import UmamiClient
    from config.app_config import AppConfig
    config = AppConfig.get_instance()
    return UmamiClient(
        url=config.get("umami_url", ""),
        username=config.get("umami_username", ""),
        password=config.get("umami_password", ""),
    )


# ══════════════════════════════════════════════════════════════════════════════
# REPOSITORIES (Infrastructure adapters implementing domain ports)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def pipeline_repository():
    """
    Pipeline repository bound to the "pipelines" collection in the pipeline monitoring database.
    
    @returns MongoPipelineRepository: Repository instance for the `pipelines` collection.
    """
    from infrastructure.mongo.pipeline_repository import MongoPipelineRepository
    return MongoPipelineRepository(pipeline_monitoring_db()["pipelines"])


@lru_cache(maxsize=1)
def data_source_repository():
    """
    Provide a Mongo-backed data source repository for the "sources" collection.
    
    Returns:
        MongoDataSourceRepository: Instance bound to the "sources" collection in the data_sources database.
    """
    from infrastructure.mongo.data_source_repository import MongoDataSourceRepository
    return MongoDataSourceRepository(data_sources_db()["sources"])


@lru_cache(maxsize=1)
def monitoring_repository():
    """
    Provide the monitoring repository backed by the pipeline_monitoring MongoDB database.
    
    Returns:
        MongoMonitoringRepository: Repository instance bound to the pipeline_monitoring database.
    """
    from infrastructure.mongo.monitoring_repository import MongoMonitoringRepository
    return MongoMonitoringRepository(pipeline_monitoring_db())


@lru_cache(maxsize=None)
def vector_repository(collection_name: str):
    """
    Create and initialize a vector repository for the given collection.
    
    Parameters:
        collection_name (str): Name of the vector collection to create or open in the vector store.
    
    Returns:
        VectorRepository: An initialized vector repository instance bound to the specified collection and ready for use.
    """
    from bootstrap.factories import VectorRepositoryFactory    
    repo = VectorRepositoryFactory.create({
        "type": "qdrant",
        "collection_name": collection_name,
        "embedding_dim": embedding_generator().embedding_dim,
    })
    repo.initialize()
    return repo


@lru_cache(maxsize=1)
def slack_channel_repository():
    """
    Provides a Mongo-backed repository for Slack channels.
    
    Returns:
        MongoSlackChannelRepository: Repository instance connected to the "slack_channels" collection in the data_sources database.
    """
    from infrastructure.mongo.slack_channel_repository import MongoSlackChannelRepository
    return MongoSlackChannelRepository(data_sources_db()["slack_channels"])


@lru_cache(maxsize=1)
def terms_approval_repository():
    """
    Provides a Mongo-backed repository for user terms approvals.
    
    Returns:
        MongoTermsApprovalRepository: Repository instance bound to the "terms_user_approval" collection in the users database.
    """
    from infrastructure.mongo.terms_approval_repository import MongoTermsApprovalRepository
    return MongoTermsApprovalRepository(users_db()["terms_user_approval"])


# ══════════════════════════════════════════════════════════════════════════════
# PROCESSORS (Domain layer - stateless data transformers)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def slack_processor():
    """
    Create a Slack message processor.
    
    Returns:
        SlackProcessor: An instantiated SlackProcessor.
    """
    from domain.processor.slack_processor import SlackProcessor
    return SlackProcessor()


@lru_cache(maxsize=1)
def document_processor():
    """
    Provide a DocumentProcessor configured to handle PDF and Markdown documents.
    
    Returns:
        DocumentProcessor: Processor instance capable of extracting and preparing content from PDF and Markdown sources.
    """
    from domain.processor.document_processor import DocumentProcessor
    return DocumentProcessor()


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG MANAGERS (Infrastructure layer - configuration adapters)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def slack_config_manager():
    """
    Create a SlackConfigManager preconfigured with default project tokens from the application config.
    
    If AppConfig contains a `default_slack_bot_token`, the manager will be configured with that bot token and the optional `default_slack_user_token` for the project "example-project", and that project will be set as the default. The returned manager is ready for use whether or not default tokens were present.
    """
    from infrastructure.config.slack_config_manager import SlackConfigManager
    from config.app_config import AppConfig
    
    config = AppConfig.get_instance()
    manager = SlackConfigManager()
    
    # Configure default project tokens from app config
    bot_token = config.get("default_slack_bot_token", "")
    user_token = config.get("default_slack_user_token", "")
    
    if bot_token:
        manager.set_project_tokens(
            project_id="example-project",
            bot_token=bot_token,
            user_token=user_token,
        )
        manager.set_default_project("example-project")
    
    return manager


# ══════════════════════════════════════════════════════════════════════════════
# CELERY ADAPTERS (Infrastructure layer - async task dispatch)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def celery_pipeline_dispatcher():
    """
    Create a Celery adapter for dispatching pipeline tasks.
    
    Returns:
        CeleryPipelineDispatcher: A configured dispatcher for enqueuing pipeline-related Celery tasks.
    """
    from infrastructure.celery.pipeline_dispatcher import CeleryPipelineDispatcher
    return CeleryPipelineDispatcher()


@lru_cache(maxsize=1)
def celery_slack_event_dispatcher():
    """
    Create a Celery-backed dispatcher for Slack events.
    
    Returns:
        CelerySlackEventDispatcher: Dispatcher instance that enqueues Slack event handling tasks to Celery.
    """
    from infrastructure.celery.slack_event_dispatcher import CelerySlackEventDispatcher
    return CelerySlackEventDispatcher()


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTORS (Infrastructure layer - data source adapters)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=None)
def slack_connector(project_id: str):
    """
    Resolve a SlackConnector configured for the given project.
    
    Parameters:
        project_id (str): Project identifier used to scope the connector.
    
    Returns:
        SlackConnector: A SlackConnector instance wired with the shared Slack config manager and slack channel repository for the specified project.
    """
    from infrastructure.connector.slack_connector import SlackConnector
    return SlackConnector(
        config_manager=slack_config_manager(),
        channel_repo=slack_channel_repository(),
        project_id=project_id,
    )


@lru_cache(maxsize=1)
def document_connector():
    """
    Provide a DocumentConnector for ingesting PDF and other document formats.
    
    Returns:
        DocumentConnector: Connector used to fetch and normalize document content.
    """
    from infrastructure.connector.document_connector import DocumentConnector
    return DocumentConnector()


# ══════════════════════════════════════════════════════════════════════════════
# CHUNKERS (Infrastructure layer - content splitting strategies)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def slack_chunker():
    """
    Creates a Slack conversation chunker configured for typical message batching.
    
    The chunker splits Slack conversations into chunks sized for downstream embedding/processing with a modest overlap and a time-based window to group recent messages.
    
    Returns:
        SlackChunkerStrategy: Configured with max_tokens_per_chunk=500, overlap_tokens=50, and time_window_seconds=300.
    """
    from infrastructure.chunking.slack_chunker import SlackChunkerStrategy
    return SlackChunkerStrategy(
        max_tokens_per_chunk=500,
        overlap_tokens=50,
        time_window_seconds=300,
    )


@lru_cache(maxsize=1)
def pdf_chunker():
    """
    Create a PDF/document chunker configured for default chunking behavior.
    
    Returns:
        PDFChunkerStrategy: Chunker configured with max_tokens_per_chunk=500 and overlap_tokens=50.
    """
    from infrastructure.chunking.pdf_chunker import PDFChunkerStrategy
    return PDFChunkerStrategy(
        max_tokens_per_chunk=500,
        overlap_tokens=50,
    )


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION SERVICES
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def pipeline_service():
    """
    Create and return the application's PipelineService configured with the application pipeline repository.
    
    Returns:
        PipelineService: A PipelineService instance wired with the module's pipeline_repository.
    """
    from application.pipeline_service import PipelineService
    return PipelineService(pipeline_repo=pipeline_repository())


@lru_cache(maxsize=1)
def monitoring_service():
    """Monitoring application service."""
    from application.monitoring_service import MonitoringService
    return MonitoringService(
        monitoring_repo=monitoring_repository(),
        pipeline_repo=pipeline_repository(),
    )


@lru_cache(maxsize=1)
def data_source_service():
    """
    Create the DataSourceService configured with the data source repository, pipeline repository, and a vector repository factory.
    
    Returns:
        DataSourceService: An application service for managing data sources, wired with required repositories and vector repository factory.
    """
    from application.data_source_service import DataSourceService
    return DataSourceService(
        source_repo=data_source_repository(),
        pipeline_repo=pipeline_repository(),
        vector_repo_factory=vector_repository,
    )


@lru_cache(maxsize=1)
def doc_validators():
    """
    Create and return a DocValidators factory configured with application settings and repository-backed checkers.
    
    The returned factory bundles four validators:
    - DuplicateValidator: detects duplicate documents using the data source repository.
    - ExtensionValidator: enforces allowed file extensions from DocConfigManager.
    - SizeValidator: enforces maximum file size from DocConfigManager (defaults to 50 MB).
    - NameDuplicateValidator: detects duplicate file names using the data source repository.
    
    Returns:
        DocValidators: A factory containing the configured document validators.
    """
    from application.validation.validators.document.factory import DocValidators
    from application.validation.validators.document.duplicate_validator import DuplicateValidator
    from application.validation.validators.document.extension_validator import ExtensionValidator
    from application.validation.validators.document.size_validator import SizeValidator
    from application.validation.validators.document.name_duplicate_validator import NameDuplicateValidator
    from infrastructure.config.doc_config_manager import DocConfigManager
    from infrastructure.validation.document_duplicate_checker import DocumentDuplicateCheckerAdapter
    from infrastructure.validation.name_duplicate_checker import NameDuplicateCheckerAdapter
    
    config = DocConfigManager()
    
    # Create individual validators with their dependencies
    duplicate_validator = DuplicateValidator(
        duplicate_checker=DocumentDuplicateCheckerAdapter(data_source_repository())
    )
    extension_validator = ExtensionValidator(
        supported_extensions=config.get_supported_file_types()
    )
    size_validator = SizeValidator(
        max_file_size_bytes=config.get_config_value("max_file_size_mb", 50) * 1024 * 1024
    )
    name_duplicate_validator = NameDuplicateValidator(
        name_duplicate_checker=NameDuplicateCheckerAdapter(data_source_repository())
    )
    
    return DocValidators(
        duplicate_validator=duplicate_validator,
        extension_validator=extension_validator,
        size_validator=size_validator,
        name_duplicate_validator=name_duplicate_validator,
    )


@lru_cache(maxsize=1)
def slack_validators():
    """
    Create a Slack validators factory configured for channel bot installation checks.
    
    Returns:
        SlackValidators: A SlackValidators instance containing a ChannelBotInstallationValidator that uses a BotInstallationCheckerAdapter (currently initialized without a Slack connector) and a MembershipUpdaterAdapter backed by the slack channel repository.
    """
    from application.validation.validators.slack.factory import SlackValidators
    from application.validation.validators.slack.channel_bot_installation_validator import ChannelBotInstallationValidator
    from infrastructure.validation.bot_installation_checker import BotInstallationCheckerAdapter, MembershipUpdaterAdapter
    
    # TODO: Inject proper Slack connector based on project (None for now - graceful fallback)
    bot_checker = BotInstallationCheckerAdapter(slack_connector=None)
    membership_updater = MembershipUpdaterAdapter(storage=slack_channel_repository())
    
    return SlackValidators(
        channel_bot_validator=ChannelBotInstallationValidator(
            bot_checker=bot_checker,
            membership_updater=membership_updater,
        )
    )


def file_validation_service(username: str):
    """
    Create a FileValidationService configured for the given username.
    
    This function returns a per-user validator instance (not cached) since each username requires distinct validation state.
    
    Parameters:
    	username (str): Username that scopes validation rules and duplicate-name checks.
    
    Returns:
    	FileValidationService: A FileValidationService instance configured to validate uploads for the specified username.
    """
    from application.file_validation_service import FileValidationService
    from infrastructure.config.doc_config_manager import DocConfigManager
    from infrastructure.validation.name_duplicate_checker import NameDuplicateCheckerAdapter
    
    return FileValidationService(
        username=username,
        config_manager=DocConfigManager(),
        name_checker=NameDuplicateCheckerAdapter(data_source_repository()),
    )


@lru_cache(maxsize=1)
def registration_factory():
    """
    Create and return a RegistrationFactory configured for the application.
    
    Returns:
        RegistrationFactory: A factory wired with the application's data source repository, upload folder, document validators, and Slack validators.
    """
    from application.registration.factory import RegistrationFactory
    from config.app_config import AppConfig
    return RegistrationFactory(
        data_source_repository=data_source_repository(),
        upload_folder=AppConfig.get_instance().upload_folder,
        doc_validators=doc_validators(),
        slack_validators=slack_validators(),
    )


@lru_cache(maxsize=1)
def registration_service():
    """
    Create and return the application's RegistrationService used for source registration flows.
    
    Returns:
        RegistrationService: A configured RegistrationService instance.
    """
    from application.registration.registration_service import RegistrationService
    return RegistrationService(factory=registration_factory())


@lru_cache(maxsize=1)
def pipeline_dispatch_service():
    """
    Provide a PipelineDispatchService configured with the registration service and Celery pipeline dispatcher.
    
    Returns:
        PipelineDispatchService: Service that coordinates registration and dispatching of pipeline tasks.
    """
    from application.pipeline_dispatch_service import PipelineDispatchService
    return PipelineDispatchService(
        registration_svc=registration_service(),
        task_dispatcher=celery_pipeline_dispatcher(),
    )


@lru_cache(maxsize=1)
def slack_event_dispatch_service():
    """
    Provide a SlackEventDispatchService configured to dispatch Slack Events via the application's async dispatcher.
    
    Returns:
        SlackEventDispatchService: instance wired with the Celery Slack event dispatcher.
    """
    from application.slack_event_dispatch_service import SlackEventDispatchService
    return SlackEventDispatchService(
        dispatcher=celery_slack_event_dispatcher(),
    )


@lru_cache(maxsize=1)
def terms_approval_service():
    """
    Provide a TermsApprovalService configured with the terms approval repository.
    
    @returns TermsApprovalService: Service instance for managing user terms approvals.
    """
    from application.terms_approval_service import TermsApprovalService
    return TermsApprovalService(approval_repo=terms_approval_repository())


# ══════════════════════════════════════════════════════════════════════════════
# SLACK EVENTS (Application layer - event handling)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def channel_created_handler():
    """
    Create a ChannelCreatedEventHandler configured for the example project.
    
    Returns:
        ChannelCreatedEventHandler: Configured with the Slack channel repository and project_id "example-project".
    """
    from application.slack_events.handlers.channel_created import ChannelCreatedEventHandler
    return ChannelCreatedEventHandler(
        channel_repo=slack_channel_repository(),
        project_id="example-project",  # TODO: Get from config
    )


@lru_cache(maxsize=1)
def slack_event_service():
    """
    Create a SlackEventService with built-in Slack event handlers registered.
    
    Registers the factory for the "channel_created" event so the service can resolve handlers for that event type.
    
    Returns:
        SlackEventService: A configured SlackEventService instance with the "channel_created" handler registered.
    """
    from application.slack_events.service import SlackEventService
    service = SlackEventService()
    service.register_factory("channel_created", channel_created_handler)
    return service


# ══════════════════════════════════════════════════════════════════════════════
# EMBEDDING & VECTOR COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def embedding_generator():
    """
    Provide a shared embedding generator configured for the "sentence_transformer" implementation.
    
    Returns:
        EmbeddingGenerator: An embedding generator instance configured to produce sentence-transformer embeddings.
    """
    from bootstrap.factories import EmbeddingGeneratorFactory
    return EmbeddingGeneratorFactory.create({"type": "sentence_transformer"})


# ══════════════════════════════════════════════════════════════════════════════
# RETRIEVAL SERVICE (Application layer - vector search orchestration)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def source_filter_resolver():
    """
    Resolve and map retrieval filters (for example, document IDs or tags) to source IDs.
    
    Returns:
        SourceFilterResolver: A resolver instance configured with the "sources" collection from the data_sources database.
    """
    from infrastructure.retrieval.source_filter_resolver import SourceFilterResolver
    return SourceFilterResolver(data_sources_db()["sources"])


@lru_cache(maxsize=None)
def retrieval_service(source_type: str):
    """
    Constructs a RetrievalService for the given source type.
    
    Parameters:
        source_type (str): Source type name (e.g., "DOCUMENT", "SLACK"); the value is normalized to uppercase and used to select the corresponding vector repository named "<source_type>_data".
    
    Returns:
        RetrievalService: Instance configured with the shared embedder, the vector repository for the source, the source filter resolver, and the normalized source type.
    """
    from application.retrieval_service import RetrievalService
    return RetrievalService(
        embedder=embedding_generator(),
        vector_repo=vector_repository(f"{source_type.lower()}_data"),
        filter_resolver=source_filter_resolver(),
        source_type=source_type.upper(),
    )


# ══════════════════════════════════════════════════════════════════════════════
# STATS SERVICES (Application layer - query/aggregation use cases)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def vector_stats_service():
    """
    Provide a configured VectorStatsService for collecting statistics about vector storage.
    
    Returns:
        VectorStatsService: Service instance configured with a vector repository factory.
    """
    from application.stats.vector_stats_service import VectorStatsService
    return VectorStatsService(vector_repo_factory=vector_repository)


@lru_cache(maxsize=1)
def slack_stats_service():
    """
    Provides a Slack statistics aggregation service.
    
    Returns:
        SlackStatsService: Instance configured with the application's data_source_service.
    """
    from application.stats.slack_stats_service import SlackStatsService
    return SlackStatsService(data_source_service=data_source_service())


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE HANDLERS (Application layer - source-specific orchestration)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def slack_pipeline_handler():
    """
    Provide a pipeline handler for Slack that routes and processes Slack content.
    
    The returned handler is wired with the default Slack connector, a Slack processor,
    a Slack chunker strategy, and the shared embedding generator.
    
    Returns:
        SlackPipelineHandler: Handler configured with connector, processor, chunker, and embedder.
    """
    from application.pipeline.slack_handler import SlackPipelineHandler
    return SlackPipelineHandler(
        connector=slack_connector("default"),
        processor=slack_processor(),
        chunker=slack_chunker(),
        embedder=embedding_generator(),
    )


@lru_cache(maxsize=1)
def document_pipeline_handler():
    """
    Create a DocumentPipelineHandler wired with the document connector, document processor, PDF chunker, and embedding generator.
    
    @returns DocumentPipelineHandler configured for document ingestion and processing using the document connector, document processor, PDF chunker, and embedding generator.
    """
    from application.pipeline.document_handler import DocumentPipelineHandler
    return DocumentPipelineHandler(
        connector=document_connector(),
        processor=document_processor(),
        chunker=pdf_chunker(),
        embedder=embedding_generator(),
    )


def get_pipeline_handler(source_type: str):
    """
    Resolve the pipeline handler for a given source type.
    
    Parameters:
        source_type (str): Source type identifier, e.g. "SLACK" or "DOCUMENT".
    
    Returns:
        SourcePipelinePort: The pipeline handler instance corresponding to the provided source type.
    
    Raises:
        ValueError: If the provided source type is not supported.
    """
    handlers = {
        "SLACK": slack_pipeline_handler,
        "DOCUMENT": document_pipeline_handler,
    }
    
    factory = handlers.get(source_type.upper())
    if not factory:
        raise ValueError(f"Unsupported source type: {source_type}")
    
    return factory()


@lru_cache(maxsize=1)
def pipeline_executor():
    """
    Create the application PipelineExecutor wired with the shared pipeline, monitoring, and data-source services and the vector repository factory.
    
    Returns:
        PipelineExecutor: Executor instance configured with pipeline_service, monitoring_service, data_source_service, and the vector_repository factory.
    """
    from application.pipeline.executor import PipelineExecutor
    return PipelineExecutor(
        pipeline_service=pipeline_service(),
        monitoring_service=monitoring_service(),
        data_source_service=data_source_service(),
        vector_repository=vector_repository,
    )


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY - Cache management for testing
# ══════════════════════════════════════════════════════════════════════════════

def clear_all_caches():
    """
    Clear all cached singleton factories so subsequent calls create fresh instances.
    
    This resets the lru_cache for every component in the app container and is intended for use in tests to ensure a clean, deterministic environment between test cases.
    """
    # Infrastructure
    mongo_client.cache_clear()
    pipeline_monitoring_db.cache_clear()
    data_sources_db.cache_clear()
    users_db.cache_clear()
    file_storage.cache_clear()
    umami_client.cache_clear()
    # Repositories
    pipeline_repository.cache_clear()
    data_source_repository.cache_clear()
    monitoring_repository.cache_clear()
    vector_repository.cache_clear()
    slack_channel_repository.cache_clear()
    terms_approval_repository.cache_clear()
    # Processors
    slack_processor.cache_clear()
    document_processor.cache_clear()
    # Config Managers
    slack_config_manager.cache_clear()
    # Connectors
    slack_connector.cache_clear()
    document_connector.cache_clear()
    # Chunkers
    slack_chunker.cache_clear()
    pdf_chunker.cache_clear()
    # Services
    pipeline_service.cache_clear()
    monitoring_service.cache_clear()
    data_source_service.cache_clear()
    terms_approval_service.cache_clear()
    # Registration & Dispatch
    doc_validators.cache_clear()
    slack_validators.cache_clear()
    registration_factory.cache_clear()
    registration_service.cache_clear()
    pipeline_dispatch_service.cache_clear()
    # Celery Adapters
    celery_pipeline_dispatcher.cache_clear()
    celery_slack_event_dispatcher.cache_clear()
    slack_event_dispatch_service.cache_clear()
    # Embedding
    embedding_generator.cache_clear()
    # Retrieval
    source_filter_resolver.cache_clear()
    retrieval_service.cache_clear()
    # Stats
    vector_stats_service.cache_clear()
    slack_stats_service.cache_clear()
    # Slack Events
    channel_created_handler.cache_clear()
    slack_event_service.cache_clear()
    # Pipeline Handlers & Executor
    slack_pipeline_handler.cache_clear()
    document_pipeline_handler.cache_clear()
    pipeline_executor.cache_clear()
