"""Unit tests for caller_uid_var context propagation."""
import asyncio
import contextvars
import threading

from mas.elements.tools.common.execution.context import caller_uid_var


class TestCallerUidVar:
    """Verify contextvar behavior matches design assumptions."""

    def test_default_is_empty_string(self):
        ctx = contextvars.copy_context()
        val = ctx.run(caller_uid_var.get)
        assert val == ""

    def test_set_and_get(self):
        ctx = contextvars.copy_context()
        ctx.run(caller_uid_var.set, "agent-123")
        assert ctx.run(caller_uid_var.get) == "agent-123"

    def test_isolation_between_contexts(self):
        ctx1 = contextvars.copy_context()
        ctx2 = contextvars.copy_context()

        ctx1.run(caller_uid_var.set, "agent-A")
        ctx2.run(caller_uid_var.set, "agent-B")

        assert ctx1.run(caller_uid_var.get) == "agent-A"
        assert ctx2.run(caller_uid_var.get) == "agent-B"

    def test_thread_isolation(self):
        """contextvars are inherited at thread creation but isolated after."""
        token = caller_uid_var.set("parent")
        results = {}

        def thread_fn(name, uid):
            caller_uid_var.set(uid)
            results[name] = caller_uid_var.get()

        t1 = threading.Thread(target=thread_fn, args=("t1", "child-1"))
        t2 = threading.Thread(target=thread_fn, args=("t2", "child-2"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results["t1"] == "child-1"
        assert results["t2"] == "child-2"

        caller_uid_var.reset(token)

    def test_asyncio_to_thread_propagation(self):
        """asyncio.to_thread copies the context to the thread."""
        async def main():
            caller_uid_var.set("async-agent")

            def sync_check():
                return caller_uid_var.get()

            result = await asyncio.to_thread(sync_check)
            return result

        result = asyncio.run(main())
        assert result == "async-agent"
