"""迁移 analysis_runs 表到 datetime 窗口字段。

用法：
    在 back_end 目录执行：
    uv run python ..\\scripts\\migrate_analysis_runs_datetime.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "back_end"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402


def _has_column(conn, table_name: str, column_name: str) -> bool:
    row = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
              AND COLUMN_NAME = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).scalar_one()
    return bool(row)


def _has_index(conn, table_name: str, index_name: str) -> bool:
    row = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
              AND INDEX_NAME = :index_name
            """
        ),
        {"table_name": table_name, "index_name": index_name},
    ).scalar_one()
    return bool(row)


def main() -> None:
    engine = create_engine(settings.sqlalchemy_database_uri)

    with engine.begin() as conn:
        has_old_start = _has_column(conn, "analysis_runs", "window_start_date")
        has_old_end = _has_column(conn, "analysis_runs", "window_end_date")
        has_new_start = _has_column(conn, "analysis_runs", "window_start")
        has_new_end = _has_column(conn, "analysis_runs", "window_end")

        if has_new_start and has_new_end and not has_old_start and not has_old_end:
            print("analysis_runs migration already applied.")
            return

        if not has_old_start or not has_old_end:
            raise RuntimeError(
                "analysis_runs 表结构不符合预期：缺少旧字段 "
                "window_start_date/window_end_date，且新字段未完整存在。"
            )

        if _has_index(conn, "analysis_runs", "uq_analysis_runs_window_hash"):
            print("Dropping old unique index uq_analysis_runs_window_hash ...")
            conn.execute(text("ALTER TABLE analysis_runs DROP INDEX uq_analysis_runs_window_hash"))

        if not has_new_start:
            print("Adding column window_start ...")
            conn.execute(text("ALTER TABLE analysis_runs ADD COLUMN window_start DATETIME(6) NULL"))
        if not has_new_end:
            print("Adding column window_end ...")
            conn.execute(text("ALTER TABLE analysis_runs ADD COLUMN window_end DATETIME(6) NULL"))

        print("Backfilling datetime window columns ...")
        conn.execute(
            text(
                """
                UPDATE analysis_runs
                SET
                    window_start = COALESCE(
                        window_start,
                        CAST(CONCAT(window_start_date, ' 00:00:00.000000') AS DATETIME(6))
                    ),
                    window_end = COALESCE(
                        window_end,
                        CAST(CONCAT(window_end_date, ' 23:59:59.999999') AS DATETIME(6))
                    )
                """
            )
        )

        print("Enforcing NOT NULL on new columns ...")
        conn.execute(
            text(
                """
                ALTER TABLE analysis_runs
                MODIFY COLUMN window_start DATETIME(6) NOT NULL,
                MODIFY COLUMN window_end DATETIME(6) NOT NULL
                """
            )
        )

        print("Dropping old date columns ...")
        conn.execute(
            text(
                """
                ALTER TABLE analysis_runs
                DROP COLUMN window_start_date,
                DROP COLUMN window_end_date
                """
            )
        )

        print("Creating new unique index uq_analysis_runs_window_hash ...")
        conn.execute(
            text(
                """
                ALTER TABLE analysis_runs
                ADD CONSTRAINT uq_analysis_runs_window_hash
                UNIQUE (config_id, window_start, window_end, config_snapshot_hash)
                """
            )
        )

    print("analysis_runs datetime migration completed.")


if __name__ == "__main__":
    main()
