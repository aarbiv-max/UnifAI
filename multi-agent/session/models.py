from dataclasses import dataclass, field, asdict
from typing import Dict, Any
from enum import Enum


class SessionMode(str, Enum):
    PERSISTENT = "persistent"
    EPHEMERAL = "ephemeral"


@dataclass(frozen=True)
class RuntimeElement:
    """Complete runtime element: instance + config + spec."""
    instance: Any
    config: Any
    spec: Any


@dataclass(slots=True)
class SessionMeta:
    title: str | None = None
    tags: Dict[str, str] = field(default_factory=dict)
    mode: SessionMode = SessionMode.PERSISTENT

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMeta":
        return cls(**data)
