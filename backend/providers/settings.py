import requests
from config.app_config import AppConfig
from shared.logger import logger
import umami


app_config = AppConfig.get_instance()


def get_umami_settings(website_name: str = "unifai"):
    try:
        umami_url = app_config.get("umami_url", "")
        umami_website_name = app_config.get("umami_website_name", "unifai")
        umami_username = app_config.get("umami_username", "")
        umami_password = app_config.get("umami_password", "")
        umami.set_url_base(umami_url)
        umami.login(umami_username, umami_password)
        websites = umami.websites()
        website_info = next(w for w in websites if w.name == umami_website_name)
        website_id = website_info.id
        return {"umami_url": umami_url, "website_id": website_id}
    except Exception as e:
        logger.error(f"Failed to get Umami website ID: {website_name}: {e}")
        raise