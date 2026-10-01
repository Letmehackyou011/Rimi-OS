"""Small in-process event stream for live scan telemetry."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
_cancelled_scans: set[str] = set()


def publish_scan_event(scan_id: str, event: str, **data: Any) -> dict[str, Any]:
    item = {
        "scan_id": scan_id,
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    _events[scan_id].append(item)
    _events[scan_id] = _events[scan_id][-500:]
    return item


def get_scan_events(scan_id: str, after: int = 0) -> list[dict[str, Any]]:
    return _events[scan_id][max(after, 0):]


def mark_scan_cancelled(scan_id: str) -> None:
    _cancelled_scans.add(scan_id)
    publish_scan_event(scan_id, "scan_cancelled")


def is_scan_cancelled(scan_id: str) -> bool:
    return scan_id in _cancelled_scans
