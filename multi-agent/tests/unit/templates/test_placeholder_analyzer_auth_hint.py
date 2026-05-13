"""
Unit tests for PlaceholderAnalyzer — auth hint passthrough.

Verifies that a field with AuthHint in json_schema_extra (specifically the
McpProviderConfig.sign_in field) is correctly preserved when PlaceholderAnalyzer
generates a field definition, so the frontend can detect and render auth widgets.
"""

import pytest
from typing import Optional
from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from unittest.mock import MagicMock

from mas.templates.schema.analyzer import PlaceholderAnalyzer
from mas.templates.models.template import PlaceholderPointer
from mas.core.field_hints import AuthHint, ConditionalHint, combine_hints
from mas.elements.providers.mcp_server_client.config import McpProviderConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def registry():
    """Minimal mock registry (not needed for unit-level field extraction tests)."""
    return MagicMock()


@pytest.fixture
def analyzer(registry):
    return PlaceholderAnalyzer(registry)


@pytest.fixture
def sign_in_placeholder():
    return PlaceholderPointer(
        field_path="sign_in",
        required=False,
        label="Google Workspace",
        hint="Click below to sign in with Google",
    )


# ---------------------------------------------------------------------------
# Tests: _extract_single_field for McpProviderConfig.sign_in
# ---------------------------------------------------------------------------


class TestAuthHintExtraction:
    """Tests for PlaceholderAnalyzer._extract_single_field with auth hints."""

    def test_sign_in_field_is_found_in_mcp_provider_config(
        self, analyzer, sign_in_placeholder
    ):
        """PlaceholderAnalyzer must locate the sign_in field in McpProviderConfig."""
        field_def = analyzer._extract_single_field(McpProviderConfig, sign_in_placeholder)
        assert field_def is not None, (
            "sign_in must be found in McpProviderConfig; "
            "field was not returned by _extract_single_field"
        )

    def test_sign_in_field_name_is_correct(self, analyzer, sign_in_placeholder):
        """The extracted FieldDefinition must have name='sign_in'."""
        field_def = analyzer._extract_single_field(McpProviderConfig, sign_in_placeholder)
        assert field_def is not None
        assert field_def.name == "sign_in"

    def test_sign_in_field_info_carries_auth_hint(self, analyzer, sign_in_placeholder):
        """
        The FieldInfo for sign_in must preserve json_schema_extra containing hints.auth
        so the frontend can detect it as an auth widget.
        """
        field_def = analyzer._extract_single_field(McpProviderConfig, sign_in_placeholder)
        assert field_def is not None

        json_extra = field_def.field_info.json_schema_extra
        assert json_extra is not None, "sign_in field_info must have json_schema_extra"
        hints = json_extra.get("hints", {})
        assert "auth" in hints, (
            f"sign_in must carry hints.auth in json_schema_extra; "
            f"found hints keys: {list(hints.keys())}"
        )

    def test_auth_hint_has_correct_action_uid(self, analyzer, sign_in_placeholder):
        """hints.auth.action_uid must equal 'auth.authenticate'."""
        field_def = analyzer._extract_single_field(McpProviderConfig, sign_in_placeholder)
        assert field_def is not None

        auth_hint = field_def.field_info.json_schema_extra["hints"]["auth"]
        assert auth_hint.get("action_uid") == "auth.authenticate", (
            f"Expected action_uid='auth.authenticate', got: {auth_hint.get('action_uid')}"
        )

    def test_auth_hint_dependencies_map_mcp_url_to_server_identifier(
        self, analyzer, sign_in_placeholder
    ):
        """AuthHint.dependencies must contain mcp_url → server_identifier."""
        field_def = analyzer._extract_single_field(McpProviderConfig, sign_in_placeholder)
        assert field_def is not None

        deps = field_def.field_info.json_schema_extra["hints"]["auth"].get("dependencies", {})
        assert "mcp_url" in deps, (
            f"dependencies must contain 'mcp_url'; got keys: {list(deps.keys())}"
        )
        assert deps["mcp_url"] == "server_identifier", (
            f"mcp_url must map to 'server_identifier'; got: {deps['mcp_url']}"
        )

    def test_sign_in_placeholder_label_overrides_field_title(
        self, analyzer, sign_in_placeholder
    ):
        """PlaceholderPointer.label must be used as the field's title."""
        field_def = analyzer._extract_single_field(McpProviderConfig, sign_in_placeholder)
        assert field_def is not None
        assert field_def.field_info.title == "Google Workspace", (
            f"Expected title='Google Workspace', got: '{field_def.field_info.title}'"
        )

    def test_sign_in_placeholder_hint_overrides_description(
        self, analyzer, sign_in_placeholder
    ):
        """PlaceholderPointer.hint must be used as the field's description."""
        field_def = analyzer._extract_single_field(McpProviderConfig, sign_in_placeholder)
        assert field_def is not None
        assert field_def.field_info.description == "Click below to sign in with Google"

    def test_unknown_field_path_returns_none(self, analyzer):
        """A PlaceholderPointer with an unknown field_path must return None (skipped)."""
        bad_placeholder = PlaceholderPointer(
            field_path="nonexistent_xyz",
            required=False,
            label="Bad",
            hint="Should be skipped",
        )
        field_def = analyzer._extract_single_field(McpProviderConfig, bad_placeholder)
        assert field_def is None, (
            "Unknown field paths must be silently skipped (return None)"
        )

    def test_mcp_url_field_is_found(self, analyzer):
        """mcp_url must also be found when used as a placeholder field_path."""
        mcp_url_placeholder = PlaceholderPointer(
            field_path="mcp_url",
            required=False,
            label="MCP URL",
            hint="The MCP server URL",
        )
        field_def = analyzer._extract_single_field(McpProviderConfig, mcp_url_placeholder)
        assert field_def is not None
        assert field_def.name == "mcp_url"


