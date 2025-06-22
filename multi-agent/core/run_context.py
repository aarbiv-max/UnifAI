from __future__ import annotations
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime
from typing import Any, Dict, Optional
import uuid


@dataclass(frozen=True)
class RunContext:
    """Immutable metadata about one graph‐execution run."""
    user_id: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    engine_name: Optional[str] = None

    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None

    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, Any] = field(default_factory=dict)
    scope: Optional[str] = "public"

    def change_scope(self, new_scope: str) -> RunContext:
        """Return a new context with the scope changed."""
        return replace(self, scope=new_scope)

    def mark_finished(self) -> RunContext:
        # create a new copy, updating finished_at
        return replace(self, finished_at=datetime.utcnow())

    def with_metadata(self, **entries) -> RunContext:
        # merge the metadata dict
        new_md = {**self.metadata, **entries}
        return replace(self, metadata=new_md)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["started_at"] = self.started_at.isoformat() + "Z"
        d["finished_at"] = (self.finished_at.isoformat() + "Z") if self.finished_at else None
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RunContext:
        d = data.copy()
        d["started_at"] = datetime.fromisoformat(d["started_at"].rstrip("Z"))
        if d.get("finished_at"):
            d["finished_at"] = datetime.fromisoformat(d["finished_at"].rstrip("Z"))
        return cls(**d)
