"""创建服务报告 V1 所需表结构。

用法：
    在 back_end 目录执行：
    uv run python ..\\scripts\\migrate_service_report_v1.py
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


def _has_table(conn, table_name: str) -> bool:
    return bool(
        conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                """
            ),
            {"table_name": table_name},
        ).scalar_one()
    )


def main() -> None:
    engine = create_engine(settings.sqlalchemy_database_uri)

    with engine.begin() as conn:
        if not _has_table(conn, "service_report_configs"):
            print("Creating table service_report_configs ...")
            conn.execute(
                text(
                    """
                    CREATE TABLE service_report_configs (
                        id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL,
                        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                        updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                        name VARCHAR(120) COLLATE utf8mb4_unicode_ci NOT NULL,
                        project_name VARCHAR(120) COLLATE utf8mb4_unicode_ci NOT NULL,
                        report_type VARCHAR(32) COLLATE utf8mb4_unicode_ci NOT NULL,
                        period_rule VARCHAR(32) COLLATE utf8mb4_unicode_ci NOT NULL,
                        template_key VARCHAR(64) COLLATE utf8mb4_unicode_ci NOT NULL,
                        project_owner_user_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL,
                        template_owner_user_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL,
                        metric_owner_user_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL,
                        enabled TINYINT(1) NOT NULL DEFAULT 1,
                        recipient_emails JSON NOT NULL,
                        source_bindings JSON NOT NULL,
                        PRIMARY KEY (id),
                        UNIQUE KEY uq_service_report_configs_name (name),
                        KEY ix_service_report_configs_project_name (project_name),
                        KEY ix_service_report_configs_report_type (report_type),
                        KEY ix_service_report_configs_enabled (enabled),
                        CONSTRAINT fk_service_report_configs_project_owner
                            FOREIGN KEY (project_owner_user_id) REFERENCES users(id)
                            ON DELETE RESTRICT,
                        CONSTRAINT fk_service_report_configs_template_owner
                            FOREIGN KEY (template_owner_user_id) REFERENCES users(id)
                            ON DELETE RESTRICT,
                        CONSTRAINT fk_service_report_configs_metric_owner
                            FOREIGN KEY (metric_owner_user_id) REFERENCES users(id)
                            ON DELETE RESTRICT
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
            )
        else:
            print("Table service_report_configs already exists, skipping.")

        if not _has_table(conn, "service_report_source_runs"):
            print("Creating table service_report_source_runs ...")
            conn.execute(
                text(
                    """
                    CREATE TABLE service_report_source_runs (
                        id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL,
                        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                        updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                        config_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL,
                        window_start DATETIME(6) NOT NULL,
                        window_end DATETIME(6) NOT NULL,
                        status VARCHAR(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
                        included_sources JSON NOT NULL,
                        source_results JSON NOT NULL,
                        snapshot_payload JSON NULL,
                        error_message TEXT NULL,
                        finished_at DATETIME(6) NULL,
                        PRIMARY KEY (id),
                        KEY ix_service_report_source_runs_config_id (config_id),
                        KEY ix_service_report_source_runs_status (status),
                        CONSTRAINT fk_service_report_source_runs_config
                            FOREIGN KEY (config_id) REFERENCES service_report_configs(id)
                            ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
            )
        else:
            print("Table service_report_source_runs already exists, skipping.")

        if not _has_table(conn, "service_report_runs"):
            print("Creating table service_report_runs ...")
            conn.execute(
                text(
                    """
                    CREATE TABLE service_report_runs (
                        id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL,
                        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                        updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                        config_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL,
                        source_run_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL,
                        window_start DATETIME(6) NOT NULL,
                        window_end DATETIME(6) NOT NULL,
                        status VARCHAR(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
                        completeness_status VARCHAR(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'blocked',
                        config_snapshot JSON NOT NULL,
                        source_snapshot_summary JSON NOT NULL,
                        report_payload JSON NOT NULL,
                        manual_note TEXT NULL,
                        export_artifacts JSON NULL,
                        evidence_refs JSON NULL,
                        error_message TEXT NULL,
                        finished_at DATETIME(6) NULL,
                        PRIMARY KEY (id),
                        KEY ix_service_report_runs_config_id (config_id),
                        KEY ix_service_report_runs_status (status),
                        KEY ix_service_report_runs_completeness_status (completeness_status),
                        CONSTRAINT fk_service_report_runs_config
                            FOREIGN KEY (config_id) REFERENCES service_report_configs(id)
                            ON DELETE CASCADE,
                        CONSTRAINT fk_service_report_runs_source_run
                            FOREIGN KEY (source_run_id) REFERENCES service_report_source_runs(id)
                            ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
            )
        else:
            print("Table service_report_runs already exists, skipping.")

    print("service report v1 migration completed.")


if __name__ == "__main__":
    main()
