from enum import StrEnum

STREAM_PREFIX = "mas:stream:"
ACTIVE_SESSIONS_KEY = "mas:sessions:active"
CANCELLED_PREFIX = "mas:sessions:cancelled:"
CANCEL_FLAG_TTL = 120


class StreamField(StrEnum):
    PAYLOAD = "payload"
    CONTROL = "__control"


class ControlSignal(StrEnum):
    CLOSE = "close"
