from temporalio import activity
from temporal.models import ExecutionParams


@activity.defn
def run_session(params: ExecutionParams) -> dict:
    """
    Temporal activity that executes a session via the existing SessionService.
    This is the exact same call Flask makes — just invoked from a Temporal worker.

    AppContainer is a singleton (via SingletonMeta) — already bootstrapped
    by the worker process before activities are registered.
    """
    from core.app_container import AppContainer
    from config.app_config import AppConfig

    activity.logger.info(f"Running session {params.session_id}")

    container = AppContainer(AppConfig.get_instance())
    result = container.session_service.execute(
        session_id=params.session_id,
        inputs=params.inputs,
        stream=False,
        scope=params.scope,
        logged_in_user=params.logged_in_user,
    )

    activity.logger.info(f"Session {params.session_id} completed")
    return result
