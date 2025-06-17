from session.session_registry import SessionRegistry
from schemas.blueprint.blueprint import BlueprintSpec
from graph.graph_plan import GraphPlan
from engine.builder.base_graph_builder import BaseGraphBuilder
from engine.executor.interfaces import GraphExecutor
from core.run_context import RunContext
from graph.state.graph_state import GraphState
from .status import SessionStatus
from .models import SessionMeta


class WorkflowSession:
    """
    Holds all runtime state for a single user-run of a blueprint:
      - session_registry: dynamic component instances (LLMs, agents, etc.)
      - blueprint: the validated BlueprintSpec
      - graph_plan: the abstract plan (list of Steps)
      - executable_graph: compiled graph ready to invoke()
      - logger: records every event
      - builder: the graph builder used (for live recompilation)
      - metadata: arbitrary dict (run_id, timestamps, user_id, etc.)
    """

    def __init__(
            self,
            session_registry: SessionRegistry,
            blueprint: BlueprintSpec,
            blueprint_id: str,
            graph_plan: GraphPlan,
            executable_graph: GraphExecutor,
            builder: BaseGraphBuilder,
            run_context: RunContext,
            # logger: LoggerInterface,
            graph_state: GraphState,
            metadata: SessionMeta | None = None
    ) -> None:
        self.session_registry = session_registry
        self.blueprint = blueprint
        self.blueprint_id = blueprint_id
        self.graph_plan = graph_plan
        self.executable_graph = executable_graph
        # self.logger = logger
        self.builder = builder
        self.run_context = run_context
        self.metadata = metadata
        self.graph_state = graph_state
        self.status: SessionStatus = SessionStatus.PENDING

    def recompile(self) -> None:
        """
        Rebuilds the executable_graph from the current graph_plan,
        using the stored builder.
        """
        self.executable_graph = self.builder.compile_from_plan(self.graph_plan)

    def get_user_id(self) -> str:
        """
        Returns the user ID associated with this session.
        """
        return self.run_context.user_id

    def get_run_id(self) -> str:
        """
        Returns the user ID associated with this session.
        """
        return self.run_context.run_id

    def get_state(self) -> GraphState:
        """
        Returns the current state of the graph.
        """
        return self.graph_state

    def get_status(self) -> SessionStatus:
        """
        Returns the current status of the session.
        """
        return self.status.name

    def update_status(self, new: SessionStatus) -> None:
        self.status = new
