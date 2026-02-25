import asyncio
from concurrent.futures import ThreadPoolExecutor
from temporalio.worker import Worker

from config.app_config import AppConfig
from core.app_container import AppContainer
from temporal.client import get_temporal_client
from temporal.workflows import AgentExecutionWorkflow
from temporal.activities import run_session


async def main():
    cfg = AppConfig.get_instance()

    # Bootstrap the same DI container Flask uses
    AppContainer(cfg)

    client = await get_temporal_client()

    worker = Worker(
        client,
        task_queue=cfg.temporal_task_queue,
        workflows=[AgentExecutionWorkflow],
        activities=[run_session],
        activity_executor=ThreadPoolExecutor(max_workers=5),
    )

    print(f"Temporal worker started, polling queue: {cfg.temporal_task_queue}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
