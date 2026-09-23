"""Exports a merged OpenAPI spec (router + qa) to openapi.yaml at repo root.

CLAUDE.md §6: "Keep openapi.yaml in sync (export from FastAPI and commit; a test fails if they
drift)." Run `python scripts/export_openapi.py` after any schema/route change, then commit the
diff. tests/contract/test_openapi_sync.py fails CI if someone forgets.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "openapi.yaml"


def build_merged_spec() -> dict:
    from app.qa.api import app as qa_app
    from app.router.api import app as router_app

    router_spec = router_app.openapi()
    qa_spec = qa_app.openapi()

    merged = {
        "openapi": router_spec["openapi"],
        "info": {
            "title": "AMYPO Unified Platform API",
            "version": router_spec["info"]["version"],
            "description": "PS1 Router (POST /api/v1/route, ...) + PS7 Q&A (POST /api/v1/ask, ...). "
            "See CLAUDE.md for the full spec.",
        },
        "servers": [
            {"url": "http://router:8000", "description": "router service (PS1)"},
            {"url": "http://qa:8001", "description": "qa service (PS7)"},
        ],
        "paths": {},
        "components": {"schemas": {}},
    }

    # router and qa are separate services on separate ports that happen to share a couple of
    # relative paths (e.g. /api/v1/health) with an identical contract — merge tags onto the
    # existing entry there instead of letting the second service's spec clobber the first's.
    for spec, tag in ((router_spec, "router"), (qa_spec, "qa")):
        for path, item in spec.get("paths", {}).items():
            for op in item.values():
                op.setdefault("tags", []).append(tag)
            if path in merged["paths"]:
                for method, op in item.items():
                    existing = merged["paths"][path].setdefault(method, op)
                    if existing is not op:
                        existing["tags"] = sorted(set(existing.get("tags", [])) | set(op.get("tags", [])))
            else:
                merged["paths"][path] = item
        for name, schema in spec.get("components", {}).get("schemas", {}).items():
            merged["components"]["schemas"][name] = schema

    return merged


def main() -> None:
    spec = build_merged_spec()
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(spec, f, sort_keys=False)
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
