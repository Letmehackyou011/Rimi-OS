import pytest
from pydantic import ValidationError

from security.scope import ScopeDocument, ScopeTarget, SecurityMode, ToolName, scope_from_request


def test_scope_requires_requested_target():
    with pytest.raises(ValueError, match="must be present"):
        scope_from_request(
            "example.com",
            ScopeDocument(targets=[ScopeTarget(host="other.example")]),
            "safe",
        )


def test_safe_mode_rejects_packet_capture():
    with pytest.raises(ValidationError, match="safe mode"):
        ScopeDocument(
            mode=SecurityMode.SAFE,
            targets=[ScopeTarget(host="example.com")],
            tool_allowlist=[ToolName.TCPDUMP],
        )


def test_scope_rejects_shell_characters():
    with pytest.raises(ValidationError, match="invalid characters"):
        ScopeTarget(host="example.com;whoami")


def test_human_review_scope_is_valid_without_release_token():
    scope = ScopeDocument(
        mode=SecurityMode.HUMAN_REVIEW,
        targets=[ScopeTarget(host="example.com")],
    )
    assert scope.approval_token is None
