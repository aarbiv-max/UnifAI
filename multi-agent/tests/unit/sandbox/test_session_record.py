"""Tests for SessionRecord sandbox_pvc_name field."""
import pytest

from mas.core.execution_context import ExecutionContext
from mas.session.domain.session_record import SessionRecord


class TestSessionRecordSandboxField:

    def test_sandbox_pvc_name_defaults_none(self):
        record = SessionRecord(
            run_id="run-1",
            user_id="u1",
            blueprint_id="bp1",
            run_context=ExecutionContext(),
        )
        assert record.sandbox_pvc_name is None

    def test_sandbox_pvc_name_set(self):
        record = SessionRecord(
            run_id="run-1",
            user_id="u1",
            blueprint_id="bp1",
            run_context=ExecutionContext(),
            sandbox_pvc_name="sandbox-pvc-abc12345",
        )
        assert record.sandbox_pvc_name == "sandbox-pvc-abc12345"

    def test_deserialization_without_sandbox_field(self):
        """Simulate loading an old document that lacks the field."""
        data = {
            "run_id": "run-1",
            "user_id": "u1",
            "blueprint_id": "bp1",
            "run_context": {},
        }
        record = SessionRecord.model_validate(data)
        assert record.sandbox_pvc_name is None

    def test_serialization_roundtrip(self):
        record = SessionRecord(
            run_id="run-1",
            user_id="u1",
            blueprint_id="bp1",
            run_context=ExecutionContext(),
            sandbox_pvc_name="pvc-xyz",
        )
        data = record.model_dump()
        restored = SessionRecord.model_validate(data)
        assert restored.sandbox_pvc_name == "pvc-xyz"
