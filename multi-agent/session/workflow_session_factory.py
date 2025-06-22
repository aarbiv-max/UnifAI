from typing import Optional, Callable, Type
from pathlib import Path
from registry.element_registry import ElementRegistry
from blueprints.loader.base_blueprint_loader import BaseBlueprintLoader
from session.element_builder import SessionElementBuilder
from composers.plan_composer import PlanComposer
from engine.builder.graph_builder_factory import GraphBuilderFactory
from session.workflow_session import WorkflowSession
from graph.state.graph_state import GraphState
from core.run_context import RunContext
from core.context import set_current_context
from logs.logger_interface import LoggerInterface
from schemas.blueprint.blueprint import BlueprintSpec
from .models import SessionMeta


class WorkflowSessionFactory:
    """
    Orchestrates the creation of a WorkflowSession end-to-end:
      0) Build RunContext & set it
      1) Load & validate blueprint
      2) Instantiate atomic elements
      3) Build GraphPlan
      4) Compile to ExecutableGraph
      5) Create logger, saver, modifier
      6) Wire everything into WorkflowSession
      7) Persist initial snapshot
    """

    def __init__(
            self,
            element_registry: ElementRegistry,
            engine_name: str,
            # logger_factory: Callable[[RunContext], LoggerInterface],
    ):
        self._elements = element_registry
        self._session_builder = SessionElementBuilder(element_registry)
        self._engine_name = engine_name
        # self._logger_factory = logger_factory

    def create(
            self,
            *,
            user_id: str,
            blueprint_spec: BlueprintSpec,
            blueprint_id: str,
            metadata: SessionMeta = None,
            graph_state: GraphState = GraphState(),
    ) -> WorkflowSession:
        # 0) Build and propagate RunContext ———
        ctx = RunContext(
            user_id=user_id,
            engine_name=self._engine_name,
            metadata=metadata or {}
        )
        set_current_context(ctx)

        # 1) Instantiate session‐wide components ———
        session_registry = self._session_builder.build(blueprint_spec)

        # 2) Compose abstract plan ———
        composer = PlanComposer(session_registry)
        graph_plan = composer.compose(blueprint_spec.plan)

        # Optional: visualize
        graph_plan.pretty_print()

        # 3) Compile to executable graph ———
        _engine_builder = GraphBuilderFactory(GraphState).create(self._engine_name)
        executable_graph = _engine_builder.compile_from_plan(graph_plan)

        # 4) Create logger, saver, modifier ———
        # logger = self._logger_factory(ctx)
        # graph_saver = self._graph_saver
        # graph_modifier = self._graph_modifier_cls  # class, we'll instantiate below

        # 5) Wire into WorkflowSession ———
        session = WorkflowSession(
            session_registry=session_registry,
            blueprint=blueprint_spec,
            blueprint_id=blueprint_id,
            graph_plan=graph_plan,
            executable_graph=executable_graph,
            builder=_engine_builder,
            run_context=ctx,
            metadata=metadata or {},
            graph_state=graph_state,
        )

        return session
