"""Connector domain layer - ports and interfaces."""

from core.connector.domain.base import DataConnector
from core.connector.domain.document_converter import (
    ConversionResult,
    DocumentConverterPort,
    DocumentConversionError,
)

__all__ = [
    "DataConnector",
    "ConversionResult",
    "DocumentConverterPort",
    "DocumentConversionError",
]
