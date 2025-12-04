"""
Comprehensive integration tests for RTGraphPlan with the new topology system.

Tests that RTGraphPlan correctly creates StepContext with StepTopology containing
FinalizerPathInfo, and that this information is properly injected into nodes.
"""

import pytest
from collections import defaultdict
from unittest.mock import Mock, MagicMock, call
from graph.rt_graph_plan import RTGraphPlan
from graph.graph_plan import GraphPlan
from graph.models import Step, StepContext
from graph.topology.models import StepTopology, FinalizerPathInfo
from core.enums import ResourceCategory
from session.session_registry import SessionRegistry
from catalog.element_registry import ElementRegistry
from blueprints.models.blueprint import StepMeta


def create_mock_fixtures():
    """Create mock session registry and element registry for testing."""
    session_registry = Mock(spec=SessionRegistry)
    element_registry = Mock(spec=ElementRegistry)
    
    mock_nodes = {}
    store = defaultdict(dict)
    
    def create_mock_node(rid):
        mock_node = Mock()
        mock_node.set_context = Mock()
        mock_node.__dict__['set_context'] = mock_node.set_context
        return mock_node
    
    for node_id in ["orchestrator", "agent", "processor", "finalizer"]:
        rid = f"{node_id}_rid"
        mock_nodes[rid] = create_mock_node(rid)
    
    def get_instance_side_effect(category, rid):
        if rid not in mock_nodes:
            mock_nodes[rid] = create_mock_node(rid)
        return mock_nodes[rid]
    
    def create_runtime_element(rid):
        runtime_element = Mock()
        runtime_element.instance = mock_nodes.get(rid, Mock())
        
        resource_spec = Mock()
        resource_spec.name = f"Test {rid}"
        resource_spec.type = "test_type"
        resource_spec.config = Mock()
        resource_spec.config.__dict__ = {}
        
        runtime_element.resource_spec = resource_spec
        
        spec = Mock()
        spec.type_key = "test_type"
        spec.name = f"Test {rid}"
        spec.description = f"Test description for {rid}"
        spec.capability_names = []
        spec.card_builder_cls = None
        
        runtime_element.spec = spec
        return runtime_element
    
    for category in ResourceCategory:
        store[category] = {}
    
    session_registry._store = store
    session_registry.get_instance.side_effect = get_instance_side_effect
    
    mock_spec = Mock()
    mock_spec.category = ResourceCategory.NODE
    mock_spec.type_key = "test_type"
    mock_spec.name = "Test"
    mock_spec.description = "Test description"
    mock_spec.capability_names = []
    mock_spec.card_builder_cls = None
    element_registry.get_spec.return_value = mock_spec
    
    return session_registry, element_registry, mock_nodes, store, create_runtime_element


