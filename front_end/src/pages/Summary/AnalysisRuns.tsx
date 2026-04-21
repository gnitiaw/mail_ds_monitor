import React, { useState, useEffect, useRef } from 'react';
import { Card, Table, Tag, Button, Space, Typography, Modal, Form, DatePicker, Drawer, Checkbox } from 'antd';
import { SyncOutlined, EyeOutlined, SendOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import type { TablePaginationConfig } from 'antd';
import { summaryApi, sendSummary } from '../../api/summary';
import type { AnalysisRun, AnalysisRunDetail } from '../../api/types';
import dayjs from 'dayjs';
import { appMessage } from '../../utils/appMessage';

function getDrawerWidth() {
  if (typeof window === 'undefined') return 700;
  return Math.min(700, window.innerWidth - 48);
}

const { RangePicker } = DatePicker;

const AnalysisRuns: React.FC = () => {
  const { configId } = useParams<{ configId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<AnalysisRun[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 });

  const [createVisible, setCreateVisible] = useState(false);
  const [createForm] = Form.useForm();
  const [createLoading, setCreateLoading] = useState(false);

  const [detailVisible, setDetailVisible] = useState(false);
  const [detailData, setDetailData] = useState<AnalysisRunDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchData = async (page = pagination.current, pageSize = pagination.pageSize) => {
    if (!configId) return;
    try {
      setLoading(true);
      const res = await summaryApi.getAnalysisRuns(configId, { page, page_size: pageSize });
      setData(res.items || []);
      setTotal(res.total || 0);
      setPagination({ current: page, pageSize });
    } catch {
      //
    } finally {
      setLoading(false);
    }
  };

  const paginationRef = useRef(pagination);
  useEffect(() => {
    paginationRef.current = pagination;
  }, [pagination]);

  useEffect(() => {
    fetchData(paginationRef.current.current, paginationRef.current.pageSize);
    const interval = setInterval(() => {
      fetchData(paginationRef.current.current, paginationRef.current.pageSize);
    }, 10000); // Polling every 10s
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configId]);

  const handleTableChange = (newPagination: TablePaginationConfig) => {
    fetchData(newPagination.current, newPagination.pageSize);
  };

  const handleCreateOk = async () => {
    if (!configId) return;
    try {
      const values = await createForm.validateFields();
      setCreateLoading(true);
      await summaryApi.createAnalysisRun(configId, {
        window_start: values.timeRange[0].toISOString(),
        window_end: values.timeRange[1].toISOString(),
        force_rerun: values.force_rerun,
      });
      appMessage.success('已触发分析运行');
      setCreateVisible(false);
      fetchData(1);
    } catch {
      //
    } finally {
      setCreateLoading(false);
    }
  };

  const showDetail = async (runId: string) => {
    setDetailVisible(true);
    setDetailLoading(true);
    try {
      const res = await summaryApi.getAnalysisRunDetail(runId);
      setDetailData(res);
    } catch {
      setDetailVisible(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSend = async (runId: string) => {
    if (!configId) return;
    try {
      await sendSummary(configId, { analysis_run_id: runId });
      appMessage.success('已触发发送任务');
    } catch {
      // handled
    }
  };

  const columns = [
    { title: '运行 ID', dataIndex: 'run_id', width: 120, ellipsis: true },
    { 
      title: '状态', 
      dataIndex: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          success: 'success',
          failed: 'error',
          canceled: 'warning'
        };
        return <Tag color={colorMap[status] || 'default'} icon={status === 'running' ? <SyncOutlined spin /> : null}>{status}</Tag>;
      }
    },
    { 
      title: '时间窗口', 
      render: (_: unknown, record: AnalysisRun) => (
        `${dayjs(record.window_start).format('MM-DD HH:mm')} ~ ${dayjs(record.window_end).format('MM-DD HH:mm')}`
      )
    },
    { title: '分析模式', dataIndex: 'customer_analysis_mode', render: (val: string) => val === 'ai' ? 'AI增强' : '基础规则' },
    { title: 'AI降级', dataIndex: 'ai_fallback_used', render: (val: boolean) => val ? <Tag color="warning">已降级</Tag> : '-' },
    { title: '失败原因', dataIndex: 'error_message', ellipsis: true, render: (val: string | null) => val || '-' },
    {
      title: '操作',
      render: (_: unknown, record: AnalysisRun) => (
        <Space>
          <Button type="link" icon={<EyeOutlined />} onClick={() => showDetail(record.run_id)}>查看结果</Button>
          {record.status === 'success' && (
            <Button type="link" icon={<SendOutlined />} onClick={() => handleSend(record.run_id)}>发信</Button>
          )}
        </Space>
      )
    }
  ];

  return (
    <div className="page-container">
      <div className="back-nav-bar">
        <Space align="center">
          <Button onClick={() => navigate(-1)}>返回配置列表</Button>
          <Typography.Title level={4} style={{ margin: 0 }}>分析运行记录</Typography.Title>
        </Space>
        <Button type="primary" onClick={() => setCreateVisible(true)}>新建运行</Button>
      </div>

      <Card className="main-card">
        <Table
          columns={columns}
          dataSource={data}
          rowKey="run_id"
          pagination={{ ...pagination, total, showSizeChanger: true }}
          loading={loading}
          onChange={handleTableChange}
        />
      </Card>

      <Modal
        title="新建分析运行"
        open={createVisible}
        onOk={handleCreateOk}
        onCancel={() => setCreateVisible(false)}
        confirmLoading={createLoading}
        destroyOnHidden
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="timeRange" label="分析时间窗口" rules={[{ required: true }]}>
            <RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="force_rerun" valuePropName="checked" tooltip="开启后将忽略活动任务防重机制，强制新建跑数">
            <Checkbox>强制重新运行</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title="分析运行结果"
        width={getDrawerWidth()}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
      >
        {detailLoading ? (
          <div style={{ textAlign: 'center', padding: 50 }}>加载中...</div>
        ) : detailData ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {detailData.error_message && (
              <Card size="small" type="inner" title="错误信息" style={{ borderColor: 'var(--ant-color-error)' }}>
                <Typography.Text type="danger">{detailData.error_message}</Typography.Text>
              </Card>
            )}
            {detailData.status === 'running' && (
              <Card size="small" style={{ textAlign: 'center', padding: 24 }}>
                <SyncOutlined spin style={{ fontSize: 32, color: 'var(--matcha-600)', marginBottom: 12 }} />
                <Typography.Title level={5}>分析进行中...</Typography.Title>
                <Typography.Text type="secondary">请稍后刷新查看结果</Typography.Text>
              </Card>
            )}
            {detailData.status === 'pending' && (
              <Card size="small" style={{ textAlign: 'center', padding: 24 }}>
                <Typography.Title level={5}>等待执行</Typography.Title>
                <Typography.Text type="secondary">分析任务已排队，等待处理中</Typography.Text>
              </Card>
            )}
            {detailData.result_payload?.summary_markdown ? (
              <>
                <Card size="small" title="邮件 Markdown 预览">
                  <pre style={{ whiteSpace: 'pre-wrap', background: 'var(--oat-light)', padding: 12, borderRadius: 'var(--radius-base)' }}>
                    {String(detailData.result_payload.summary_markdown)}
                  </pre>
                </Card>
                <Card size="small" title="分析概览 (Overview)">
                  <pre style={{ whiteSpace: 'pre-wrap', background: 'var(--oat-light)', padding: 12, borderRadius: 'var(--radius-base)' }}>
                    {JSON.stringify(detailData.result_payload?.overview || {}, null, 2)}
                  </pre>
                </Card>
              </>
            ) : detailData.status === 'success' && !detailData.result_payload ? (
              <Card size="small" style={{ textAlign: 'center', padding: 24 }}>
                <Typography.Text type="secondary">分析已完成但未生成结果</Typography.Text>
              </Card>
            ) : null}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 50 }}>暂无数据</div>
        )}
      </Drawer>
    </div>
  );
};

export default AnalysisRuns;
