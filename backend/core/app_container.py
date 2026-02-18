from pymongo import MongoClient

from admin_config.repository.mongo_repository import MongoAdminConfigRepository
from admin_config.service import AdminConfigService
from admin_config.template import ADMIN_CONFIG_TEMPLATE
from config.app_config import AppConfig
from global_utils.utils.singleton import SingletonMeta
from global_utils.utils.util import get_mongo_url


class AppContainer(metaclass=SingletonMeta):
    """
    Central composition root for the platform backend.

    All wiring lives here:
      - owns the shared MongoClient (single connection pool)
      - reads collection names from AppConfig
    """

    def __init__(self, cfg: AppConfig):
        if getattr(self, "_initialized", False):
            return

        # Shared MongoDB client (single connection pool)
        mongo_client = MongoClient(get_mongo_url())
        db = mongo_client[cfg.mongo_db]

        self.admin_config_repo = MongoAdminConfigRepository(
            collection=db[cfg.admin_config_coll],
        )

        self.admin_config_service = AdminConfigService(
            repository=self.admin_config_repo,
            template=ADMIN_CONFIG_TEMPLATE,
        )

        self._initialized = True
