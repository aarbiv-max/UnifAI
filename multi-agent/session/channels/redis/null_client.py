"""
Null object pattern implementations for Redis.

Used when Redis is unavailable, allowing the system to continue
operating without streaming capabilities (graceful degradation).
"""


class NullRedis:
    """
    Null object pattern for Redis - used when Redis is unavailable.
    
    Allows the system to continue operating without streaming capabilities.
    All operations are no-ops that return safe defaults.
    """
    
    def __getattr__(self, name):
        return self._noop
    
    def _noop(self, *args, **kwargs):
        return None
    
    def ping(self):
        return False
    
    def pipeline(self):
        return NullPipeline()
    
    def xadd(self, *args, **kwargs):
        return None
    
    def xrange(self, *args, **kwargs):
        return []
    
    def xread(self, *args, **kwargs):
        return []
    
    def hgetall(self, *args, **kwargs):
        return {}
    
    def sismember(self, *args, **kwargs):
        return False
    
    def smembers(self, *args, **kwargs):
        return set()
    
    def is_connected(self) -> bool:
        return False


class NullPipeline:
    """Null pipeline for NullRedis."""
    
    def __getattr__(self, name):
        return self._noop
    
    def _noop(self, *args, **kwargs):
        return self
    
    def execute(self):
        return []
