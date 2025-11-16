from typing import Union, Annotated
from pydantic import Field

from elements.nodes.custom_agent.config import CustomAgentNodeConfig
from elements.nodes.mock_agent.config import MockAgentNodeConfig
from elements.nodes.llm_merger.config import MergerLLMNodeConfig
from elements.nodes.final_answer.config import FinalAnswerNodeConfig
from elements.nodes.user_question.config import UserQuestionNodeConfig
from elements.nodes.branch_chooser.config import BranchChooserNodeConfig
from elements.nodes.orchestrator.config import OrchestratorNodeConfig

# Union type for backward compatibility with blueprints
NodeSpec = Annotated[
    Union[
        CustomAgentNodeConfig,
        MockAgentNodeConfig,
        MergerLLMNodeConfig,
        FinalAnswerNodeConfig,
        UserQuestionNodeConfig,
        BranchChooserNodeConfig,
        OrchestratorNodeConfig
    ],
    Field(discriminator="type")
]
