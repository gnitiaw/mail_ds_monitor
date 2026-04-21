import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Input,
  List,
  Row,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
  message,
} from 'antd';
import { DownloadOutlined, LeftOutlined, SaveOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useNavigate, useParams } from 'react-router-dom';
import {
  createServiceReportExport,
  downloadServiceReportExport,
  getServiceReportRunDetail,
  updateServiceReportManualNote,
} from '../../api/serviceReport';
import type { ServiceReportCompletenessStatus, ServiceReportRunDetail, ServiceReportRunSection } from '../../api/types';

const completenessMeta: Record<ServiceReportCompletenessStatus, { color: string; label: string; alertType: 'success' | 'warning' | 'error'; description: string }> = {
  ready: {
    color: 'success',
    label: '可交付',
    alertType: 'success',
    description: '当前报告已满足导出条件，可直接导出给内部或客户使用。',
  },
  partial: {
    color: 'warning',
    label: '内部复核',
    alertType: 'warning',
    description: '当前报告存在部分数据降级，允许预览与内部导出，但必须带“仅供内部复核”标识。',
  },
  blocked: {
    color: 'error',
    label: '已阻塞',
    alertType: 'error',
    description: '当前报告缺少必需数据或存在关键解析失败，禁止导出。',
  },
};

const completenessValueColor: Record<ServiceReportCompletenessStatus, string> = {
  ready: '#31A46C',
  partial: '#F5A623',
  blocked: '#E14D4D',
};

const sectionStatusColor: Record<ServiceReportRunSection['data_status'], string> = {
  ready: 'success',
  partial: 'warning',
  blocked: 'error',
};

