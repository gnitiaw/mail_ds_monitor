import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Alert, Button, Card, Descriptions, Empty, Result, Space, Spin, Tag, Typography } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import DOMPurify from 'dompurify';
import { getMailMessageDetail } from '../../api/mailMessage';
import type { RawMailDetail } from '../../api/types';

const RawMailDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<RawMailDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchDetail = async () => {
      if (!id) {
        setLoading(false);
        setError(true);
        return;
      }
      setLoading(true);
      setError(false);
      try {
        const res = await getMailMessageDetail(id);
        setData(res);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [id]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Result
        status="error"
        title="获取原始邮件失败"
        extra={[
          <Button key="retry" type="primary" onClick={() => window.location.reload()}>
            重试
          </Button>,
          <Button key="back" onClick={() => navigate('/mail-messages')}>
            返回列表
          </Button>,
        ]}
      />
    );
  }

  if (!data) {
    return <Empty description="找不到原始邮件" />;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Space align="center" size="middle">
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate(-1)}
            type="text"
            style={{ padding: 0, color: 'var(--text-secondary)' }}
          >
            返回
          </Button>
          <Typography.Title level={4} style={{ margin: 0, color: 'var(--text-primary)' }}>
            原始邮件详情
          </Typography.Title>
        </Space>
      </div>

      <Card title="基础信息" className="main-card" style={{ marginBottom: 16 }}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="邮件记录 ID">{data.message_id}</Descriptions.Item>
          <Descriptions.Item label="所属邮箱">{data.mailbox_id}</Descriptions.Item>
          <Descriptions.Item label="Message-ID">{data.internet_message_id || '-'}</Descriptions.Item>
          <Descriptions.Item label="Provider UID">{data.provider_uid || '-'}</Descriptions.Item>
          <Descriptions.Item label="文件夹">{data.folder}</Descriptions.Item>
          <Descriptions.Item label="附件">{data.has_attachments ? '有' : '无'}</Descriptions.Item>
          <Descriptions.Item label="发件人名称">{data.sender_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="发件人邮箱">{data.sender_email || '-'}</Descriptions.Item>
          <Descriptions.Item label="收件人" span={2}>{data.recipients_to?.join(', ') || '-'}</Descriptions.Item>
          <Descriptions.Item label="抄送" span={2}>{data.recipients_cc?.join(', ') || '-'}</Descriptions.Item>
          <Descriptions.Item label="主题" span={2}>{data.subject || '(无主题)'}</Descriptions.Item>
          <Descriptions.Item label="接收时间">{data.received_at ? dayjs(data.received_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</Descriptions.Item>
          <Descriptions.Item label="拉取时间">{dayjs(data.pulled_at).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
          <Descriptions.Item label="解析状态">
            <Tag color={data.parse_status === 'parsed' ? 'success' : data.parse_status === 'failed' ? 'error' : 'default'}>
              {data.parse_status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="提取状态">
            <Tag color={data.extraction_status === 'success' ? 'success' : data.extraction_status === 'failed' ? 'error' : 'default'}>
              {data.extraction_status}
            </Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {(data.parse_error || data.extraction_error) && (
        <Card className="main-card" style={{ marginBottom: 16 }}>
          {data.parse_error && (
            <Alert
              message="解析失败原因"
              description={data.parse_error}
              type="error"
              showIcon
              style={{ marginBottom: data.extraction_error ? 12 : 0 }}
            />
          )}
          {data.extraction_error && (
            <Alert
              message="提取失败原因"
              description={data.extraction_error}
              type="error"
              showIcon
            />
          )}
        </Card>
      )}

      <Card title="邮件原文" className="main-card">
        {data.body_html ? (
          <div
            style={{
              padding: 16,
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--border-radius-base)',
              background: '#fafafa',
              overflowX: 'auto',
            }}
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(data.body_html) }}
          />
        ) : (
          <pre
            style={{
              padding: 16,
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--border-radius-base)',
              background: '#fafafa',
              whiteSpace: 'pre-wrap',
              wordWrap: 'break-word',
              color: 'var(--text-secondary)',
            }}
          >
            {data.body_text || '无正文内容'}
          </pre>
        )}
      </Card>
    </div>
  );
};

export default RawMailDetailView;
