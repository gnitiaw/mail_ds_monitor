import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Spin,
  Typography,
  Alert,
  Empty,
  Space,
} from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { getArchiveDetail } from "../../api/archive";
import type { ArchiveDetail as IArchiveDetail } from "../../api/types";

import DOMPurify from "dompurify";

const { Title, Paragraph } = Typography;

const ArchiveDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<IArchiveDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      getArchiveDetail(id)
        .then((res) => {
          setData(res);
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [id]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return <Empty description="找不到归档记录" />;
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
        return "default";
      case "parsed":
        return "processing";
      case "archived":
        return "success";
      case "failed":
        return "error";
      default:
        return "default";
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <Space align="center" size="middle">
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate(-1)}
            type="text"
            style={{ padding: 0, color: "var(--text-secondary)" }}
          >
            返回
          </Button>
          <Typography.Title
            level={4}
            style={{ margin: 0, color: "var(--text-primary)" }}
          >
            归档详情
          </Typography.Title>
        </Space>
      </div>

      <Card
        title="基础邮件信息"
        className="main-card"
        style={{ marginBottom: 16 }}
      >
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="归档 ID">
            {data.archive_id}
          </Descriptions.Item>
          <Descriptions.Item label="邮件 ID">
            {data.message_id}
          </Descriptions.Item>
          <Descriptions.Item label="所属邮箱" span={2}>
            {data.mailbox_id}
          </Descriptions.Item>
          <Descriptions.Item label="发件人">{data.sender}</Descriptions.Item>
          <Descriptions.Item label="收件人">
            {data.recipients?.join(", ")}
          </Descriptions.Item>
          <Descriptions.Item label="主题" span={2}>
            {data.subject}
          </Descriptions.Item>
          <Descriptions.Item label="接收时间">
            {data.received_at
              ? dayjs(data.received_at).format("YYYY-MM-DD HH:mm:ss")
              : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="处理状态">
            <Tag color={getStatusColor(data.status)}>{data.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="标签" span={2}>
            {data.tags?.length
              ? data.tags.map((t) => (
                  <Tag
                    key={t}
                    color="var(--light-blue-surface)"
                    style={{
                      color: "var(--primary-color)",
                      borderColor: "var(--accent-blue-border)",
                    }}
                  >
                    {t}
                  </Tag>
                ))
              : "-"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title="AI 提取结果"
        className="main-card"
        style={{ marginBottom: 16 }}
      >
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="提取状态">
            <Tag
              color={
                data.extraction_status === "success"
                  ? "success"
                  : data.extraction_status === "failed"
                    ? "error"
                    : "default"
              }
            >
              {data.extraction_status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="置信度">
            {data.confidence ?? "-"}
          </Descriptions.Item>
          <Descriptions.Item label="大模型">
            {data.model_name || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="Prompt 版本">
            {data.prompt_version || "-"}
          </Descriptions.Item>
        </Descriptions>

        <div style={{ marginTop: 16 }}>
          <Title level={5}>提取摘要</Title>
          <Paragraph style={{ color: "var(--text-secondary)" }}>
            {data.summary || "无摘要"}
          </Paragraph>
        </div>

        {data.extraction_status === "failed" && data.parse_error && (
          <Alert
            message="提取失败原因"
            description={data.parse_error}
            type="error"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        <div style={{ marginTop: 16 }}>
          <Title level={5}>结构化字段</Title>
          {data.extracted_fields &&
          Object.keys(data.extracted_fields).length > 0 ? (
            <Descriptions column={1} bordered size="small">
              {Object.entries(data.extracted_fields).map(([key, val]) => (
                <Descriptions.Item label={key} key={key}>
                  {typeof val === "object" ? JSON.stringify(val) : String(val)}
                </Descriptions.Item>
              ))}
            </Descriptions>
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="无结构化字段"
            />
          )}
        </div>
      </Card>

      <Card title="邮件原文" className="main-card">
        {data.body_html ? (
          <div
            style={{
              padding: 16,
              border: "1px solid var(--border-color)",
              borderRadius: "var(--border-radius-base)",
              background: "#fafafa",
              overflowX: "auto",
            }}
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(data.body_html),
            }}
          />
        ) : (
          <pre
            style={{
              padding: 16,
              border: "1px solid var(--border-color)",
              borderRadius: "var(--border-radius-base)",
              background: "#fafafa",
              whiteSpace: "pre-wrap",
              wordWrap: "break-word",
              color: "var(--text-secondary)",
            }}
          >
            {data.body_text || "无正文"}
          </pre>
        )}
      </Card>
    </div>
  );
};

export default ArchiveDetail;
