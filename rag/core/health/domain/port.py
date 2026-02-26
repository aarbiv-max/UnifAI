"""Health check domain port - protocol for health-checkable services."""

from typing import Protocol


class HealthCheckable(Protocol):
    """
    Protocol for services that support health checks via test_connection().

    Both DocumentConverterPort and EmbeddingPort satisfy this protocol
    structurally (duck typing) without needing to inherit from it.
    """

    def test_connection(self) -> bool:
        """
        Test if the service is available.

        Returns:
            True if available, False otherwise
        """
        ...
