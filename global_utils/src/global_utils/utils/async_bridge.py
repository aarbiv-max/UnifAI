"""
AsyncBridge for safe sync→async execution.
Provides a centralized, thread-safe way to run async code from sync contexts.

Key Features:
- Singleton pattern for process-wide shared portal
- Version-compatible anyio API usage with multiple fallbacks
- Proper BlockingPortal context manager handling
- Thread-safe portal lifecycle management
- SOLID design with dependency injection and composition

"""
import asyncio
import threading
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterable, Optional, Protocol, runtime_checkable
import anyio
from anyio.from_thread import BlockingPortal
import anyio.from_thread
import logging

logger = logging.getLogger(__name__)

from .singleton import SingletonMeta


@runtime_checkable
class AsyncRunner(Protocol):
    """
    Interface Segregation: Minimal interface for running awaitables.
    Enables Dependency Inversion for testing and alternate implementations.
    """
    
    def run(self, awaitable: Awaitable[Any], timeout: Optional[float] = None) -> Any:
        """Run a single awaitable from sync context."""
        ...
    
    def run_many(
        self, 
        awaitables: Iterable[Awaitable[Any]], 
        timeout: Optional[float] = None, 
        limit: Optional[int] = None
    ) -> list[Any]:
        """Run multiple awaitables concurrently from sync context."""
        ...
    
    def close(self) -> None:
        """Clean up resources."""
        ...


@dataclass(frozen=True)
class BridgeConfig:
    """
    Value Object: Immutable configuration.
    Single Responsibility: Hold configuration data.
    """
    default_timeout: Optional[float] = None
    max_concurrent: int = 100
    portal_backend: str = "asyncio"  # or "trio"


class PortalLifecycleManager:
    """
    Single Responsibility: Manage BlockingPortal lifecycle.
    Handles thread-safe creation, reuse, and cleanup with reference counting.
    """
    
    def __init__(self, config: BridgeConfig):
        self._config = config
        self._lock = threading.RLock()
        self._portal_context = None
        self._portal: Optional[BlockingPortal] = None
        self._closed = False
        self._ref_count = 0  # Reference counting for safe context manager usage
    
    def acquire_portal(self) -> BlockingPortal:
        """Get or create the shared portal and increment reference count."""
        with self._lock:
            if self._closed:
                raise RuntimeError("AsyncBridge has been closed")
            
            self._ref_count += 1
            
            if self._portal is None:
                # Create portal context manager and enter it
                # Try simpler approaches first for better compatibility
                portal_created = False
                
                # Try 1: Simple anyio.from_thread.start_blocking_portal without backend
                if not portal_created:
                    try:
                        logger.debug("Trying anyio.from_thread.start_blocking_portal() without backend")
                        self._portal_context = anyio.from_thread.start_blocking_portal()
                        portal_created = True
                    except AttributeError:
                        logger.debug("anyio.from_thread.start_blocking_portal not available")
                
                # Try 2: With backend specification
                if not portal_created:
                    try:
                        logger.debug("Trying anyio.from_thread.start_blocking_portal with backend")
                        self._portal_context = anyio.from_thread.start_blocking_portal(
                            backend=self._config.portal_backend
                        )
                        portal_created = True
                    except (AttributeError, TypeError):
                        logger.debug("anyio.from_thread.start_blocking_portal with backend failed")
                
                # Try 3: Fallback to anyio.start_blocking_portal (if it exists)
                if not portal_created:
                    try:
                        logger.debug("Trying anyio.start_blocking_portal")
                        self._portal_context = anyio.start_blocking_portal()
                        portal_created = True
                    except AttributeError:
                        logger.debug("anyio.start_blocking_portal not available")
                
                if not portal_created:
                    raise RuntimeError("No compatible anyio blocking portal API found")
                
                # Enter the context to get the actual portal
                try:
                    self._portal = self._portal_context.__enter__()
                    logger.debug("Successfully entered portal context")
                except Exception as e:
                    logger.error(f"Failed to enter portal context: {e}")
                    self._portal_context = None
                    raise RuntimeError(f"Failed to create blocking portal: {e}")
            
            return self._portal
    
    def release_portal(self) -> None:
        """Decrement reference count and close portal if no more references."""
        with self._lock:
            if self._ref_count > 0:
                self._ref_count -= 1
                logger.debug(f"Released portal reference, count now: {self._ref_count}")
                
            # Only close when no more references
            if self._ref_count == 0 and self._portal is not None:
                self._close_portal()
    
    def _close_portal(self) -> None:
        """Internal method to actually close the portal."""
        try:
            # Exit the context manager properly
            if self._portal_context is not None:
                self._portal_context.__exit__(None, None, None)
                logger.debug("Successfully closed portal context")
        except Exception as e:
            logger.warning(f"Error closing portal context: {e}")
        
        self._portal = None
        self._portal_context = None
    
    def force_close(self) -> None:
        """Force close the portal and mark as closed (for shutdown)."""
        with self._lock:
            if self._portal is not None:
                self._close_portal()
            self._closed = True
            self._ref_count = 0
    
    @property
    def is_closed(self) -> bool:
        """Check if the manager is closed."""
        with self._lock:
            return self._closed


