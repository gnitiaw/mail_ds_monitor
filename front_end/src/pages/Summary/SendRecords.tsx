import React, { useState, useEffect } from 'react';
import { Table, Form, Select, Button, Space, Tag, Modal, Card, Typography } from 'antd';
import dayjs from 'dayjs';
import { getSummarySends } from '../../api/summary';
import { getSummaryConfigs } from '../../api/summary';
import type { SummarySendRecord, SummaryConfig } from '../../api/types';

const SendRecords: React.FC = () => {
  const [data, setData] = useState<SummarySendRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [configs, setConfigs] = useState<SummaryConfig[]>([]);

  const [form] = Form.useForm();

  useEffect(() => {
    getSummaryConfigs().then(res => {
      setConfigs(res.items || []);
    });
  }, []);

  const fetchRecords = async (p = page, ps = pageSize) => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const res = await getSummarySends({
        page: p,
        page_size: ps,
        config_id: values.config_id,
        status: values.status,
      });
      setData(res.items || []);
      setTotal(res.total || 0);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords(page, pageSize);
  }, [page, pageSize]);

  const onSearch = () => {
    setPage(1);
    fetchRecords(1, pageSize);
  };

  const onReset = () => {
    form.resetFields();
    setPage(1);
    fetchRecords(1, pageSize);
  };

  const showError = (errorMsg: string | null | undefined) => {
    if (!errorMsg) return;
    Modal.error({
      title: '失败原因',
      content: <div>{errorMsg}</div>,
    });
  };

  const columns = [
    {
      title: '发送 ID',
      dataIndex: 'send_id',
      key: 'send_id',
    },
    {
      title: '所属配置',
      dataIndex: 'config_id',
      key: 'config_id',
      render: (id: string) => configs.find(c => c.id === id)?.name || id,
    },
    {
      title: '分析运行 ID',
      dataIndex: 'analysis_run_id',
      key: 'analysis_run_id',
      render: (id: string | null) => id || '-',
    },
    {
      title: '邮件主题',
      dataIndex: 'subject',
      key: 'subject',
    },
    {
      title: '收件人数',
      dataIndex: 'recipient_count',
      key: 'recipient_count',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: SummarySendRecord) => {
        let color = 'default';
        if (status === 'success') color = 'success';
        if (status === 'failed') color = 'error';
        if (status === 'pending') color = 'processing';
        
        return (
          <Space>
            <Tag color={color}>{status}</Tag>
            {status === 'failed' && record.error_message && (
              <a onClick={() => showError(record.error_message)}>查看原因</a>
            )}
          </Space>
        );
      },
    },
    {
      title: '发送时间',
      dataIndex: 'sent_at',
      key: 'sent_at',
      render: (val: string) => val ? dayjs(val).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Typography.Title level={3} className="page-title">汇总发送记录</Typography.Title>
          <div className="page-desc">查看系统的汇总邮件发送历史与结果</div>
        </div>
      </div>

      <Card className="filter-card">
        <Form form={form} layout="inline">
          <Form.Item name="config_id" label="配置名称">
            <Select 
              style={{ width: 200 }} 
              allowClear 
              placeholder="请选择"
              options={configs.map(c => ({ label: c.name, value: c.id }))}
            />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select style={{ width: 120 }} allowClear placeholder="请选择">
              <Select.Option value="pending">处理中</Select.Option>
              <Select.Option value="success">成功</Select.Option>
              <Select.Option value="failed">失败</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" onClick={onSearch}>查询</Button>
              <Button onClick={onReset}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card className="main-card">
        <Table
          rowKey="send_id"
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

export default SendRecords;
