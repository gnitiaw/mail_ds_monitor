"""时间字段工具。"""

from __future__ import annotations

from datetime import datetime, timezone


def assume_utc(dt: datetime | None) -> datetime | None:
    """将 naive datetime 解释为 UTC。"""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
