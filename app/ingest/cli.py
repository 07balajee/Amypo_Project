"""Ingestion CLI: loads documents, structured records and training sets from the configured adapter
into the amypo database.

    python -m app.ingest.cli                                   # uses config.yaml / env
    python -m app.ingest.cli --db-url mysql://user:pass@host:3306/amypo
    python -m app.ingest.cli --adapter amypo --only tables,docs

The connection string can also come from DB__MYSQL__URL, which keeps the password out of your
shell history. Vector (Chroma) and BM25 indexing are built from the `chunks` table later (M4).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from app.core import config as config_module
from app.ingest.loaders import PARTS


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m app.ingest.cli", description=__doc__.splitlines()[0])
    ap.add_argument("--db-url", help="mysql://user:pass@host:port/database (overrides config)")
    ap.add_argument("--adapter", help="data adapter: synthetic | amypo (default: data.adapter)")
    ap.add_argument("--only", default=",".join(PARTS), help=f"comma list of {', '.join(PARTS)}")
    args = ap.parse_args(argv)

    if args.db_url:
        os.environ["DB__BACKEND"] = "mysql"
        os.environ["DB__MYSQL__URL"] = args.db_url
    settings = config_module.get_settings(reload=True)

    # Imported after settings are final so connections pick up --db-url.
    from app.core.db.conn import get_amypo_conn
    from app.ingest.adapters import get_adapter
    from app.ingest.loaders import load_all

    parts = tuple(p.strip() for p in args.only.split(",") if p.strip())
    adapter = get_adapter(args.adapter)
    db = settings.db
    target = (
        f"mysql://{db.mysql.user}@{db.mysql.host}:{db.mysql.port}/{db.mysql.amypo_database}"
        if db.backend == "mysql"
        else f"sqlite:{db.sqlite.amypo_db_path} (dir {db.sqlite.dir})"
    )
    print(f"ingest: adapter={adapter.name} parts={','.join(parts)} -> {target}")

    started = time.perf_counter()
    with get_amypo_conn() as conn:
        report = load_all(adapter, conn, parts)
    elapsed = time.perf_counter() - started

    width = max(len(t) for t in report.counts)
    for table, n in report.counts.items():
        print(f"  {table:<{width}}  {n:>6}")
    if report.index_version:
        print(f"  index_version: {report.index_version}")
    print(f"done in {elapsed:.1f}s")
    if report.dangling_record_ids:
        print(
            f"WARNING: {len(report.dangling_record_ids)} cited record_ids do not resolve, e.g. "
            f"{report.dangling_record_ids[:5]}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
