from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ExecutionParams:
    """Serializable parameters for the run_session Temporal activity."""
    session_id: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    scope: str = "public"
    logged_in_user: str = ""
