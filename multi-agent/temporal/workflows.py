from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

from temporal.models import ExecutionParams


@workflow.defn
class AgentExecutionWorkflow:
    """
    Temporal workflow that runs an agent session as a single activity.
    The entire LangGraph execution happens inside one activity call.
    """

    @workflow.run
    async def run(self, params: ExecutionParams) -> dict:
        return await workflow.execute_activity(
            "run_session",
            params,
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
