"""迁移 summary_configs / summary_send_records 到 customer_grouped 所需结构。

用法：
    在 back_end 目录执行：
    uv run python ..\\scripts\\migrate_summary_customer_grouped.py
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
    return bool(
        conn.execute(
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
    )


def _has_index(conn, table_name: str, index_name: str) -> bool:
    return bool(
        conn.execute(
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
    )


def _has_fk(conn, table_name: str, constraint_name: str) -> bool:
    return bool(
        conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.REFERENTIAL_CONSTRAINTS
                WHERE CONSTRAINT_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                  AND CONSTRAINT_NAME = :constraint_name
                """
            ),
            {"table_name": table_name, "constraint_name": constraint_name},
        ).scalar_one()
    )


def main() -> None:
    engine = create_engine(settings.sqlalchemy_database_uri)

    with engine.begin() as conn:
        if not _has_column(conn, "summary_configs", "summary_scope_mode"):
            print("Adding summary_configs.summary_scope_mode ...")
            conn.execute(
                text(
                    """
                    ALTER TABLE summary_configs
                    ADD COLUMN summary_scope_mode VARCHAR(32) NOT NULL DEFAULT 'flat'
                    """
                )
            )

        if not _has_column(conn, "summary_configs", "include_unidentified_senders"):
            print("Adding summary_configs.include_unidentified_senders ...")
            conn.execute(
                text(
                    """
                    ALTER TABLE summary_configs
                    ADD COLUMN include_unidentified_senders TINYINT(1) NOT NULL DEFAULT 1
                    """
                )
            )

        if not _has_column(conn, "summary_configs", "top_n_per_customer"):
            print("Adding summary_configs.top_n_per_customer ...")
            conn.execute(
                text(
                    """
                    ALTER TABLE summary_configs
                    ADD COLUMN top_n_per_customer INT NOT NULL DEFAULT 5
                    """
                )
            )

        if not _has_column(conn, "summary_configs", "customer_analysis_mode"):
            print("Adding summary_configs.customer_analysis_mode ...")
            conn.execute(
                text(
                    """
                    ALTER TABLE summary_configs
                    ADD COLUMN customer_analysis_mode VARCHAR(32) NOT NULL DEFAULT 'basic'
                    """
                )
            )

        if not _has_column(conn, "summary_send_records", "analysis_run_id"):
            print("Adding summary_send_records.analysis_run_id ...")
            conn.execute(
                text(
                    """
                    ALTER TABLE summary_send_records
                    ADD COLUMN analysis_run_id VARCHAR(36) NULL
                    """
                )
            )

        if not _has_index(conn, "summary_send_records", "analysis_run_id"):
            print("Adding index summary_send_records.analysis_run_id ...")
            conn.execute(
                text(
                    """
                    ALTER TABLE summary_send_records
                    ADD INDEX analysis_run_id (analysis_run_id)
                    """
                )
            )

        if not _has_fk(conn, "summary_send_records", "summary_send_records_ibfk_2"):
            print("Adding FK summary_send_records_ibfk_2 -> analysis_runs(id) ...")
            conn.execute(
                text(
                    """
                    ALTER TABLE summary_send_records
                    ADD CONSTRAINT summary_send_records_ibfk_2
                    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
                    ON DELETE SET NULL
                    """
                )
            )

    print("summary customer_grouped migration completed.")


if __name__ == "__main__":
    main()