class ExecutionGuard:
    """
    Single Responsibility: Validate execution context.
    Prevents deadlocks by detecting unsafe execution contexts.
    """
    
    @staticmethod
    def validate_sync_execution() -> None:
        """
        Ensure we're not in an event loop thread.
        Open/Closed: Easy to extend with more validations.
        """
        try:
            loop = asyncio.get_running_loop()
            current_thread = threading.current_thread()
            
            # Check if we're in the event loop thread
            if hasattr(loop, '_thread_id'):
                loop_thread_id = loop._thread_id
                if current_thread.ident == loop_thread_id:
                    raise RuntimeError(
                        "AsyncBridge.run() called from event loop thread. "
                        "Use 'await' directly or call from a different thread."
                    )
        except RuntimeError:
            # No running loop - safe to proceed
            pass


class TimeoutManager:
    """
    Single Responsibility: Handle timeout logic.
    Encapsulates timeout resolution and application.
    """
    
    def __init__(self, config: BridgeConfig):
        self._config = config
    
    def resolve_timeout(self, provided_timeout: Optional[float]) -> Optional[float]:
        """Resolve effective timeout from provided and default values."""
        return provided_timeout if provided_timeout is not None else self._config.default_timeout
    
    async def apply_timeout(self, awaitable: Awaitable[Any], timeout: Optional[float]) -> Any:
        """Apply timeout to an awaitable if specified."""
        if timeout is not None:
            with anyio.fail_after(timeout):
                return await awaitable
        return await awaitable


class ConcurrentExecutor:
    """
    Single Responsibility: Execute multiple awaitables concurrently.
    Strategy pattern: Could be extended with different execution strategies.
    """
    
    def __init__(self, config: BridgeConfig, timeout_manager: TimeoutManager):
        self._config = config
        self._timeout_manager = timeout_manager
    
    async def execute_many(
        self,
        awaitables: list[Awaitable[Any]],
        timeout: Optional[float],
        limit: Optional[int]
    ) -> list[Any]:
        """Execute multiple awaitables with concurrency control."""
        if not awaitables:
            return []
        
        results: list[Any] = [None] * len(awaitables)
        effective_limit = min(limit or self._config.max_concurrent, len(awaitables))
        semaphore = anyio.Semaphore(effective_limit)
        
        async def _execute_one(index: int, awaitable: Awaitable[Any]) -> None:
            async with semaphore:
                results[index] = await self._timeout_manager.apply_timeout(awaitable, timeout)
        
        async with anyio.create_task_group() as task_group:
            for i, awaitable in enumerate(awaitables):
                task_group.start_soon(_execute_one, i, awaitable)
        
        return results


