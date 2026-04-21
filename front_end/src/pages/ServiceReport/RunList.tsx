import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Select, Space, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getServiceReportConfigs, getServiceReportRuns } from '../../api/serviceReport';
import type { ServiceReportConfig, ServiceReportRunItem } from '../../api/types';

const completenessColor: Record<ServiceReportRunItem['completeness_status'], string> = {
  ready: 'success',
  partial: 'warning',
  blocked: 'error',
};

const completenessLabel: Record<ServiceReportRunItem['completeness_status'], string> = {
  ready: '可交付',
  partial: '内部复核',
  blocked: '已阻塞',
};

const runStatusColor: Record<ServiceReportRunItem['status'], string> = {
  pending: 'default',
  running: 'processing',
  success: 'success',
  failed: 'error',
  canceled: 'warning',
};

const RunList: React.FC = () => {
  const [form] = Form.useForm();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [data, setData] = useState<ServiceReportRunItem[]>([]);
  const [configs, setConfigs] = useState<ServiceReportConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);

  const fetchRuns = async (nextPage = page, nextPageSize = pageSize) => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const result = await getServiceReportRuns({
        config_id: values.config_id || undefined,
        report_type: values.report_type || undefined,
        status: values.status || undefined,
        page: nextPage,
        page_size: nextPageSize,
      });
      setData(result.items || []);
      setTotal(result.total || 0);
      setPage(result.page || nextPage);
      setPageSize(result.page_size || nextPageSize);
    } catch {
      setData([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const initialConfigId = searchParams.get('config_id');
    if (initialConfigId) {
      form.setFieldsValue({ config_id: initialConfigId });
    }
    getServiceReportConfigs()
      .then((result) => setConfigs(result.items || []))
      .catch(() => setConfigs([]));
    fetchRuns(1, pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const columns = [
    {
      title: '运行信息',
      key: 'meta',
      render: (_: string, record: ServiceReportRunItem) => (
        <div>
          <div style={{ fontWeight: 600 }}>{record.config_name}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{record.project_name}</div>
        </div>
      ),
    },
    {
      title: '报告类型',
      dataIndex: 'report_type',
      key: 'report_type',
      render: (value: ServiceReportRunItem['report_type']) => {
        const labelMap = { monthly: '月报', quarterly: '季报', annual: '年报' };
        return <Tag color="blue">{labelMap[value]}</Tag>;
      },
    },
    {
      title: '执行状态',
      dataIndex: 'status',
      key: 'status',
      render: (value: ServiceReportRunItem['status']) => <Tag color={runStatusColor[value]}>{value}</Tag>,
    },
    {
      title: '完整度',
      dataIndex: 'completeness_status',
      key: 'completeness_status',
      render: (value: ServiceReportRunItem['completeness_status']) => (
        <Tag color={completenessColor[value]}>{completenessLabel[value]}</Tag>
      ),
    },
    {
      title: '时间窗口',
      key: 'window',
      render: (_: string, record: ServiceReportRunItem) => (
        <span>{dayjs(record.window_start).format('YYYY-MM-DD HH:mm')} ~ {dayjs(record.window_end).format('YYYY-MM-DD HH:mm')}</span>
      ),
    },
    {
      title: '导出格式',
      dataIndex: 'export_formats',
      key: 'export_formats',
      render: (formats: Array<'markdown' | 'html'>) => (
        <Space wrap>
          {formats.length > 0 ? formats.map((item) => <Tag key={item}>{item.toUpperCase()}</Tag>) : '-'}
        </Space>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (value: string) => dayjs(value).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: string, record: ServiceReportRunItem) => (
        <Button type="link" onClick={() => navigate(`/service-report-runs/${record.run_id}`)}>
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Typography.Title level={3} className="page-title">
            服务报告运行记录
          </Typography.Title>
          <div className="page-desc">查看报告生成状态、完整度和导出情况。</div>
        </div>
      </div>

      <Card className="filter-card">
        <Form form={form} layout="inline">
          <Form.Item name="config_id" label="配置">
            <Select
              allowClear
              showSearch
              style={{ width: 220 }}
              placeholder="全部配置"
              options={configs.map((item) => ({ label: item.name, value: item.config_id }))}
            />
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
          <Form.Item name="status" label="执行状态">
            <Select
              allowClear
              placeholder="全部"
              style={{ width: 150 }}
              options={[
                { label: 'pending', value: 'pending' },
                { label: 'running', value: 'running' },
                { label: 'success', value: 'success' },
                { label: 'failed', value: 'failed' },
                { label: 'canceled', value: 'canceled' },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" onClick={() => fetchRuns(1, pageSize)}>查询</Button>
              <Button
                onClick={() => {
                  form.resetFields();
                  fetchRuns(1, pageSize);
                }}
              >
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card className="main-card">
        <Table<ServiceReportRunItem>
          rowKey="run_id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (nextPage, nextPageSize) => {
              fetchRuns(nextPage, nextPageSize);
            },
          }}
        />
      </Card>
    </div>
  );
};

export default RunList;
