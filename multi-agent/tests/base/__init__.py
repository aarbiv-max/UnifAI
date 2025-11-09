"""
Base test infrastructure.

Exports base test classes and helper functions for reuse across all tests.
All helpers here are GENERIC and work for ANY node type.
"""

from tests.base.base_node_test import BaseNodeTest, BaseOrchestratorTest, BaseCustomAgentTest
from tests.base.base_integration_test import BaseIntegrationTest
from tests.base.base_unit_test import BaseUnitTest
from tests.base.test_helpers import (
    # Core test setup (REAL objects, not mocks!)
    create_test_element_card,
    create_test_adjacent_nodes,
    create_test_step_context,
    setup_node_with_state,
    setup_node_with_context,
    assert_workplan_created,
    assert_has_workload_capability,
    assert_has_iem_capability,
    assert_has_llm_capability,
    assert_has_agent_capability,
    get_workspace_from_node,
    get_thread_from_node,
    get_root_threads_from_node,
    # Orchestration helpers
    create_work_plan_with_items,
    assert_work_plan_status,
    create_mock_worker_node,
    simulate_worker_response,
    create_predictable_llm_for_phases,
    # Thread hierarchy helpers
    create_thread_hierarchy,
    create_multi_level_hierarchy,
    assert_thread_hierarchy,
    assert_response_routes_to_root,
    get_hierarchy_depth,
    # Multi-node integration helpers
    create_custom_agent_node,
    create_orchestrator_node,
    connect_nodes,
    send_task_between_nodes,
    assert_agent_processed_task,
    wait_for_node_response,
    create_multi_node_scenario,
    # Real flow execution helpers
    setup_node_for_execution,
    setup_multi_node_env,
    create_task_packet,
    add_packet_to_inbox,
    add_packets_to_inbox,
    get_packets_from_outbox,
    find_packet_to_node,
    create_response_task,
    manually_add_to_outbox,
)

# Phase 2A: Real Flow Testing Helpers
from tests.base.flow_test_helpers import (
    # Mock LLM helpers
    create_mock_llm_with_tools,
    create_planning_llm,
    create_delegating_llm,
    create_planning_and_delegating_llm,  # Multi-phase orchestration
    # Flow execution
    execute_orchestrator_cycle,
    execute_agent_work,
    # Flow verification
    assert_llm_called_with_tools,
    assert_packets_sent,
    assert_work_plan_created,
    assert_work_plan_has_items,
    get_delegation_packets,
    # Complete flow patterns
    run_orchestration_flow,
    # Multi-round orchestration (Priority 2)
    create_stateful_llm,
    create_simple_agent_llm,
    create_stateful_agent_llm,
    create_multi_round_planning_llm,
    run_orchestration_until_complete,
    create_monitoring_llm,
    assert_orchestration_cycle_count,
    assert_work_plan_complete,
    get_work_plan_status_counts,
    # Delegation & Response Simulation (Generic Round-Trip Helpers)
    simulate_delegation_responses,
    execute_cycle_and_respond,
    get_latest_delegations,
    simulate_specific_responses,
)

__all__ = [
    # Base test classes
    'BaseNodeTest',
    'BaseOrchestratorTest', 
    'BaseCustomAgentTest',
    'BaseIntegrationTest',
    'BaseUnitTest',
    
    # GENERIC helper functions (work for ALL nodes - REAL objects!)
    'create_test_element_card',
    'create_test_adjacent_nodes',
    'create_test_step_context',
    'setup_node_with_state',
    'setup_node_with_context',
    'assert_workplan_created',
    'assert_has_workload_capability',
    'assert_has_iem_capability',
    'assert_has_llm_capability',
    'assert_has_agent_capability',
    'get_workspace_from_node',
    'get_thread_from_node',
    'get_root_threads_from_node',
    
    # GENERIC orchestration helpers
    'create_work_plan_with_items',
    'assert_work_plan_status',
    'create_mock_worker_node',
    'simulate_worker_response',
    'create_predictable_llm_for_phases',
    # Thread Hierarchy Helpers
    'create_thread_hierarchy',
    'create_multi_level_hierarchy',
    'assert_thread_hierarchy',
    'assert_response_routes_to_root',
    'get_hierarchy_depth',
    
    # Multi-Node Integration Helpers (Phase 2A)
    'create_custom_agent_node',
    'create_orchestrator_node',
    'connect_nodes',
    'send_task_between_nodes',
    'assert_agent_processed_task',
    'wait_for_node_response',
    'create_multi_node_scenario',
    
    # Real Flow Execution Helpers
    'setup_node_for_execution',
    'setup_multi_node_env',
    'create_task_packet',
    'add_packet_to_inbox',
    'add_packets_to_inbox',
    'get_packets_from_outbox',
    'find_packet_to_node',
    'create_response_task',
    'manually_add_to_outbox',
    
    # Phase 2A: Complete Flow Testing Helpers
    'create_mock_llm_with_tools',
    'create_planning_llm',
    'create_delegating_llm',
    'create_planning_and_delegating_llm',  # Multi-phase
    'execute_orchestrator_cycle',
    'execute_agent_work',
    'assert_llm_called_with_tools',
    'assert_packets_sent',
    'assert_work_plan_has_items',
    'get_delegation_packets',
    'run_orchestration_flow',
    # Multi-round orchestration (Priority 2)
    'create_stateful_llm',
    'create_simple_agent_llm',
    'create_stateful_agent_llm',
    'create_multi_round_planning_llm',
    'run_orchestration_until_complete',
    'create_monitoring_llm',
    'assert_orchestration_cycle_count',
    'assert_work_plan_complete',
    'get_work_plan_status_counts',
    # Delegation & Response Simulation (Generic Round-Trip Helpers)
    'simulate_delegation_responses',
    'execute_cycle_and_respond',
    'get_latest_delegations',
    'simulate_specific_responses',
]