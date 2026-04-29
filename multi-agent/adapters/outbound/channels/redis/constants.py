from enum import StrEnum

STREAM_PREFIX = "mas:stream:"
ACTIVE_SESSIONS_KEY = "mas:sessions:active"
CANCELLED_PREFIX = "mas:cancelled:"


class StreamField(StrEnum):
    PAYLOAD = "payload"
    CONTROL = "__control"


class ControlSignal(StrEnum):
    CLOSE = "close"
