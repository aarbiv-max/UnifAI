from registry.element_registry import ElementRegistry
from blueprints.repository.mongo_blueprint_repository import MongoBlueprintRepository
from blueprints.service import BlueprintService
from session.workflow_session_factory import WorkflowSessionFactory
from session.repository.mongo_session_repository import MongoSessionRepository
from session.user_session_manager import UserSessionManager
from session.session_executor import SessionExecutor
from session.service import SessionService
from config.app_config import AppConfig
from global_utils.utils.util import singleton


@singleton
class AppContainer:
    """
    Central composition root.  All wiring lives here, but no magic strings:
      • reads collection names   from AppConfig
      • reads engine_name        from AppConfig
      • reads mongo_uri & db     from AppConfig
    """

    def __init__(self, cfg: AppConfig):
        # idempotent guard
        if getattr(self, "_initialized", False):
            return

        # plugin discovery
        self.element_registry = ElementRegistry()
        self.element_registry.auto_discover()

        # blueprint catalog
        self.blueprint_repo = MongoBlueprintRepository(
            mongodb_port=cfg.mongodb_port,
            mongodb_ip=cfg.mongodb_ip,
            db_name=cfg.mongo_db,
            coll_name=cfg.blueprint_coll
        )
        self.blueprint_service = BlueprintService(self.blueprint_repo)

        # session orchestration
        self.session_factory = WorkflowSessionFactory(
            element_registry=self.element_registry,
            engine_name=cfg.engine_name
        )
        self.session_repo = MongoSessionRepository(
            mongodb_port=cfg.mongodb_port,
            mongodb_ip=cfg.mongodb_ip,
            db_name=cfg.mongo_db,
            collection_name=cfg.session_coll,
            session_factory=self.session_factory
        )
        self.session_manager = UserSessionManager(
            repository=self.session_repo,
            session_factory=self.session_factory
        )
        self.session_executor = SessionExecutor(
            session_manager=self.session_manager,
            repository=self.session_repo
        )

        self.session_service = SessionService(
            manager=self.session_manager,
            executor=self.session_executor
        )

        self._initialized = True
