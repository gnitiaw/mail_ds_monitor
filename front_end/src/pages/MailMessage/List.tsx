import React, { useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, Form, Input, Select, Space, Table, Tag, Tooltip, Typography } from 'antd';
import { ReloadOutlined, SyncOutlined, WarningOutlined } from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { batchRetryExtraction, getMailMessages, retryExtraction } from '../../api/mailMessage';
import { getMailboxes } from '../../api/mailbox';
import { getTaskLogDetail } from '../../api/taskLog';
import type { Mailbox, RawMailItem } from '../../api/types';
import { appMessage } from '../../utils/appMessage';
import { TASK_POLL_INTERVAL_MS, buildBatchRetrySummary, buildSingleRetryMessage, isTaskTerminal } from './retryTaskUtils';

type ActiveRetryTask = {
  jobId: string;
  label: string;
  isBatch: boolean;
};

const RawMailList: React.FC = () => {
  const [data, setData] = useState<RawMailItem[]>([]);
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);
  const [loading, setLoading] = useState(false);
  const [retrySubmitting, setRetrySubmitting] = useState(false);
  const [pollingTask, setPollingTask] = useState<ActiveRetryTask | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const paginationRef = useRef({ page: 1, pageSize: 20 });

  useEffect(() => {
    paginationRef.current = { page, pageSize };
  }, [page, pageSize]);

  useEffect(() => {
    getMailboxes({ page: 1, page_size: 100 }).then((res) => {
      setMailboxes(res.items || []);
    });
  }, []);

  const fetchMailMessages = async (
    nextPage = paginationRef.current.page,
    nextPageSize = paginationRef.current.pageSize,
    forcedMailboxId?: string,
  ) => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const res = await getMailMessages({
        page: nextPage,
        page_size: nextPageSize,
        mailbox_id: forcedMailboxId ?? values.mailbox_id,
        keyword: values.keyword,
      });
      setData(res.items || []);
      setTotal(res.total || 0);
    } catch {
      //
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const mailboxId = searchParams.get('mailbox_id');
    if (mailboxId) {
      form.setFieldValue('mailbox_id', mailboxId);
    }
    fetchMailMessages(1, pageSize, mailboxId || undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!pollingTask) {
      return;
    }

    let cancelled = false;
    let timerId: number | undefined;

    const pollTask = async () => {
      try {
        const task = await getTaskLogDetail(pollingTask.jobId);
        if (cancelled) {
          return;
        }

        if (!isTaskTerminal(task.status)) {
          timerId = window.setTimeout(pollTask, TASK_POLL_INTERVAL_MS);
          return;
        }

        setPollingTask(null);
        setSelectedRowKeys([]);
        await fetchMailMessages(paginationRef.current.page, paginationRef.current.pageSize);

        if (task.status === 'failed') {
          appMessage.error(task.error_message || `${pollingTask.label}失败`);
          return;
        }

        if (pollingTask.isBatch) {
          appMessage.success(buildBatchRetrySummary(task.result));
          return;
        }

        appMessage.success(buildSingleRetryMessage(task));
      } catch {
        if (!cancelled) {
          setPollingTask(null);
          appMessage.error(`${pollingTask.label}状态查询失败`);
        }
      }
    };

    pollTask();

    return () => {
      cancelled = true;
      if (timerId) {
        window.clearTimeout(timerId);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollingTask]);

  const onSearch = () => {
    setPage(1);
    fetchMailMessages(1, pageSize);
  };

  const onReset = () => {
    form.resetFields();
    setPage(1);
    fetchMailMessages(1, pageSize);
  };

  const handleAcceptedTask = (
    jobId: string,
    options: {
      reusedExistingJob: boolean;
      isBatch: boolean;
    },
  ) => {
    const { reusedExistingJob, isBatch } = options;
    setPollingTask({
      jobId,
      label: isBatch ? '批量重试任务' : '重试任务',
      isBatch,
    });

    if (reusedExistingJob) {
      appMessage.info('已复用进行中的重试任务，页面会自动刷新结果');
      return;
    }
    appMessage.success('重试任务已受理，正在后台处理');
  };

  const handleSingleRetry = async (record: RawMailItem) => {
    try {
      setRetrySubmitting(true);
      const res = await retryExtraction(record.message_id);
      handleAcceptedTask(res.job_id, {
        reusedExistingJob: res.reused_existing_job,
        isBatch: false,
      });
    } catch {
      //
    } finally {
      setRetrySubmitting(false);
    }
  };

  const handleBatchRetry = async () => {
    if (selectedRowKeys.length === 0) {
      appMessage.warning('请选择要重试的邮件');
      return;
    }

    try {
      setRetrySubmitting(true);
      const res = await batchRetryExtraction(selectedRowKeys as string[]);
      handleAcceptedTask(res.job_id, {
        reusedExistingJob: res.reused_existing_job,
        isBatch: true,
      });
    } catch {
      //
    } finally {
      setRetrySubmitting(false);
    }
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
      render: (id: string) => mailboxes.find((mailbox) => mailbox.id === id)?.name || id,
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
      render: (status: string, record: RawMailItem) => {
        const color = status === 'success' ? 'success' : status === 'failed' ? 'error' : 'processing';
        const icon = status === 'pending' ? <SyncOutlined spin /> : status === 'failed' ? <WarningOutlined /> : undefined;
        if (status === 'failed' && record.extraction_error) {
          return (
            <Tooltip title={record.extraction_error}>
              <Tag color={color} icon={icon} style={{ cursor: 'pointer' }}>
                {status}
              </Tag>
            </Tooltip>
          );
        }
        return <Tag color={color} icon={icon}>{status}</Tag>;
      },
    },
    {
      title: '重试次数',
      dataIndex: 'retry_count',
      key: 'retry_count',
      render: (count: number, record: RawMailItem) => `${count}/${record.max_retries}`,
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
        <Space>
          <Button type="link" onClick={() => navigate(`/mail-messages/${record.message_id}`)}>
            详情
          </Button>
          {record.extraction_status === 'failed' && record.retry_count < record.max_retries && (
            <Button
              type="link"
              icon={<ReloadOutlined />}
              loading={retrySubmitting}
              disabled={Boolean(pollingTask)}
              onClick={() => handleSingleRetry(record)}
            >
              重试
            </Button>
          )}
        </Space>
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
              options={mailboxes.map((mailbox) => ({ label: mailbox.name, value: mailbox.id }))}
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

      <Card
        className="main-card"
        title={(
          <Space>
            <span>邮件列表</span>
            {selectedRowKeys.length > 0 && (
              <Button
                type="primary"
                size="small"
                icon={<ReloadOutlined />}
                loading={retrySubmitting}
                disabled={Boolean(pollingTask)}
                onClick={handleBatchRetry}
              >
                批量重试 ({selectedRowKeys.length})
              </Button>
            )}
          </Space>
        )}
      >
        {pollingTask && (
          <Alert
            showIcon
            type="info"
            style={{ marginBottom: 16 }}
            title="后台重试任务处理中"
            description="页面会自动轮询任务状态，完成后刷新列表。"
          />
        )}
        <Table
          rowKey="message_id"
          columns={columns}
          dataSource={data}
          loading={loading}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys),
            getCheckboxProps: (record: RawMailItem) => ({
              disabled: Boolean(pollingTask) || record.extraction_status !== 'failed' || record.retry_count >= record.max_retries,
            }),
          }}
          pagination={{
            current: page,
            pageSize,
            total,
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPage);
              setPageSize(nextPageSize);
              fetchMailMessages(nextPage, nextPageSize);
            },
          }}
        />
      </Card>
    </div>
  );
};

export default RawMailList;