const RunDetail: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<ServiceReportRunDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [manualNote, setManualNote] = useState('');
  const [savingNote, setSavingNote] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<'markdown' | 'html' | null>(null);

  const fetchDetail = async () => {
    if (!runId) {
      return;
    }
    setLoading(true);
    try {
      const result = await getServiceReportRunDetail(runId);
      setDetail(result);
      setManualNote(result.manual_note ?? '');
    } catch {
      setDetail(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const overviewEntries = useMemo(() => {
    if (!detail?.source_snapshot_summary?.overview) {
      return [];
    }
    return Object.entries(detail.source_snapshot_summary.overview);
  }, [detail]);

  const handleSaveManualNote = async () => {
    if (!runId) {
      return;
    }
    setSavingNote(true);
    try {
      await updateServiceReportManualNote(runId, manualNote.trim() || null);
      message.success('人工补充说明已保存');
      await fetchDetail();
    } catch {
      // 已统一处理
    } finally {
      setSavingNote(false);
    }
  };

  const handleExport = async (format: 'markdown' | 'html') => {
    if (!runId) {
      return;
    }
    setExportingFormat(format);
    try {
      const artifact = await createServiceReportExport(runId, format, true);
      await downloadServiceReportExport(runId, {
        format: artifact.format,
        file_name: artifact.file_name,
      });
      await fetchDetail();
    } catch {
      // 已统一处理
    } finally {
      setExportingFormat(null);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '96px 0' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!detail) {
    return <Empty description="未找到报告详情" />;
  }

  const completeness = completenessMeta[detail.completeness_status];
  const exportDisabled = detail.completeness_status === 'blocked';

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="page-header">
        <Space>
          <Button icon={<LeftOutlined />} onClick={() => navigate(-1)}>
            返回
          </Button>
          <div>
            <Typography.Title level={3} className="page-title">
              服务报告详情
            </Typography.Title>
            <div className="page-desc">{detail.config_snapshot.project_name} / {detail.config_snapshot.name}</div>
          </div>
        </Space>
        <Space>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleExport('markdown')}
            loading={exportingFormat === 'markdown'}
            disabled={exportDisabled}
          >
            导出 Markdown
          </Button>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={() => handleExport('html')}
            loading={exportingFormat === 'html'}
            disabled={exportDisabled}
          >
            导出 HTML
          </Button>
        </Space>
      </div>

      <Alert
        type={completeness.alertType}
        showIcon
        message={`报告完整度：${completeness.label}`}
        description={completeness.description}
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card className="main-card">
            <Statistic title="报告类型" value={detail.config_snapshot.report_type} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="main-card">
            <Statistic title="完整度" value={completeness.label} valueStyle={{ color: completenessValueColor[detail.completeness_status] }} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="main-card">
            <Statistic title="章节数" value={detail.report_payload.sections.length} />
          </Card>
        </Col>
      </Row>

      <Card className="main-card" title="报告元信息">
        <Descriptions column={{ xs: 1, md: 2 }} bordered size="small">
          <Descriptions.Item label="运行 ID">{detail.run_id}</Descriptions.Item>
          <Descriptions.Item label="source_run_id">{detail.source_run_id}</Descriptions.Item>
          <Descriptions.Item label="时间窗口">
            {dayjs(detail.window_start).format('YYYY-MM-DD HH:mm')} ~ {dayjs(detail.window_end).format('YYYY-MM-DD HH:mm')}
          </Descriptions.Item>
          <Descriptions.Item label="模板 Key">{detail.config_snapshot.template_key}</Descriptions.Item>
          <Descriptions.Item label="收件人">{detail.config_snapshot.recipient_emails.join(', ')}</Descriptions.Item>
          <Descriptions.Item label="导出产物">
            <Space wrap>
              {detail.export_artifacts.length > 0 ? detail.export_artifacts.map((item) => (
                <Tag key={`${item.format}-${item.generated_at}`}>{item.format.toUpperCase()}</Tag>
              )) : '-'}
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card className="main-card" title="报告摘要预览">
        <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'inherit', lineHeight: 1.7 }}>
          {detail.report_payload.summary_markdown}
        </pre>
      </Card>

      <Card className="main-card" title="章节内容">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {detail.report_payload.sections.map((section) => (
            <Card
              key={section.key}
              type="inner"
              title={
                <Space>
                  <span>{section.title}</span>
                  <Tag color={sectionStatusColor[section.data_status]}>{section.data_status}</Tag>
                </Space>
              }
            >
              {section.blocking_reason && (
                <Alert
                  type={section.data_status === 'blocked' ? 'error' : 'warning'}
                  showIcon
                  style={{ marginBottom: 12 }}
                  message={section.blocking_reason}
                />
              )}
              <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'inherit', lineHeight: 1.7 }}>
                {section.content_markdown}
              </pre>
            </Card>
          ))}
        </div>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <Card className="main-card" title="数据汇总概览">
            {overviewEntries.length === 0 ? (
              <Empty description="暂无汇总概览" />
            ) : (
              <Row gutter={[12, 12]}>
                {overviewEntries.map(([key, value]) => (
                  <Col xs={24} sm={12} key={key}>
                    <Card size="small" style={{ background: '#F7FBFF' }}>
                      <Typography.Text type="secondary">{key}</Typography.Text>
                      <div style={{ marginTop: 8, fontSize: 24, fontWeight: 700 }}>{String(value)}</div>
                    </Card>
                  </Col>
                ))}
              </Row>
            )}
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card className="main-card" title="数据源状态">
            <List
              dataSource={detail.source_snapshot_summary.source_results || []}
              renderItem={(item) => (
                <List.Item>
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    <Space>
                      <Typography.Text strong>{item.source_type}</Typography.Text>
                      <Tag color={item.status === 'success' ? 'success' : item.status === 'partial_success' ? 'warning' : 'error'}>
                        {item.status}
                      </Tag>
                    </Space>
                    <Typography.Text type="secondary">
                      记录 {item.record_count} / 有效 {item.valid_row_count} / 无效 {item.invalid_row_count}
                    </Typography.Text>
                    {item.error_message && <Typography.Text type="danger">{item.error_message}</Typography.Text>}
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Card className="main-card" title="人工补充说明">
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Input.TextArea
            value={manualNote}
            onChange={(event) => setManualNote(event.target.value)}
            rows={5}
            maxLength={2000}
            placeholder="补充交付口径、客户侧说明或需人工强调的重点事项。"
          />
          <Space>
            <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveManualNote} loading={savingNote}>
              保存说明
            </Button>
            <Typography.Text type="secondary">该说明不会替代自动章节，只作为报告底部补充信息。</Typography.Text>
          </Space>
        </Space>
      </Card>

      <Card className="main-card" title="证据引用">
        <List
          dataSource={detail.evidence_refs}
          locale={{ emptyText: '暂无证据引用' }}
          renderItem={(item, index) => (
            <List.Item key={`${String(item.ref_id ?? index)}-${index}`}>
              <Space direction="vertical" size={2}>
                <Typography.Text strong>{String(item.title ?? item.ref_id ?? `evidence-${index + 1}`)}</Typography.Text>
                <Typography.Text type="secondary">
                  来源：{String(item.source_type ?? '-')} / 类型：{String(item.ref_type ?? '-')}
                </Typography.Text>
                <Typography.Text>{String(item.summary ?? '-')}</Typography.Text>
              </Space>
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
};

export default RunDetail;
