"""Adapter registry. `get_adapter()` picks the one named by `data.adapter` in config.yaml."""
from __future__ import annotations

from app.core.config import get_settings
from app.ingest.adapters.base import DataAdapter


def get_adapter(name: str | None = None) -> DataAdapter:
    name = name or get_settings().data.adapter
    if name == "synthetic":
        from app.ingest.adapters.synthetic import SyntheticAdapter

        return SyntheticAdapter()
    if name == "amypo":
        from app.ingest.adapters.amypo import AmypoAdapter

        return AmypoAdapter()
    raise ValueError(f"unknown data adapter {name!r} (expected 'synthetic' or 'amypo')")
