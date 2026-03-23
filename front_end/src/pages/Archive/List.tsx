import React, { useState, useEffect } from 'react';
import { Table, Tag, Space, Form, Input, Select, DatePicker, Button, Card, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { getArchives } from '../../api/archive';
import { getMailboxes } from '../../api/mailbox';
import type { Archive, Mailbox } from '../../api/types';

const { RangePicker } = DatePicker;

const ArchiveList: React.FC = () => {
  const [data, setData] = useState<Archive[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);

  const [form] = Form.useForm();
  const navigate = useNavigate();

  useEffect(() => {
    // 简单获取邮箱列表用于筛选
    getMailboxes({ page: 1, page_size: 100 }).then(res => {
      setMailboxes(res.items || []);
    });
  }, []);

  const fetchArchives = async (p = page, ps = pageSize) => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const params: any = {
        page: p,
        page_size: ps,
        mailbox_id: values.mailbox_id,
        status: values.status,
        keyword: values.keyword,
      };
      if (values.timeRange && values.timeRange.length === 2) {
        params.start_time = values.timeRange[0].toISOString();
        params.end_time = values.timeRange[1].toISOString();
      }

      const res = await getArchives(params);
      setData(res.items || []);
      setTotal(res.total || 0);
    } catch {
      // 错误已统一处理
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchArchives(page, pageSize);
  }, [page, pageSize]);

  const onSearch = () => {
    setPage(1);
    fetchArchives(1, pageSize);
  };

  const onReset = () => {
    form.resetFields();
    setPage(1);
    fetchArchives(1, pageSize);
  };

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'pending': return 'default';
      case 'parsed': return 'processing';
      case 'archived': return 'success';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  const columns = [
    {
      title: '主题',
      dataIndex: 'subject',
      key: 'subject',
      render: (text: string, record: Archive) => (
        <a onClick={() => navigate(`/archives/${record.archive_id}`)} style={{ color: 'var(--primary-color)', fontWeight: 500 }}>{text}</a>
      )
    },
    {
      title: '发件人',
      dataIndex: 'sender',
      key: 'sender',
    },
    {
      title: '所属邮箱',
      dataIndex: 'mailbox_id',
      key: 'mailbox_id',
      render: (id: string) => mailboxes.find(m => m.id === id)?.name || id,
    },
    {
      title: '处理状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{status}</Tag>
      )
    },
    {
      title: '提取状态',
      dataIndex: 'extraction_status',
      key: 'extraction_status',
      render: (status: string, record: Archive) => (
        <Space direction="vertical" size={0}>
          <Tag color={status === 'success' ? 'success' : status === 'failed' ? 'error' : 'default'} style={{ margin: 0 }}>
            {status}
          </Tag>
          {record.confidence ? <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>置信度: {record.confidence}</span> : null}
        </Space>
      )
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <Space size={[0, 4]} wrap>
          {tags?.map(t => <Tag key={t} color="var(--light-blue-surface)" style={{ color: 'var(--primary-color)', borderColor: 'var(--accent-blue-border)' }}>{t}</Tag>)}
        </Space>
      )
    },
    {
      title: '接收时间',
      dataIndex: 'received_at',
      key: 'received_at',
      render: (val: string) => dayjs(val).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Archive) => (
        <Button type="link" onClick={() => navigate(`/archives/${record.archive_id}`)}>详情</Button>
      )
    }
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Typography.Title level={3} className="page-title">归档列表</Typography.Title>
          <div className="page-desc">查询所有邮箱拉取并由 AI 提取结构化的归档记录</div>
        </div>
      </div>
      
      <Card className="filter-card">
        <Form form={form} layout="inline">
          <Form.Item name="mailbox_id" label="邮箱">
            <Select 
              style={{ width: 150 }} 
              allowClear 
              placeholder="全部"
              options={mailboxes.map(m => ({ label: m.name, value: m.id }))}
            />
          </Form.Item>
          <Form.Item name="status" label="处理状态">
            <Select style={{ width: 120 }} allowClear placeholder="全部">
              <Select.Option value="pending">待处理</Select.Option>
              <Select.Option value="parsed">已解析</Select.Option>
              <Select.Option value="archived">已归档</Select.Option>
              <Select.Option value="failed">失败</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="timeRange" label="接收时间">
            <RangePicker showTime />
          </Form.Item>
          <Form.Item name="keyword" label="关键词">
            <Input placeholder="搜索主题、发件人..." allowClear style={{ width: 200 }} />
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
          rowKey="archive_id"
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
            }
          }}
        />
      </Card>
    </div>
  );
};

export default ArchiveList;
