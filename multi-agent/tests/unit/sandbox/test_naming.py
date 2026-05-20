"""Unit tests for sandbox naming utilities."""
import pytest

from mas.elements.tools.sandbox_exec.naming import sanitize_name


@pytest.mark.parametrize("raw,expected", [
    ("agent-1", "agent-1"),
    ("Agent_Node.2", "agent-node-2"),
    ("hello world!", "hello-world"),
    ("---", "default"),
    ("", "default"),
    ("UPPER_CASE", "upper-case"),
    ("a/b/c", "a-b-c"),
    ("simple", "simple"),
])
def test_sanitize_name(raw: str, expected: str):
    assert sanitize_name(raw) == expected


def test_sanitize_name_empty_returns_default():
    assert sanitize_name("") == "default"


def test_sanitize_name_only_special_chars_returns_default():
    assert sanitize_name("@#$%") == "default"
