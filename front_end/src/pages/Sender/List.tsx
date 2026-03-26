import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Button, Space, Form, Input, Select, Modal, Tabs } from 'antd';
import type { TablePaginationConfig } from 'antd';
import { senderApi } from '../../api/sender';
import type { SenderCandidate, SenderProfile } from '../../api/types';
import dayjs from 'dayjs';
import { appMessage } from '../../utils/appMessage';

const { Option } = Select;

const SenderList: React.FC = () => {
  const [activeTab, setActiveTab] = useState('profiles');
  const [profiles, setProfiles] = useState<SenderProfile[]>([]);
  const [candidates, setCandidates] = useState<SenderCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 });
  const [total, setTotal] = useState(0);

  const [modalVisible, setModalVisible] = useState(false);
  const [modalForm] = Form.useForm();
  const [editingId, setEditingId] = useState<string | null>(null);
  
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;
  const isOperator = user?.role === 'operator';

  const fetchData = async (page = pagination.current, pageSize = pagination.pageSize) => {
    try {
      setLoading(true);
      const values = form.getFieldsValue();
      if (activeTab === 'profiles') {
        const res = await senderApi.getProfiles({ ...values, page, page_size: pageSize });
        setProfiles(res.items || []);
        setTotal(res.total || 0);
      } else {
        const res = await senderApi.getCandidates({ ...values, page, page_size: pageSize });
        setCandidates(res.items || []);
        setTotal(res.total || 0);
      }
      setPagination({ current: page, pageSize });
    } catch {
      // Error handled globally
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPagination({ current: 1, pageSize: 20 });
    form.resetFields();
    fetchData(1, 20);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const handleTableChange = (newPagination: TablePaginationConfig) => {
    fetchData(newPagination.current, newPagination.pageSize);
  };

  const handleSearch = () => fetchData(1);

  const openModal = (record?: SenderProfile) => {
    if (record) {
      setEditingId(record.profile_id);
      modalForm.setFieldsValue(record);
    } else {
      setEditingId(null);
      modalForm.resetFields();
      modalForm.setFieldsValue({ status: 'enabled', match_type: 'exact_email', sender_type: 'customer' });
    }
    setModalVisible(true);
  };

  const handleModalOk = async () => {
    try {
      const values = await modalForm.validateFields();
      if (editingId) {
        await senderApi.updateProfile(editingId, values);
        appMessage.success('更新成功');
      } else {
        await senderApi.createProfile(values);
        appMessage.success('创建成功');
      }
      setModalVisible(false);
      fetchData();
    } catch {
      //
    }
  };

  const createFromCandidate = (record: SenderCandidate) => {
    setActiveTab('profiles');
    setTimeout(() => {
      setEditingId(null);
      modalForm.resetFields();
      modalForm.setFieldsValue({
        status: 'enabled',
        match_type: 'exact_email',
        match_value: record.sender_email,
        sender_type: 'customer',
        customer_name: record.customer_name || ''
      });
      setModalVisible(true);
    }, 100);
  };

  const profileColumns = [
    { title: '匹配模式', dataIndex: 'match_type', render: (val: string) => val === 'exact_email' ? '精确邮箱' : '域名' },
    { title: '匹配值', dataIndex: 'match_value' },
    { title: '客户名称', dataIndex: 'customer_name' },
    { title: '发件人标签', dataIndex: 'sender_label', render: (val: string) => val || '-' },
    { title: '类型', dataIndex: 'sender_type' },
    { title: '状态', dataIndex: 'status', render: (val: string) => <Tag color={val === 'enabled' ? 'success' : 'error'}>{val}</Tag> },
    { title: '最近出现', dataIndex: 'last_seen_at', render: (val: string | null) => val ? dayjs(val).format('YYYY-MM-DD HH:mm') : '-' },
    {
      title: '操作',
      render: (_: unknown, record: SenderProfile) => (
        <Button type="link" onClick={() => openModal(record)} disabled={isOperator}>编辑</Button>
      )
    }
  ];

  const candidateColumns = [
    { title: '发件人邮箱', dataIndex: 'sender_email' },
    { title: '发件人名称', dataIndex: 'sender_name_sample', render: (val: string) => val || '-' },
    { title: '归档数/邮件数', render: (_: unknown, record: SenderCandidate) => `${record.archive_count} / ${record.message_count}` },
    { title: '最近主题', dataIndex: 'latest_subject', render: (val: string) => val || '-' },
    { title: '状态', dataIndex: 'identified_status', render: (val: string) => <Tag color={val === 'identified' ? 'processing' : 'warning'}>{val === 'identified' ? '已建档' : '未识别'}</Tag> },
    { title: '最近出现', dataIndex: 'last_seen_at', render: (val: string | null) => val ? dayjs(val).format('YYYY-MM-DD HH:mm') : '-' },
    {
      title: '操作',
      render: (_: unknown, record: SenderCandidate) => (
        record.identified_status !== 'identified' && !isOperator ? (
          <Button type="link" onClick={() => createFromCandidate(record)}>建档</Button>
        ) : null
      )
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <Card>
        <Form form={form} layout="inline" onFinish={handleSearch}>
          <Form.Item name="keyword" label="关键字">
            <Input placeholder="邮箱/域名/客户名称" allowClear style={{ width: 200 }} />
          </Form.Item>
          {activeTab === 'profiles' ? (
            <Form.Item name="status" label="状态">
              <Select style={{ width: 120 }} allowClear>
                <Option value="enabled">启用</Option>
                <Option value="disabled">停用</Option>
              </Select>
            </Form.Item>
          ) : (
            <Form.Item name="identified_status" label="状态">
              <Select style={{ width: 120 }} allowClear>
                <Option value="identified">已建档</Option>
                <Option value="unidentified">未识别</Option>
              </Select>
            </Form.Item>
          )}
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">搜索</Button>
              <Button onClick={() => { form.resetFields(); handleSearch(); }}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card
        title="发件人管理"
        extra={activeTab === 'profiles' && !isOperator && <Button type="primary" onClick={() => openModal()}>新建发件人</Button>}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'profiles',
              label: '已建档发件人',
              children: (
                <Table
                  columns={profileColumns}
                  dataSource={profiles}
                  rowKey="profile_id"
                  loading={loading}
                  pagination={{ ...pagination, total, showSizeChanger: true, showTotal: t => `共 ${t} 条` }}
                  onChange={handleTableChange}
                />
              ),
            },
            {
              key: 'candidates',
              label: '候选发件人',
              children: (
                <Table
                  columns={candidateColumns}
                  dataSource={candidates}
                  rowKey="sender_email"
                  loading={loading}
                  pagination={{ ...pagination, total, showSizeChanger: true, showTotal: t => `共 ${t} 条` }}
                  onChange={handleTableChange}
                />
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editingId ? '编辑发件人' : '新建发件人'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
        destroyOnHidden
      >
        <Form form={modalForm} layout="vertical">
          <Form.Item name="match_type" label="匹配模式" rules={[{ required: true }]}>
            <Select disabled={!!editingId}>
              <Option value="exact_email">精确邮箱 (exact_email)</Option>
              <Option value="email_domain">域名 (email_domain)</Option>
            </Select>
          </Form.Item>
          <Form.Item name="match_value" label="匹配值" rules={[{ required: true }]}>
            <Input disabled={!!editingId} placeholder="如 user@example.com 或 example.com" />
          </Form.Item>
          <Form.Item name="customer_name" label="归属客户名称" rules={[{ required: true }]}>
            <Input placeholder="输入客户名称" />
          </Form.Item>
          <Form.Item name="sender_label" label="发件人标签">
            <Input placeholder="例如：批量任务通知" />
          </Form.Item>
          <Form.Item name="sender_type" label="发件人类型" rules={[{ required: true }]}>
            <Select>
              <Option value="customer">Customer</Option>
              <Option value="vendor">Vendor</Option>
              <Option value="internal">Internal</Option>
              <Option value="system">System</Option>
              <Option value="unknown">Unknown</Option>
            </Select>
          </Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true }]}>
            <Select>
              <Option value="enabled">启用</Option>
              <Option value="disabled">停用</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SenderList;
