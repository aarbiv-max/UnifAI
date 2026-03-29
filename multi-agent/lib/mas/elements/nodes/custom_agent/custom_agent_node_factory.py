from multi_agent.lib.mas.elements.nodes.custom_agent.custom_agent import CustomAgent


def custom_agent_node_factory(
    id: str, node_config: dict, template_id: str | None = None, summary: str | None = None, retriever: dict | None = None
) -> CustomAgent:
    return CustomAgent(id=id, node_config=node_config, template_id=template_id, summary=summary, retriever=retriever)