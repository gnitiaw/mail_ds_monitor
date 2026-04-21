import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, Form, Input, Select, Space, Table, Tag, Typography } from 'antd';
import { FileSearchOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getServiceReportConfigs, getUserOptions } from '../../api/serviceReport';
import type { ServiceReportConfig, UserOption } from '../../api/types';
import ConfigModal from './components/ConfigModal';
import UploadRunModal from './components/UploadRunModal';

const reportTypeLabel: Record<ServiceReportConfig['report_type'], string> = {
  monthly: '月报',
  quarterly: '季报',
  annual: '年报',
};

const reportTypeColor: Record<ServiceReportConfig['report_type'], string> = {
  monthly: 'blue',
  quarterly: 'gold',
  annual: 'purple',
};

const ConfigList: React.FC = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [data, setData] = useState<ServiceReportConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [configModalVisible, setConfigModalVisible] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<ServiceReportConfig | null>(null);
  const [userOptions, setUserOptions] = useState<UserOption[]>([]);

  const currentUser = useMemo(() => {
    const raw = localStorage.getItem('user');
    return raw ? (JSON.parse(raw) as { role?: string }) : null;
  }, []);

  const ownerMap = useMemo(
    () => new Map(userOptions.map((item) => [item.id, item.display_name])),
    [userOptions],
  );

  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const result = await getServiceReportConfigs({
        report_type: values.report_type || undefined,
        keyword: values.keyword || undefined,
      });
      setData(result.items || []);
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
    if (currentUser?.role === 'admin') {
      getUserOptions()
        .then((result) => setUserOptions(result.items || []))
        .catch(() => setUserOptions([]));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const columns = [
    {
      title: '配置名称',
      dataIndex: 'name',
      key: 'name',
      render: (_: string, record: ServiceReportConfig) => (
        <div>
          <div style={{ fontWeight: 600 }}>{record.name}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{record.project_name}</div>
        </div>
      ),
    },
    {
      title: '报告类型',
      dataIndex: 'report_type',
      key: 'report_type',
      render: (value: ServiceReportConfig['report_type']) => (
        <Tag color={reportTypeColor[value]}>{reportTypeLabel[value]}</Tag>
      ),
    },
    {
      title: 'Owner',
      key: 'owners',
      render: (_: string, record: ServiceReportConfig) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span>项目：{ownerMap.get(record.project_owner_user_id) ?? record.project_owner_user_id}</span>
          <span>模板：{ownerMap.get(record.template_owner_user_id) ?? record.template_owner_user_id}</span>
          <span>口径：{ownerMap.get(record.metric_owner_user_id) ?? record.metric_owner_user_id}</span>
        </div>
      ),
    },
    {
      title: '收件人',
      dataIndex: 'recipient_emails',
      key: 'recipient_emails',
      render: (emails: string[]) => emails.join(', '),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>{enabled ? '已启用' : '已停用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: string, record: ServiceReportConfig) => (
        <Space wrap>
          <Button
            type="link"
            icon={<UploadOutlined />}
            onClick={() => {
              setSelectedConfig(record);
              setUploadModalVisible(true);
            }}
          >
            上传并生成
          </Button>
          <Button
            type="link"
            icon={<FileSearchOutlined />}
            onClick={() => navigate(`/service-report-runs?config_id=${record.config_id}`)}
          >
            查看记录
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Typography.Title level={3} className="page-title">
            服务报告配置
          </Typography.Title>
          <div className="page-desc">管理报告模板责任人、收件人和运行时上传入口。</div>
        </div>
        {currentUser?.role === 'admin' && (
          <Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => setConfigModalVisible(true)}>
            新增配置
          </Button>
        )}
      </div>

      <Card className="filter-card">
        <Form form={form} layout="inline">
          <Form.Item name="keyword" label="关键词">
            <Input placeholder="配置名 / 项目名" allowClear style={{ width: 220 }} />
          </Form.Item>
          <Form.Item name="report_type" label="报告类型">
            <Select
              allowClear
              placeholder="全部"
              style={{ width: 140 }}
              options={[
                { label: '月报', value: 'monthly' },
                { label: '季报', value: 'quarterly' },
                { label: '年报', value: 'annual' },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" onClick={fetchConfigs}>查询</Button>
              <Button
                onClick={() => {
                  form.resetFields();
                  fetchConfigs();
                }}
              >
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card className="main-card">
        <Table<ServiceReportConfig>
          rowKey="config_id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={false}
        />
      </Card>

      <ConfigModal
        visible={configModalVisible}
        onCancel={() => setConfigModalVisible(false)}
        onSuccess={() => {
          setConfigModalVisible(false);
          fetchConfigs();
          if (currentUser?.role === 'admin') {
            getUserOptions()
              .then((result) => setUserOptions(result.items || []))
              .catch(() => setUserOptions([]));
          }
        }}
      />

      <UploadRunModal
        visible={uploadModalVisible}
        config={selectedConfig}
        onCancel={() => {
          setUploadModalVisible(false);
          setSelectedConfig(null);
        }}
        onSuccess={(runId) => {
          setUploadModalVisible(false);
          setSelectedConfig(null);
          navigate(`/service-report-runs/${runId}`);
        }}
      />
    </div>
  );
};

export default ConfigList;
