from dataclasses import dataclass, field, asdict
from typing import Dict, Any


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
    from_shared_link: bool = False  # Indicates if session was created from a public chat link

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMeta":
        # Handle backward compatibility - if from_shared_link is not present, default to False
        if 'from_shared_link' not in data:
            data['from_shared_link'] = False
        return cls(**data)
