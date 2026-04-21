import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Form, Input, Modal, Select, Space, Switch, Typography, message } from 'antd';
import { createServiceReportConfig, getUserOptions } from '../../../api/serviceReport';
import type { ServiceReportType, UserOption } from '../../../api/types';

interface ConfigModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

const REPORT_META: Record<ServiceReportType, { period_rule: 'natural_month' | 'natural_quarter' | 'natural_year'; template_key: 'ops_service_monthly_v1' | 'ops_service_quarterly_v1' | 'ops_service_annual_v1'; label: string }> = {
  monthly: {
    period_rule: 'natural_month',
    template_key: 'ops_service_monthly_v1',
    label: '月报',
  },
  quarterly: {
    period_rule: 'natural_quarter',
    template_key: 'ops_service_quarterly_v1',
    label: '季报',
  },
  annual: {
    period_rule: 'natural_year',
    template_key: 'ops_service_annual_v1',
    label: '年报',
  },
};

const DEFAULT_SOURCE_BINDINGS = [
  { source_type: 'inspection' as const, ingest_mode: 'file_import' as const },
  { source_type: 'vulnerability' as const, ingest_mode: 'file_import' as const },
  { source_type: 'worklog' as const, ingest_mode: 'file_import' as const },
  { source_type: 'zentao_bug' as const, ingest_mode: 'file_import' as const },
];

const ConfigModal: React.FC<ConfigModalProps> = ({ visible, onCancel, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [userOptions, setUserOptions] = useState<UserOption[]>([]);
  const reportType = Form.useWatch<ServiceReportType>('report_type', form) ?? 'monthly';

  useEffect(() => {
    if (!visible) {
      return;
    }

    form.resetFields();
    form.setFieldsValue({
      enabled: true,
      report_type: 'monthly',
      recipient_emails: 'ops@example.com',
    });

    getUserOptions()
      .then((res) => setUserOptions(res.items || []))
      .catch(() => {
        setUserOptions([]);
      });
  }, [visible, form]);

  const userSelectOptions = useMemo(
    () => userOptions.map((item) => ({ label: `${item.display_name} (${item.role})`, value: item.id })),
    [userOptions],
  );

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      const meta = REPORT_META[values.report_type as ServiceReportType];
      setLoading(true);
      await createServiceReportConfig({
        name: values.name,
        project_name: values.project_name,
        report_type: values.report_type,
        period_rule: meta.period_rule,
        template_key: meta.template_key,
        project_owner_user_id: values.project_owner_user_id,
        template_owner_user_id: values.template_owner_user_id,
        metric_owner_user_id: values.metric_owner_user_id,
        enabled: values.enabled,
        recipient_emails: String(values.recipient_emails)
          .split(/[\n,，]/)
          .map((item) => item.trim())
          .filter(Boolean),
        source_bindings: DEFAULT_SOURCE_BINDINGS,
      });
      message.success('服务报告配置创建成功');
      onSuccess();
    } catch {
      // 请求错误由统一拦截器处理
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="新增服务报告配置"
      open={visible}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      destroyOnClose
      width={720}
    >
      <Form form={form} layout="vertical">
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 20 }}
          message="V1 为单项目试点"
          description="当前只能存在一个启用中的项目名称。报告配置保存的是口径与责任人，不绑定永久数据文件。"
        />

        <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 16 }}>
          基础信息
        </Typography.Title>

        <Space style={{ display: 'flex' }} size={16} align="start">
          <Form.Item name="name" label="配置名称" rules={[{ required: true, message: '请输入配置名称' }]} style={{ flex: 1 }}>
            <Input placeholder="例如：Alpha 项目月报配置" />
          </Form.Item>
          <Form.Item name="report_type" label="报告周期" rules={[{ required: true, message: '请选择报告周期' }]} style={{ width: 180 }}>
            <Select
              options={[
                { label: '月报', value: 'monthly' },
                { label: '季报', value: 'quarterly' },
                { label: '年报', value: 'annual' },
              ]}
            />
          </Form.Item>
        </Space>

        <Space style={{ display: 'flex' }} size={16} align="start">
          <Form.Item name="project_name" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]} style={{ flex: 1 }}>
            <Input placeholder="例如：Alpha 项目" />
          </Form.Item>
          <Form.Item name="enabled" label="启用状态" valuePropName="checked" style={{ width: 180 }}>
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
        </Space>

        <Typography.Title level={5} style={{ marginBottom: 16 }}>
          Owner 责任人
        </Typography.Title>

        <Space style={{ display: 'flex' }} size={16} align="start">
          <Form.Item
            name="project_owner_user_id"
            label="项目 Owner"
            rules={[{ required: true, message: '请选择项目 Owner' }]}
            style={{ flex: 1 }}
          >
            <Select showSearch options={userSelectOptions} placeholder="请选择项目负责人" />
          </Form.Item>
          <Form.Item
            name="template_owner_user_id"
            label="模板 Owner"
            rules={[{ required: true, message: '请选择模板 Owner' }]}
            style={{ flex: 1 }}
          >
            <Select showSearch options={userSelectOptions} placeholder="请选择模板负责人" />
          </Form.Item>
          <Form.Item
            name="metric_owner_user_id"
            label="口径 Owner"
            rules={[{ required: true, message: '请选择口径 Owner' }]}
            style={{ flex: 1 }}
          >
            <Select showSearch options={userSelectOptions} placeholder="请选择口径负责人" />
          </Form.Item>
        </Space>

        <Typography.Title level={5} style={{ marginBottom: 16 }}>
          收件与模板
        </Typography.Title>

        <Form.Item
          name="recipient_emails"
          label="收件人邮箱"
          rules={[{ required: true, message: '请输入至少一个邮箱' }]}
          extra="多个邮箱可用逗号或换行分隔"
        >
          <Input.TextArea placeholder="ops@example.com, manager@example.com" rows={3} />
        </Form.Item>

        <Alert
          type="success"
          showIcon
          message={`当前选择：${REPORT_META[reportType].label}`}
          description={`将自动绑定模板 ${REPORT_META[reportType].template_key}，周期规则 ${REPORT_META[reportType].period_rule}。`}
        />
      </Form>
    </Modal>
  );
};

export default ConfigModal;
