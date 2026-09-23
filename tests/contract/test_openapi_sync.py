"""Fails if someone changes a route/schema without re-running scripts/export_openapi.py
(CLAUDE.md §6: "Keep openapi.yaml in sync ... a test fails if they drift")."""
import yaml

from scripts.export_openapi import OUTPUT_PATH, build_merged_spec


def test_openapi_yaml_matches_live_apps():
    committed = yaml.safe_load(OUTPUT_PATH.read_text(encoding="utf-8"))
    current = build_merged_spec()
    assert committed == current, (
        "openapi.yaml is out of sync with the FastAPI apps — "
        "run `python scripts/export_openapi.py` and commit the diff."
    )
