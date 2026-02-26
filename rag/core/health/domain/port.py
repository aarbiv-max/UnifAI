"""Health check domain port - protocol for health-checkable services."""

from typing import Protocol


class HealthCheckable(Protocol):
    """
    Protocol for services that support health checks.

    Both DocumentConnector and DefaultEmbeddingGenerator satisfy this protocol
    structurally (duck typing) without needing to inherit from it.
    """

    @property
    def is_remote(self) -> bool:
        """True if this service calls an external endpoint; False if purely local."""
        ...

    def test_connection(self) -> bool:
        """
        Test if the service is available.

        Returns:
            True if available, False otherwise
        """
        ...
