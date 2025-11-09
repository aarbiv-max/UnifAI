"""
Fixtures for StepContext and related objects.

Provides fixtures for creating test contexts with various configurations.
"""

import pytest
from tests.base.test_helpers import create_test_step_context


@pytest.fixture
def step_context():
    """
    Create a basic StepContext for testing.
    
    Returns:
        StepContext with a test node and no adjacency
    """
    return create_test_step_context("test_node")


@pytest.fixture
def step_context_with_adjacency():
    """
    Create a StepContext with adjacent nodes for testing.
    
    Returns:
        StepContext with test node and 3 adjacent nodes
    """
    return create_test_step_context("test_node", ["adjacent_1", "adjacent_2", "adjacent_3"])


@pytest.fixture
def orchestrator_step_context():
    """
    Create a StepContext specifically for orchestrator node testing.
    
    Returns:
        StepContext configured for orchestrator with worker nodes
    """
    return create_test_step_context(
        uid="test_orchestrator",
        adjacent_nodes=["data_processor", "report_generator", "analyzer"]
    )


@pytest.fixture
def orchestrator_step_context_with_many_nodes():
    """
    Create a StepContext with many adjacent nodes for testing.
    
    Returns:
        StepContext with orchestrator and 10 worker nodes
    """
    adjacent_nodes = [f"node_{i}" for i in range(10)]
    return create_test_step_context(
        uid="test_orchestrator", 
        adjacent_nodes=adjacent_nodes
    )


@pytest.fixture
def orchestrator_step_context_isolated():
    """
    Create a StepContext with no adjacent nodes for testing.
    
    Returns:
        StepContext for orchestrator with no workers
    """
    return create_test_step_context(uid="test_orchestrator", adjacent_nodes=[])