# ---------------------------------------------------------------------------
# Tests: _create_field_info passthrough of json_schema_extra
# ---------------------------------------------------------------------------


class TestCreateFieldInfoAuthPassthrough:
    """Tests for _create_field_info preserving json_schema_extra."""

    def test_json_schema_extra_is_preserved(self, analyzer):
        """_create_field_info must pass through json_schema_extra unchanged."""
        auth_extra = combine_hints(
            ConditionalHint(visible_when={"auth_method": "sign_in"}),
            AuthHint(
                action_uid="auth.authenticate",
                dependencies={"mcp_url": "server_identifier"},
            ),
        )
        original = FieldInfo(
            default=None,
            description="Sign in",
            json_schema_extra=auth_extra,
        )
        placeholder = PlaceholderPointer(
            field_path="sign_in",
            required=False,
            label="Sign In",
            hint="Click to sign in",
        )
        result = analyzer._create_field_info(original, placeholder)
        assert result.json_schema_extra == auth_extra, (
            "_create_field_info must pass through json_schema_extra verbatim"
        )

    def test_json_schema_extra_none_stays_none(self, analyzer):
        """_create_field_info must not inject json_schema_extra when original is None."""
        original = FieldInfo(default=None, description="Plain field")
        placeholder = PlaceholderPointer(
            field_path="plain",
            required=False,
            label="Plain",
            hint="A plain field",
        )
        result = analyzer._create_field_info(original, placeholder)
        assert result.json_schema_extra is None

    def test_auth_hint_action_uid_accessible_after_passthrough(self, analyzer):
        """After passthrough, the action_uid is readable from json_schema_extra."""
        auth_extra = AuthHint(
            action_uid="auth.authenticate",
            dependencies={"mcp_url": "server_identifier"},
        ).to_hints()
        original = FieldInfo(default=None, json_schema_extra=auth_extra)
        placeholder = PlaceholderPointer(
            field_path="sign_in",
            required=False,
            label="L",
            hint="H",
        )
        result = analyzer._create_field_info(original, placeholder)
        uid = result.json_schema_extra["hints"]["auth"]["action_uid"]
        assert uid == "auth.authenticate"
