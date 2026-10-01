"""Strict, JSON-serializable authorization scope for scan execution."""

from __future__ import annotations

import ipaddress
import re
from enum import Enum
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SecurityMode(str, Enum):
    SAFE = "safe"
    GUARDED = "guarded"
    FULL_ACCESS = "full_access"
    HUMAN_REVIEW = "human_review"


class ToolName(str, Enum):
    NMAP = "nmap"
    CURL = "curl"
    TCPDUMP = "tcpdump"


class ScopeTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = Field(min_length=1, max_length=253)
    ports: list[int] = Field(default_factory=list, max_length=128)
    paths: list[str] = Field(default_factory=list, max_length=128)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        value = value.strip()
        if not value or any(char in value for char in ";&|`$()<>\\\"'"):
            raise ValueError("host contains invalid characters")
        candidate = value
        if "://" in value:
            parsed = urlparse(value)
            candidate = parsed.hostname or ""
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?", candidate):
                raise ValueError("host must be an IP address or DNS name")
        return value

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("ports must be unique")
        return value

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, value: list[str]) -> list[str]:
        for path in value:
            if not path.startswith("/") or ".." in path or any(char in path for char in "\r\n"):
                raise ValueError("paths must be relative URL paths")
        return value


class ScopeDocument(BaseModel):
    """The only authorization object accepted by the execution layer."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="1", pattern=r"^1$")
    mode: SecurityMode = SecurityMode.SAFE
    targets: list[ScopeTarget] = Field(min_length=1, max_length=32)
    tool_allowlist: list[ToolName] = Field(default_factory=lambda: [ToolName.NMAP, ToolName.CURL])
    max_runtime_seconds: int = Field(default=120, ge=5, le=900)
    approval_token: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def enforce_mode_policy(self) -> "ScopeDocument":
        if self.mode == SecurityMode.SAFE:
            forbidden = set(self.tool_allowlist) - {ToolName.NMAP, ToolName.CURL}
            if forbidden:
                raise ValueError("safe mode permits only nmap and curl")
        if self.mode == SecurityMode.HUMAN_REVIEW and not self.approval_token:
            return self
        return self


def scope_from_request(target: str, scope: ScopeDocument | str | None, mode: str | None) -> ScopeDocument:
    """Normalize the API payload and require an explicit target authorization."""
    if isinstance(scope, ScopeDocument):
        document = scope
    elif isinstance(scope, str) and scope.strip():
        document = ScopeDocument.model_validate_json(scope)
    else:
        document = ScopeDocument(
            mode=mode or SecurityMode.SAFE,
            targets=[ScopeTarget(host=target)],
        )
    requested_hosts = {item.host.lower() for item in document.targets}
    if target.lower() not in requested_hosts:
        raise ValueError("request target must be present in scope.targets")
    if mode and document.mode.value != mode:
        raise ValueError("request mode does not match scope.mode")
    return document
