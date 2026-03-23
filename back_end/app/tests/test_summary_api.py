"""汇总配置接口测试。"""

import pytest
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import SummarySendStatus
from app.models.summary import SummaryConfig, SummarySendRecord


class TestSummaryConfigAPI:
    """汇总配置接口测试类。"""

    def test_create_summary_config(self, client: TestClient, db_session: Session):
        """测试创建汇总配置。"""
        payload = {
            "name": "每日汇总",
            "enabled": True,
            "schedule_type": "daily",
            "recipient_emails": ["ops@example.com"],
            "mailbox_ids": [],
            "include_statuses": ["archived"],
            "send_time": "09:00",
            "summary_mode": "ai",
            "empty_result_policy": "skip",
        }

        response = client.post("/api/v1/summary-configs", json=payload)

        assert response.status_code == 201
        json_data = response.json()
        assert json_data["code"] == 0
        data = json_data["data"]
        assert data["name"] == "每日汇总"
        assert data["enabled"] is True
        assert data["schedule_type"] == "daily"
        assert data["recipient_emails"] == ["ops@example.com"]
        assert data["send_time"] == "09:00"

    def test_create_duplicate_config(self, client: TestClient, db_session: Session):
        """测试创建重复配置 - 应返回统一错误结构。"""
        payload = {
            "name": "重复配置",
            "enabled": True,
            "recipient_emails": ["test@example.com"],
            "send_time": "10:00",
        }

        response1 = client.post("/api/v1/summary-configs", json=payload)
        assert response1.status_code == 201

        response2 = client.post("/api/v1/summary-configs", json=payload)
        assert response2.status_code == 409

        # 验证统一错误响应结构
        data = response2.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 40901
        assert "detail" not in data

    def test_list_summary_configs(self, client: TestClient, db_session: Session):
        """测试获取汇总配置列表。"""
        # 创建测试数据
        for i in range(2):
            payload = {
                "name": f"配置{i}",
                "enabled": i == 0,
                "recipient_emails": [f"user{i}@example.com"],
                "send_time": "09:00",
            }
            client.post("/api/v1/summary-configs", json=payload)

        response = client.get("/api/v1/summary-configs")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 0
        data = json_data["data"]
        assert len(data["items"]) == 2
        assert data["total"] == 2

    def test_list_summary_sends(self, client: TestClient, db_session: Session):
        """测试获取发送记录列表。"""
        # 创建配置
        config = SummaryConfig(
            name="测试配置",
            enabled=True,
            recipient_emails=["test@example.com"],
            send_time="09:00",
        )
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)

        # 创建发送记录
        send_record = SummarySendRecord(
            config_id=config.id,
            status=SummarySendStatus.SUCCESS.value,
            subject="测试汇总",
            recipient_count=1,
            window_start_date=date.today(),
            window_end_date=date.today(),
            sent_at=datetime.now(timezone.utc),
        )
        db_session.add(send_record)
        db_session.commit()

        response = client.get("/api/v1/summary-sends")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["code"] == 0
        data = json_data["data"]
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "success"
        assert data["items"][0]["subject"] == "测试汇总"
