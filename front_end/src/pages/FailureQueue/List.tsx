import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Button, Space, Form, Input, Select, Modal } from 'antd';
import type { TablePaginationConfig } from 'antd';
import { useNavigate } from 'react-router-dom';
import { failureApi } from '../../api/failure';
import type { FailureQueueItem, FailureQueueStatus } from '../../api/failure';
import dayjs from 'dayjs';
import { appMessage } from '../../utils/appMessage';

const { Option } = Select;

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

const FailureQueueList: React.FC = () => {
  const [data, setData] = useState<FailureQueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
  });

  const [replayModalVisible, setReplayModalVisible] = useState(false);
  const [replayLoading, setReplayLoading] = useState(false);
  const [replayForm] = Form.useForm();

  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;
  const defaultMailboxIds = Array.isArray(user?.mailbox_scope_ids) ? user.mailbox_scope_ids : [];
  const isAdmin = user?.role === 'admin';

  const fetchData = async (page = pagination.current, pageSize = pagination.pageSize) => {
    try {
      setLoading(true);
      const values = form.getFieldsValue();
      const res = await failureApi.getList({
        ...values,
        page,
        page_size: pageSize,
      });
      setData(res.items);
      setTotal(res.total);
      setPagination({ current: page, pageSize });
    } catch {
      // Error handled globally
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTableChange = (newPagination: TablePaginationConfig) => {
    fetchData(newPagination.current, newPagination.pageSize);
  };

  const handleSearch = () => {
    fetchData(1);
  };

  const handleReplay = async () => {
    try {
      const values = await replayForm.validateFields();
      setReplayLoading(true);
      await failureApi.replayCapture({
        mailbox_ids: values.mailbox_ids,
        lookback_minutes: values.lookback_minutes,
      });
      appMessage.success('补跑任务已提交');
      setReplayModalVisible(false);
      fetchData(); // 刷新一下
    } catch {
      // validation error or api error
    } finally {
      setReplayLoading(false);
    }
  };

  const columns = [
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: FailureQueueStatus) => (
        <Tag color={statusColorMap[status]}>{statusTextMap[status] || status}</Tag>
      ),
    },
    {
      title: '客户名称',
      dataIndex: 'customer_name',
      key: 'customer_name',
      width: 150,
    },
    {
      title: '任务标识',
      dataIndex: 'task_identifier',
      key: 'task_identifier',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '主题',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
    },
    {
      title: '接收时间',
      dataIndex: 'received_at',
      key: 'received_at',
      width: 180,
      render: (text: string | null) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: FailureQueueItem) => (
        <Button type="link" onClick={() => navigate(`/failure-queue/${record.queue_id}`)}>
          查看
        </Button>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <Card>
        <Form form={form} layout="inline" onFinish={handleSearch}>
          <Form.Item name="status" label="状态">
            <Select style={{ width: 120 }} allowClear placeholder="全部">
              <Option value="new">待处理</Option>
              <Option value="acknowledged">处理中</Option>
              <Option value="resolved">已解决</Option>
            </Select>
          </Form.Item>
          <Form.Item name="keyword" label="关键字">
            <Input placeholder="主题/客户名/任务标识" allowClear style={{ width: 200 }} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                搜索
              </Button>
              <Button onClick={() => { form.resetFields(); handleSearch(); }}>
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card 
        title="失败邮件队列" 
        extra={<Button type="default" onClick={() => setReplayModalVisible(true)}>手动补跑</Button>}
      >
        <Table
          columns={columns}
          dataSource={data}
          rowKey="queue_id"
          pagination={{
            ...pagination,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`
          }}
          loading={loading}
          onChange={handleTableChange}
        />
      </Card>

      <Modal
        title="手动补跑失败邮件捕获"
        open={replayModalVisible}
        onOk={handleReplay}
        onCancel={() => setReplayModalVisible(false)}
        confirmLoading={replayLoading}
      >
        <Form form={replayForm} layout="vertical" initialValues={{ lookback_minutes: 120, mailbox_ids: defaultMailboxIds }}>
          <Form.Item 
            name="mailbox_ids" 
            label="邮箱 ID"
            rules={[{ required: true, message: isAdmin ? '请选择或输入邮箱 ID' : '请选择邮箱 ID' }]}
            tooltip={isAdmin ? '按回车键可输入新的邮箱ID' : '只能选择您有权限的邮箱ID'}
          >
            <Select 
              mode={isAdmin ? 'tags' : 'multiple'} 
              placeholder={isAdmin ? '选择或输入邮箱ID' : '选择邮箱ID'} 
              options={defaultMailboxIds.map((id: string) => ({ label: id, value: id }))} 
            />
          </Form.Item>
          <Form.Item 
            name="lookback_minutes" 
            label="回溯分钟数"
            rules={[{ required: true, message: '请输入回溯时间' }]}
          >
            <Input type="number" min={1} max={1440} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FailureQueueList;
