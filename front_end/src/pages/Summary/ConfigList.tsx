import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Tag, message, Card, Typography } from 'antd';
import { PlusOutlined, SendOutlined, ProfileOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getSummaryConfigs, sendSummary } from '../../api/summary';
import type { SummaryConfig } from '../../api/types';
import ConfigModal from './components/ConfigModal';
import SendModal from './components/SendModal';

const ConfigList: React.FC = () => {
  const [data, setData] = useState<SummaryConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const [configModalVisible, setConfigModalVisible] = useState(false);

  const [sendModalVisible, setSendModalVisible] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null);

  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const res = await getSummaryConfigs();
      setData(res.items || []);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
  }, []);

  const handleSend = async (configId: string, timeRange: [string, string]) => {
    try {
      await sendSummary(configId, { start_time: timeRange[0], end_time: timeRange[1] });
      message.success('已触发发送任务');
      setSendModalVisible(false);
    } catch {
      // handled
    }
  };

  const columns = [
    {
      title: '配置名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '模式',
      dataIndex: 'summary_scope_mode',
      key: 'summary_scope_mode',
      render: (mode: string) => <Tag color={mode === 'customer_grouped' ? 'purple' : 'default'}>{mode === 'customer_grouped' ? '客户归类' : '普通汇总'}</Tag>,
    },
    {
      title: '发送周期',
      dataIndex: 'schedule_type',
      key: 'schedule_type',
      render: (type: string) => <Tag color="var(--primary-color)">{type}</Tag>,
    },
    {
      title: '收件人',
      dataIndex: 'recipient_emails',
      key: 'recipient_emails',
      render: (emails: string[]) => emails?.join(', '),
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
      render: (_: unknown, record: SummaryConfig) => (
        <Space>
          {record.summary_scope_mode === 'customer_grouped' ? (
            <Button type="link" icon={<ProfileOutlined />} onClick={() => navigate(`/summary-configs/${record.id}/analysis-runs`)}>
              分析运行
            </Button>
          ) : (
            <Button type="link" icon={<SendOutlined />} onClick={() => {
              setSelectedConfig(record.id);
              setSendModalVisible(true);
            }}>手动发送</Button>
          )}
        </Space>
      ),
    }
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Typography.Title level={3} className="page-title">汇总配置</Typography.Title>
          <div className="page-desc">设置定时汇总的发送规则及收件人信息</div>
        </div>
        <Button type="primary" size="large" style={{ borderRadius: 'var(--border-radius-small)' }} icon={<PlusOutlined />} onClick={() => setConfigModalVisible(true)}>新增配置</Button>
      </div>

      <Card className="main-card">
        <Table
          rowKey="id"
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
        }}
      />

      <SendModal
        visible={sendModalVisible}
        configId={selectedConfig}
        onCancel={() => setSendModalVisible(false)}
        onSend={(timeRange) => handleSend(selectedConfig!, timeRange)}
      />
    </div>
  );
};

export default ConfigList;
