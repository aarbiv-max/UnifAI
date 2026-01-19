from enum import Enum, auto


class SessionStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    STOPPED = auto()  # User-initiated stop
