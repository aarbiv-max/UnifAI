"""
Card builder for CustomAgentNode.

Composes skills from dependencies (tools, providers).
"""
from typing import Dict, List

from mas.elements.common.card.default import DefaultCardBuilder
from mas.elements.common.card.models.card import Capability, ElementCard


class CustomAgentCardBuilder(DefaultCardBuilder):
    """CustomAgent card builder with file-upload capability detection."""

    _GOOGLE_GENAI_TYPE_KEY = "google_genai"

    def _compose_capabilities_from_dependencies(
        self,
        dependency_cards: Dict[str, ElementCard],
    ) -> List[Capability]:
        capabilities = super()._compose_capabilities_from_dependencies(
            dependency_cards,
        )
        if any(
            card.type_key == self._GOOGLE_GENAI_TYPE_KEY
            for card in dependency_cards.values()
        ):
            capabilities.append(Capability(
                name="supports_file_upload",
                description="Can process file attachments via Gemini File API",
            ))
        return capabilities
