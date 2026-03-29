from multi_agent.lib.mas.elements.nodes.a2a_agent.a2a_agent_node import A2AAgentNode


def a2a_agent_node_factory(
    id: str, node_config: dict, template_id: str | None = None, summary: str | None = None, retriever: dict | None = None
) -> A2AAgentNode:
    return A2AAgentNode(id=id, node_config=node_config, template_id=template_id, summary=summary, retriever=retriever)