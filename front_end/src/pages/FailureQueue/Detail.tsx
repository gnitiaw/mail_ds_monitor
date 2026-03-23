import React, { useState, useEffect } from 'react';
import { Card, Descriptions, Tag, Button, Space, Typography, Spin, message, Result } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { failureApi } from '../../api/failure';
import type { FailureQueueDetail } from '../../api/failure';
import dayjs from 'dayjs';
import DOMPurify from 'dompurify';

const { Title, Text } = Typography;

const statusColorMap: Record<string, string> = {
  new: 'error',
  acknowledged: 'processing',
  resolved: 'success',
};

const statusTextMap: Record<string, string> = {
  new: '待处理',
  acknowledged: '处理中',
  resolved: '已解决',
};

const FailureQueueDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<FailureQueueDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchDetail = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(false);
      const res = await failureApi.getDetail(id);
      setData(res);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleStatusChange = async (newStatus: 'acknowledged' | 'resolved') => {
    if (!id) return;
    try {
      setActionLoading(true);
      await failureApi.updateStatus(id, newStatus);
      message.success('状态更新成功');
      fetchDetail();
    } catch {
      // Error handled by interceptor
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Result
        status="error"
        title="获取详情失败"
        subTitle="该邮件不存在或您没有权限访问，也可能是网络异常。"
        extra={[
          <Button type="primary" key="retry" onClick={fetchDetail}>重试</Button>,
          <Button key="back" onClick={() => navigate(-1)}>返回</Button>
        ]}
      />
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space align="center">
          <Button onClick={() => navigate(-1)}>返回</Button>
          <Title level={4} style={{ margin: 0 }}>失败邮件详情</Title>
          <Tag color={statusColorMap[data.status]} style={{ marginLeft: 8 }}>
            {statusTextMap[data.status] || data.status}
          </Tag>
        </Space>
        
        <Space>
          {data.status === 'new' && (
            <Button type="primary" onClick={() => handleStatusChange('acknowledged')} loading={actionLoading}>
              认领 (设为处理中)
            </Button>
          )}
          {data.status === 'acknowledged' && (
            <Button type="primary" onClick={() => handleStatusChange('resolved')} loading={actionLoading}>
              标记为已解决
            </Button>
          )}
        </Space>
      </div>

      <Card title="基本信息">
        <Descriptions column={2}>
          <Descriptions.Item label="客户名称">{data.customer_name}</Descriptions.Item>
          <Descriptions.Item label="任务标识">{data.task_identifier || '-'}</Descriptions.Item>
          <Descriptions.Item label="主题">{data.subject}</Descriptions.Item>
          <Descriptions.Item label="发件人">{data.sender}</Descriptions.Item>
          <Descriptions.Item label="接收时间">{data.received_at ? dayjs(data.received_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</Descriptions.Item>
          <Descriptions.Item label="首次捕获时间">{data.first_captured_at ? dayjs(data.first_captured_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</Descriptions.Item>
          <Descriptions.Item label="认领人">{data.acknowledged_by || '-'}</Descriptions.Item>
          <Descriptions.Item label="解决人">{data.resolved_by || '-'}</Descriptions.Item>
          <Descriptions.Item label="命中规则标识">{data.failure_rule_key}</Descriptions.Item>
          <Descriptions.Item label="邮箱ID">{data.mailbox_id}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="命中快照 (规则与提取信息)">
        <div style={{ display: 'flex', gap: '24px' }}>
          <div style={{ flex: 1 }}>
            <Text strong>匹配到的字段 (Matched Fields)</Text>
            <pre style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', marginTop: '8px' }}>
              {JSON.stringify(data.matched_snapshot?.matched_fields || {}, null, 2)}
            </pre>
          </div>
          <div style={{ flex: 1 }}>
            <Text strong>提取出的信息 (Extracted Fields)</Text>
            <pre style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', marginTop: '8px' }}>
              {JSON.stringify(data.matched_snapshot?.extracted_fields || {}, null, 2)}
            </pre>
          </div>
        </div>
      </Card>

      <Card title="邮件正文">
        {data.body_html ? (
          <div 
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(data.body_html) }} 
            style={{ border: '1px solid #f0f0f0', padding: '16px', borderRadius: '4px', minHeight: '200px' }}
          />
        ) : (
          <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word', background: '#f5f5f5', padding: '16px', borderRadius: '4px' }}>
            {data.body_text || '无正文内容'}
          </pre>
        )}
      </Card>
    </div>
  );
};

export default FailureQueueDetailView;