class TestRTGraphPlanTopologyIntegration:
    """Test integration of topology analysis into RTGraphPlan."""
    
    @pytest.fixture
    def mock_registries(self):
        """Create mock registries for testing."""
        return create_mock_fixtures()
    
    def test_rtgraphplan_creates_topology_for_simple_chain(self, mock_registries):
        """Test RTGraphPlan creates topology for simple chain to finalizer."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        # Create simple chain: orchestrator -> agent -> finalizer
        orchestrator = Step(
            uid="orchestrator",
            category=ResourceCategory.NODE,
            rid="orchestrator_rid",
            type_key="orchestrator",
            writes={"messages"}
        )
        
        agent = Step(
            uid="agent",
            category=ResourceCategory.NODE,
            rid="agent_rid",
            type_key="agent",
            reads={"messages"},
            writes={"nodes_output"},
            after=["orchestrator"]
        )
        
        finalizer = Step(
            uid="finalizer",
            category=ResourceCategory.NODE,
            rid="finalizer_rid",
            type_key="finalizer",
            reads={"nodes_output"},
            writes={"output"},  # Finalizer
            after=["agent"]
        )
        
        for step in [orchestrator, agent, finalizer]:
            store[ResourceCategory.NODE][step.rid] = create_rt_elem(step.rid)
        
        logical_plan = GraphPlan()
        logical_plan.add_step(orchestrator)
        logical_plan.add_step(agent)
        logical_plan.add_step(finalizer)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        # Verify orchestrator got topology information
        orchestrator_node = mock_nodes["orchestrator_rid"]
        orchestrator_node.set_context.assert_called_once()
        
        context = orchestrator_node.set_context.call_args[0][0]
        assert isinstance(context, StepContext)
        assert context.uid == "orchestrator"
        assert isinstance(context.topology, StepTopology)
        
        # Orchestrator should see agent as adjacent with path to finalizer
        assert context.topology.has_finalizer_path()
        assert context.topology.get_distance_to_finalizer("agent") == 2  # agent -> finalizer + 1
        assert context.topology.get_nearest_finalizer_node() == "agent"
    
    def test_rtgraphplan_creates_topology_for_multiple_paths(self, mock_registries):
        """Test RTGraphPlan creates topology for multiple paths to finalizers."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        # Create graph: orchestrator -> [agent1, agent2] -> finalizer
        # agent1 has shorter path, agent2 has longer path
        orchestrator = Step(
            uid="orchestrator",
            category=ResourceCategory.NODE,
            rid="orchestrator_rid",
            type_key="orchestrator",
            writes={"messages"}
        )
        
        agent1 = Step(
            uid="agent1",
            category=ResourceCategory.NODE,
            rid="agent1_rid",
            type_key="agent",
            reads={"messages"},
            writes={"output"},  # Direct finalizer
            after=["orchestrator"]
        )
        
        agent2 = Step(
            uid="agent2",
            category=ResourceCategory.NODE,
            rid="agent2_rid",
            type_key="agent",
            reads={"messages"},
            writes={"intermediate"},
            after=["orchestrator"]
        )
        
        processor = Step(
            uid="processor",
            category=ResourceCategory.NODE,
            rid="processor_rid",
            type_key="processor",
            reads={"intermediate"},
            writes={"output"},  # Also a finalizer
            after=["agent2"]
        )
        
        for step in [orchestrator, agent1, agent2, processor]:
            store[ResourceCategory.NODE][step.rid] = create_rt_elem(step.rid)
        
        logical_plan = GraphPlan()
        for step in [orchestrator, agent1, agent2, processor]:
            logical_plan.add_step(step)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        # Check orchestrator's topology
        context = mock_nodes["orchestrator_rid"].set_context.call_args[0][0]
        assert context.topology.has_finalizer_path()
        
        # agent1 should have distance 1 (direct finalizer)
        assert context.topology.get_distance_to_finalizer("agent1") == 1
        # agent2 should have distance 2 (agent2 -> processor + 1)
        assert context.topology.get_distance_to_finalizer("agent2") == 2
        
        # Shortest path should be through agent1
        assert context.topology.get_shortest_finalizer_distance() == 1
        assert context.topology.get_nearest_finalizer_node() == "agent1"
    
    def test_rtgraphplan_handles_no_finalizer_paths(self, mock_registries):
        """Test RTGraphPlan handles nodes with no paths to finalizers."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        # Create graph with no finalizers
        node1 = Step(
            uid="node1",
            category=ResourceCategory.NODE,
            rid="node1_rid",
            type_key="node1",
            writes={"data1"}
        )
        
        node2 = Step(
            uid="node2",
            category=ResourceCategory.NODE,
            rid="node2_rid",
            type_key="node2",
            reads={"data1"},
            writes={"data2"},  # Not a finalizer
            after=["node1"]
        )
        
        for step in [node1, node2]:
            store[ResourceCategory.NODE][step.rid] = create_rt_elem(step.rid)
        
        logical_plan = GraphPlan()
        logical_plan.add_step(node1)
        logical_plan.add_step(node2)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        # Check node1's topology
        context = mock_nodes["node1_rid"].set_context.call_args[0][0]
        assert isinstance(context.topology, StepTopology)
        assert not context.topology.has_finalizer_path()
        assert context.topology.finalizer_paths is None
    
    def test_rtgraphplan_handles_cycles(self, mock_registries):
        """Test RTGraphPlan handles cyclic graphs correctly."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        # Create cycle: A -> B -> A, plus A -> C -> finalizer
        node_a = Step(
            uid="A",
            category=ResourceCategory.NODE,
            rid="A_rid",
            type_key="A",
            writes={"data_a"}
        )
        
        node_b = Step(
            uid="B",
            category=ResourceCategory.NODE,
            rid="B_rid",
            type_key="B",
            reads={"data_a"},
            writes={"data_a"},  # Cycles back
            after=["A"]
        )
        
        node_c = Step(
            uid="C",
            category=ResourceCategory.NODE,
            rid="C_rid",
            type_key="C",
            reads={"data_a"},
            writes={"data_c"},
            after=["A"]
        )
        
        finalizer = Step(
            uid="finalizer",
            category=ResourceCategory.NODE,
            rid="finalizer_rid",
            type_key="finalizer",
            reads={"data_c"},
            writes={"output"},
            after=["C"]
        )
        
        for step in [node_a, node_b, node_c, finalizer]:
            store[ResourceCategory.NODE][step.rid] = create_rt_elem(step.rid)
        
        logical_plan = GraphPlan()
        for step in [node_a, node_b, node_c, finalizer]:
            logical_plan.add_step(step)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        # Check A's topology - should find path through C but handle B cycle
        context = mock_nodes["A_rid"].set_context.call_args[0][0]
        assert context.topology.has_finalizer_path()
        
        # Should have path through C
        assert context.topology.get_distance_to_finalizer("C") == 2  # C -> finalizer + 1
        
        # B might or might not be included depending on cycle detection
        # The key is that we have at least one valid path
        assert context.topology.get_shortest_finalizer_distance() >= 2
    
    def test_rtgraphplan_handles_branching_conditions(self, mock_registries):
        """Test RTGraphPlan handles conditional branching in topology."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        # Create conditional branch: orchestrator -> {success: agent1, failure: agent2}
        orchestrator = Step(
            uid="orchestrator",
            category=ResourceCategory.NODE,
            rid="orchestrator_rid",
            type_key="orchestrator",
            writes={"messages"},
            branches={"success": "agent1", "failure": "agent2"}  # Conditional branches
        )
        
        agent1 = Step(
            uid="agent1",
            category=ResourceCategory.NODE,
            rid="agent1_rid",
            type_key="agent",
            reads={"messages"},
            writes={"output"}  # Finalizer
        )
        
        agent2 = Step(
            uid="agent2",
            category=ResourceCategory.NODE,
            rid="agent2_rid",
            type_key="agent",
            reads={"messages"},
            writes={"output"}  # Also finalizer
        )
        
        for step in [orchestrator, agent1, agent2]:
            store[ResourceCategory.NODE][step.rid] = create_rt_elem(step.rid)
        
        logical_plan = GraphPlan()
        for step in [orchestrator, agent1, agent2]:
            logical_plan.add_step(step)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        context = mock_nodes["orchestrator_rid"].set_context.call_args[0][0]
        assert context.topology.has_finalizer_path()
        
        assert context.topology.get_distance_to_finalizer("agent1") == 1
        assert context.topology.get_distance_to_finalizer("agent2") == 1
        assert context.topology.get_shortest_finalizer_distance() == 1
        
        reachable = set(context.topology.get_finalizer_reachable_nodes())
        assert reachable == {"agent1", "agent2"}
        
        assert context.topology.finalizer_paths is not None
        assert isinstance(context.topology.finalizer_paths, FinalizerPathInfo)
        assert context.topology.finalizer_paths.distances == {"agent1": 1, "agent2": 1}


class TestRTGraphPlanStepContextInjection:
    """Test that StepContext with topology is properly injected into nodes."""
    
    @pytest.fixture
    def mock_registries(self):
        """Create mock registries for testing."""
        return create_mock_fixtures()
    
    def test_all_nodes_receive_step_context(self, mock_registries):
        """Test that all nodes receive StepContext with topology."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        node1 = Step(uid="node1", category=ResourceCategory.NODE, rid="node1_rid", type_key="node1", writes={"data"})
        node2 = Step(uid="node2", category=ResourceCategory.NODE, rid="node2_rid", type_key="node2", reads={"data"}, writes={"processed"}, after=["node1"])
        finalizer = Step(uid="finalizer", category=ResourceCategory.NODE, rid="finalizer_rid", type_key="finalizer", reads={"processed"}, writes={"output"}, after=["node2"])
        
        for step in [node1, node2, finalizer]:
            store[ResourceCategory.NODE][step.rid] = create_rt_elem(step.rid)
        
        logical_plan = GraphPlan()
        for step in [node1, node2, finalizer]:
            logical_plan.add_step(step)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        for rid in ["node1_rid", "node2_rid", "finalizer_rid"]:
            mock_nodes[rid].set_context.assert_called_once()
            context = mock_nodes[rid].set_context.call_args[0][0]
            assert isinstance(context, StepContext)
            assert isinstance(context.topology, StepTopology)
    
    def test_step_context_contains_correct_topology(self, mock_registries):
        """Test that each node's StepContext contains correct topology for that node."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        node1 = Step(uid="node1", category=ResourceCategory.NODE, rid="node1_rid", type_key="node1", writes={"data1"})
        node2 = Step(uid="node2", category=ResourceCategory.NODE, rid="node2_rid", type_key="node2", reads={"data1"}, writes={"data2"}, after=["node1"])
        finalizer = Step(uid="finalizer", category=ResourceCategory.NODE, rid="finalizer_rid", type_key="finalizer", reads={"data2"}, writes={"output"}, after=["node2"])
        
        for step in [node1, node2, finalizer]:
            store[ResourceCategory.NODE][step.rid] = create_rt_elem(step.rid)
        
        logical_plan = GraphPlan()
        for step in [node1, node2, finalizer]:
            logical_plan.add_step(step)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        # Check node1's context
        node1_context = mock_nodes["node1_rid"].set_context.call_args[0][0]
        assert node1_context.uid == "node1"
        assert node1_context.topology.has_finalizer_path()
        assert node1_context.topology.get_distance_to_finalizer("node2") == 2  # node2 -> finalizer + 1
        
        # Check node2's context
        node2_context = mock_nodes["node2_rid"].set_context.call_args[0][0]
        assert node2_context.uid == "node2"
        assert node2_context.topology.has_finalizer_path()
        assert node2_context.topology.get_distance_to_finalizer("finalizer") == 1  # Direct to finalizer
        
        # Check finalizer's context
        finalizer_context = mock_nodes["finalizer_rid"].set_context.call_args[0][0]
        assert finalizer_context.uid == "finalizer"
        assert not finalizer_context.topology.has_finalizer_path()  # No adjacent nodes
    
    def test_step_context_includes_adjacent_nodes(self, mock_registries):
        """Test that StepContext includes both adjacent nodes and topology."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        orchestrator = Step(uid="orchestrator", category=ResourceCategory.NODE, rid="orchestrator_rid", type_key="orchestrator", writes={"messages"})
        agent1 = Step(uid="agent1", category=ResourceCategory.NODE, rid="agent1_rid", type_key="agent", reads={"messages"}, writes={"output"}, after=["orchestrator"])
        agent2 = Step(uid="agent2", category=ResourceCategory.NODE, rid="agent2_rid", type_key="agent", reads={"messages"}, writes={"output"}, after=["orchestrator"])
        
        for step in [orchestrator, agent1, agent2]:
            store[ResourceCategory.NODE][step.rid] = create_rt_elem(step.rid)
        
        logical_plan = GraphPlan()
        for step in [orchestrator, agent1, agent2]:
            logical_plan.add_step(step)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        # Check orchestrator's context
        context = mock_nodes["orchestrator_rid"].set_context.call_args[0][0]
        
        # Should have adjacent nodes
        assert len(context.adjacent_nodes) == 2
        assert "agent1" in context.adjacent_nodes
        assert "agent2" in context.adjacent_nodes
        
        # Should have topology for those adjacent nodes
        assert context.topology.has_finalizer_path()
        assert context.topology.get_distance_to_finalizer("agent1") == 1
        assert context.topology.get_distance_to_finalizer("agent2") == 1
        assert set(context.topology.get_finalizer_reachable_nodes()) == {"agent1", "agent2"}
    
    def test_nodes_without_set_context_method(self, mock_registries):
        """Test that nodes without set_context method don't cause errors."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        node_without_context = Mock()
        del node_without_context.set_context
        mock_nodes["node1_rid"] = node_without_context
        
        node1 = Step(uid="node1", category=ResourceCategory.NODE, rid="node1_rid", type_key="node1", writes={"output"})
        
        store[ResourceCategory.NODE][node1.rid] = create_rt_elem(node1.rid)
        
        logical_plan = GraphPlan()
        logical_plan.add_step(node1)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        registry.get_instance.assert_called_with(ResourceCategory.NODE, "node1_rid")


class TestRTGraphPlanCoreFeatures:
    """Test that RTGraphPlan core features work with new topology system."""
    
    @pytest.fixture
    def mock_registries(self):
        """Create mock registries for testing."""
        return create_mock_fixtures()
    
    def test_existing_functionality_with_topology(self, mock_registries):
        """Test that existing RTGraphPlan functionality works with new topology."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        step = Step(
            uid="test_step",
            category=ResourceCategory.NODE,
            rid="test_rid",
            type_key="test",
            writes={"output"}
        )
        
        store[ResourceCategory.NODE][step.rid] = create_rt_elem(step.rid)
        
        logical_plan = GraphPlan()
        logical_plan.add_step(step)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        # Existing methods should still work
        assert len(rt_plan.steps) == 1
        assert rt_plan.get_step("test_step") is not None
        assert len(rt_plan.get_roots()) == 1
        assert len(rt_plan.get_leaves()) == 1
        
        # Should be iterable
        steps = list(rt_plan)
        assert len(steps) == 1
        
        # Should have length
        assert len(rt_plan) == 1
    
    def test_step_context_with_new_topology(self, mock_registries):
        """Test that StepContext works correctly with new topology composition."""
        registry, elem_registry, mock_nodes, store, create_rt_elem = mock_registries
        
        step = Step(
            uid="test_step",
            category=ResourceCategory.NODE,
            rid="test_rid",
            type_key="test",
            writes={"output"}
        )
        
        store[ResourceCategory.NODE][step.rid] = create_rt_elem(step.rid)
        
        logical_plan = GraphPlan()
        logical_plan.add_step(step)
        
        rt_plan = RTGraphPlan(logical_plan, registry, elem_registry)
        
        context = mock_nodes["test_rid"].set_context.call_args[0][0]
        
        # All StepContext fields should be present
        assert hasattr(context, 'uid')
        assert hasattr(context, 'metadata')
        assert hasattr(context, 'adjacent_nodes')
        assert hasattr(context, 'branches')
        
        # Topology field with composition should be present
        assert hasattr(context, 'topology')
        assert isinstance(context.topology, StepTopology)
        
        # Should be able to access composed FinalizerPathInfo if present
        if context.topology.finalizer_paths:
            assert isinstance(context.topology.finalizer_paths, FinalizerPathInfo)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
