"""Resource snapshot + a minimal monitor.

M0/M3 scope: live psutil RAM/CPU + manual overrides (via admin/simulate) applied field-by-field.
Scenario-file replay on a clock (simulator.mode == "scenario") and gateway-reported queue depth /
tokens-per-second are added in M3 — this is deliberately the smallest thing that satisfies the
GET /api/v1/resource-status contract today.
"""
from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import psutil

Source = str  # "live" | "scenario" | "manual"


@dataclass(frozen=True)
class Snapshot:
    ram_available_mb: float
    cpu_load_pct: float
    bandwidth_kbps: float
    api_quota_remaining: float
    source: Source
    sampled_at: str

    def to_dict(self) -> dict:
        return asdict(self)


# Fallbacks for fields psutil can't measure (no real network/quota simulator wired up yet).
_DEFAULT_BANDWIDTH_KBPS = 512.0
_DEFAULT_QUOTA_REMAINING = 1000.0


class ResourceMonitor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._overrides: dict[str, float] = {}
        self._mode = "manual"

    def set_manual(self, **fields: float | None) -> None:
        with self._lock:
            for key, value in fields.items():
                if value is not None:
                    self._overrides[key] = value
            self._mode = "manual"

    def clear_overrides(self) -> None:
        with self._lock:
            self._overrides.clear()

    def get_snapshot(self) -> Snapshot:
        live_ram = psutil.virtual_memory().available / (1024 * 1024)
        live_cpu = psutil.cpu_percent(interval=None)
        with self._lock:
            overrides = dict(self._overrides)
        values = {
            "ram_available_mb": live_ram,
            "cpu_load_pct": live_cpu,
            "bandwidth_kbps": _DEFAULT_BANDWIDTH_KBPS,
            "api_quota_remaining": _DEFAULT_QUOTA_REMAINING,
        }
        values.update(overrides)
        source: Source = "manual" if overrides else "live"
        return Snapshot(
            **values,
            source=source,
            sampled_at=datetime.now(UTC).isoformat(),
        )


_monitor: ResourceMonitor | None = None


def get_monitor() -> ResourceMonitor:
    global _monitor
    if _monitor is None:
        _monitor = ResourceMonitor()
    return _monitor
