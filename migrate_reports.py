from __future__ import annotations

import argparse
from pathlib import Path

from report_exporter import REPORTS_DIR
from report_store import migrate_index_to_sqlite


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate reports/index.json into SQLite report history.")
    parser.add_argument("--reports-dir", default=str(REPORTS_DIR), help="Reports directory path.")
    args = parser.parse_args()

    inserted, skipped = migrate_index_to_sqlite(Path(args.reports_dir))
    print(
        f"Report history migration complete. inserted={inserted} skipped={skipped} reports_dir={args.reports_dir}"
    )


if __name__ == "__main__":
    main()
