"""Allowlisted, timeout-bounded reconnaissance command runner."""

from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from security.events import publish_scan_event
from security.scope import ScopeDocument, ScopeTarget, ToolName


@dataclass
class ToolResult:
    tool: str
    status: str
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__


def _host(target: ScopeTarget) -> str:
    parsed = urlparse(target.host if "://" in target.host else f"//{target.host}")
    return parsed.hostname or target.host


def _command(tool: ToolName, target: ScopeTarget) -> list[str] | None:
    host = _host(target)
    if tool == ToolName.NMAP:
        ports = ",".join(str(port) for port in target.ports) if target.ports else "--top-ports 100"
        command = ["nmap", "-Pn", "-sT", "-T2", "--host-timeout", "30s"]
        command += ["-p", ports] if target.ports else ["--top-ports", "100"]
        return [*command, host]
    if tool == ToolName.CURL:
        url = target.host if "://" in target.host else f"https://{target.host}"
        path = target.paths[0] if target.paths else "/"
        return ["curl", "--silent", "--show-error", "--head", "--max-time", "15", "--proto", "=http,https", f"{url.rstrip('/')}{path}"]
    if tool == ToolName.TCPDUMP:
        if os.name != "posix":
            return None
        return ["tcpdump", "-nn", "-c", "20", "host", host]
    return None


async def _run(command: list[str], tool: ToolName, timeout: int) -> ToolResult:
    if not shutil.which(command[0]):
        return ToolResult(tool.value, "unavailable", command, stderr=f"{command[0]} is not installed")
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return ToolResult(tool.value, "completed" if process.returncode == 0 else "error", command, stdout.decode(errors="replace")[-12000:], stderr.decode(errors="replace")[-4000:], process.returncode)
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        return ToolResult(tool.value, "timeout", command, stderr="tool execution exceeded scope timeout")
    except OSError as exc:
        return ToolResult(tool.value, "error", command, stderr=str(exc))


async def run_reconnaissance(scope: ScopeDocument, scan_id: str) -> list[dict[str, Any]]:
    """Run only explicitly allowlisted tools with no shell interpolation."""
    results: list[dict[str, Any]] = []
    if scope.mode.value == "human_review" and not scope.approval_token:
        publish_scan_event(scan_id, "tool_gate", status="awaiting_human_review")
        return results
    for target in scope.targets:
        for tool in scope.tool_allowlist:
            if tool == ToolName.TCPDUMP and scope.mode.value == "safe":
                publish_scan_event(scan_id, "tool_skipped", tool=tool.value, reason="not permitted in safe mode")
                continue
            command = _command(tool, target)
            if command is None:
                publish_scan_event(scan_id, "tool_skipped", tool=tool.value, reason="unsupported on this host")
                continue
            publish_scan_event(scan_id, "tool_started", tool=tool.value, target=target.host)
            result = await _run(command, tool, min(scope.max_runtime_seconds, 120))
            results.append(result.as_dict())
            publish_scan_event(scan_id, "tool_finished", tool=tool.value, status=result.status, target=target.host)
    return results
