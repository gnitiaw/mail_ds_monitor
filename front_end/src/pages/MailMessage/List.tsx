import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, Select, Space, Table, Tag, Typography } from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { getMailMessages } from '../../api/mailMessage';
import { getMailboxes } from '../../api/mailbox';
import type { Mailbox, RawMailItem } from '../../api/types';

const RawMailList: React.FC = () => {
  const [data, setData] = useState<RawMailItem[]>([]);
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const navigate = useNavigate();

  useEffect(() => {
    getMailboxes({ page: 1, page_size: 100 }).then((res) => {
      setMailboxes(res.items || []);
    });
  }, []);

  useEffect(() => {
    const mailboxId = searchParams.get('mailbox_id');
    if (mailboxId) {
      form.setFieldValue('mailbox_id', mailboxId);
    }
    fetchMailMessages(1, pageSize, mailboxId || undefined);
  }, []);

  const fetchMailMessages = async (
    p = page,
    ps = pageSize,
    forcedMailboxId?: string,
  ) => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const params = {
        page: p,
        page_size: ps,
        mailbox_id: forcedMailboxId ?? values.mailbox_id,
        keyword: values.keyword,
      };
      const res = await getMailMessages(params);
      setData(res.items || []);
      setTotal(res.total || 0);
    } catch {
      // error handled in interceptor
    } finally {
      setLoading(false);
    }
  };

  const onSearch = () => {
    setPage(1);
    fetchMailMessages(1, pageSize);
  };

  const onReset = () => {
    form.resetFields();
    setPage(1);
    fetchMailMessages(1, pageSize);
  };

  const columns = [
    {
      title: '主题',
      dataIndex: 'subject',
      key: 'subject',
      render: (text: string | null, record: RawMailItem) => (
        <a onClick={() => navigate(`/mail-messages/${record.message_id}`)} style={{ color: 'var(--primary-color)', fontWeight: 500 }}>
          {text || '(无主题)'}
        </a>
      ),
    },
    {
      title: '发件人',
      dataIndex: 'sender',
      key: 'sender',
      render: (value: string | null) => value || '-',
    },
    {
      title: '所属邮箱',
      dataIndex: 'mailbox_id',
      key: 'mailbox_id',
      render: (id: string) => mailboxes.find((m) => m.id === id)?.name || id,
    },
    {
      title: '解析状态',
      dataIndex: 'parse_status',
      key: 'parse_status',
      render: (status: string) => <Tag color={status === 'parsed' ? 'success' : status === 'failed' ? 'error' : 'default'}>{status}</Tag>,
    },
    {
      title: '提取状态',
      dataIndex: 'extraction_status',
      key: 'extraction_status',
      render: (status: string) => <Tag color={status === 'success' ? 'success' : status === 'failed' ? 'error' : 'default'}>{status}</Tag>,
    },
    {
      title: '接收时间',
      dataIndex: 'received_at',
      key: 'received_at',
      render: (value: string | null) => (value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: RawMailItem) => (
        <Button type="link" onClick={() => navigate(`/mail-messages/${record.message_id}`)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Typography.Title level={3} className="page-title">原始邮件</Typography.Title>
          <div className="page-desc">直接查看已拉取入库的原始邮件，确认邮箱拉取结果。</div>
        </div>
      </div>

      <Card className="filter-card">
        <Form form={form} layout="inline">
          <Form.Item name="mailbox_id" label="邮箱">
            <Select
              style={{ width: 180 }}
              allowClear
              placeholder="全部"
              options={mailboxes.map((m) => ({ label: m.name, value: m.id }))}
            />
          </Form.Item>
          <Form.Item name="keyword" label="关键词">
            <Input placeholder="搜索主题或发件人" allowClear style={{ width: 220 }} />
          </Form.Item>
          <Form.Item style={{ marginLeft: 'auto' }}>
            <Space>
              <Button type="primary" onClick={onSearch}>查询</Button>
              <Button onClick={onReset}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card className="main-card">
        <Table
          rowKey="message_id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
              fetchMailMessages(p, ps);
            },
          }}
        />
      </Card>
    </div>
  );
};

export default RawMailList;
