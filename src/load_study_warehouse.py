"""Load the study tables from the untouched Synthea copy into a local warehouse.

BigQuery is the warehouse named in the case. The bq command is not installed
on this machine, and no billing project was configured, so this script loads
DuckDB instead. The database is a local stand-in. It is not a BigQuery dataset.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw" / "synthea" / "csv"
DB = ROOT / "warehouse" / "riverbend.duckdb"

STUDY_TABLES = (
    "patients",
    "organizations",
    "providers",
    "payers",
    "encounters",
    "conditions",
    "observations",
    "medications",
    "procedures",
    "payer_transitions",
)


def main() -> int:
    if not RAW.exists():
        print(f"Missing {RAW}. Copy the Synthea export into data_raw first.", file=sys.stderr)
        return 1
    try:
        import duckdb
    except ImportError:
        print("duckdb is not installed. pip install duckdb", file=sys.stderr)
        return 1
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    connection = duckdb.connect(str(DB))
    for table in STUDY_TABLES:
        path = RAW / f"{table}.csv"
        if not path.exists():
            print(f"Missing {path}.", file=sys.stderr)
            return 1
        connection.execute(
            f"CREATE TABLE {table} AS SELECT * FROM read_csv(?, header = true, sample_size = -1)",
            [str(path)],
        )
        count = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"{table}\t{count}")
    connection.close()
    print(f"Wrote {DB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