class BlockingPortalAsyncRunner(AsyncRunner):
    """
    Concrete AsyncRunner implementation using anyio BlockingPortal.
    """
    
    def __init__(self, config: Optional[BridgeConfig] = None):
        self._config = config or BridgeConfig()
        self._portal_manager = PortalLifecycleManager(self._config)
        self._execution_guard = ExecutionGuard()
        self._timeout_manager = TimeoutManager(self._config)
        self._concurrent_executor = ConcurrentExecutor(self._config, self._timeout_manager)
    
    def run(self, awaitable: Awaitable[Any], timeout: Optional[float] = None) -> Any:
        """
        Template Method: Defines execution algorithm.
        """
        # Step 1: Validate execution context
        self._execution_guard.validate_sync_execution()
        
        # Step 2: Get portal
        portal = self._portal_manager.acquire_portal()
        
        # Step 3: Resolve timeout
        effective_timeout = self._timeout_manager.resolve_timeout(timeout)
        
        # Step 4: Execute
        async def _runner():
            return await self._timeout_manager.apply_timeout(awaitable, effective_timeout)
        
        return portal.call(_runner)
    
    def run_many(
        self,
        awaitables: Iterable[Awaitable[Any]],
        timeout: Optional[float] = None,
        limit: Optional[int] = None
    ) -> list[Any]:
        """Execute multiple awaitables concurrently."""
        # Step 1: Validate and convert
        self._execution_guard.validate_sync_execution()
        awaitable_list = list(awaitables)
        
        if not awaitable_list:
            return []
        
        # Step 2: Get portal
        portal = self._portal_manager.acquire_portal()
        
        # Step 3: Resolve timeout
        effective_timeout = self._timeout_manager.resolve_timeout(timeout)
        
        # Step 4: Execute concurrently
        return portal.call(
            self._concurrent_executor.execute_many,
            awaitable_list,
            effective_timeout,
            limit
        )
    
    def close(self) -> None:
        """Clean up resources."""
        self._portal_manager.release_portal()


class AsyncBridge(metaclass=SingletonMeta):
    """
    Singleton AsyncBridge for process-wide async execution.
    Single Responsibility: Provide centralized sync→async bridge.
    Uses composition instead of inheritance to avoid metaclass conflicts.
    """
    
    def __init__(self, config: Optional[BridgeConfig] = None):
        self._runner = BlockingPortalAsyncRunner(config)
    
    def run(self, awaitable: Awaitable[Any], timeout: Optional[float] = None) -> Any:
        """Run a single awaitable from sync context."""
        return self._runner.run(awaitable, timeout)
    
    def run_many(
        self,
        awaitables: Iterable[Awaitable[Any]],
        timeout: Optional[float] = None,
        limit: Optional[int] = None
    ) -> list[Any]:
        """Run multiple awaitables concurrently from sync context."""
        return self._runner.run_many(awaitables, timeout, limit)
    
    def close(self) -> None:
        """Clean up resources."""
        self._runner.close()
    
    def force_close(self) -> None:
        """Force close all resources (for application shutdown)."""
        self._runner._portal_manager.force_close()
    
    def __enter__(self) -> 'AsyncBridge':
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up on context exit."""
        self.close()


# Convenience functions for easy usage
def get_async_bridge() -> AsyncRunner:
    """Get the singleton async bridge instance."""
    return AsyncBridge()


def run_async(awaitable: Awaitable[Any], timeout: Optional[float] = None) -> Any:
    """
    Convenience function for backward compatibility.
    Replaces the old run_async function with AsyncBridge.
    """
    with get_async_bridge() as bridge:
        return bridge.run(awaitable, timeout)


def run_many_async(
    awaitables: Iterable[Awaitable[Any]], 
    timeout: Optional[float] = None, 
    limit: Optional[int] = None
) -> list[Any]:
    """
    Convenience function for running multiple awaitables.
    """
    with get_async_bridge() as bridge:
        return bridge.run_many(awaitables, timeout, limit)
