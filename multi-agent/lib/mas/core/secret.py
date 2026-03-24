from enum import Enum
from typing import Any, Dict

from pydantic import SecretStr
from pydantic_core import core_schema as cs


class SecretContext(str, Enum):
    """Keys used in Pydantic serialization context to control Secret output."""
    REVEAL = "reveal_secrets"
    STRIP = "strip_secrets"

    @classmethod
    def reveal(cls) -> Dict[str, Any]:
        """Context for DB persistence — exposes real secret values."""
        return {cls.REVEAL: True}

    @classmethod
    def strip(cls) -> Dict[str, Any]:
        """Context for sharing/cloning — replaces secrets with empty strings."""
        return {cls.STRIP: True}


class Secret(SecretStr):
    """Context-aware secret field.

    Serialization behaviour is controlled by the ``context`` argument
    passed to ``model_dump()`` / ``model_dump_json()``:

        model_dump(mode="json")                                 → '**********'
        model_dump(mode="json", context=SecretContext.reveal())  → real value
        model_dump(mode="json", context=SecretContext.strip())   → ''

    Use ``.get_secret_value()`` when you need the raw value at runtime
    (e.g. passing to an SDK constructor).
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        schema = super().__get_pydantic_core_schema__(source_type, handler)
        schema["serialization"] = cs.plain_serializer_function_ser_schema(
            cls._serialize, info_arg=True,
        )
        return schema

    @staticmethod
    def _serialize(value: "Secret", info) -> str:
        ctx = info.context or {}
        if ctx.get(SecretContext.REVEAL):
            return value.get_secret_value()
        if ctx.get(SecretContext.STRIP):
            return ""
        return "**********"
