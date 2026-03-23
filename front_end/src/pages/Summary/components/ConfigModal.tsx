import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Switch, TimePicker, message, Typography } from 'antd';
import { createSummaryConfig } from '../../../api/summary';
import { getMailboxes } from '../../../api/mailbox';
import type { Mailbox } from '../../../api/types';

interface ConfigModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

const ConfigModal: React.FC<ConfigModalProps> = ({ visible, onCancel, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);

  useEffect(() => {
    if (visible) {
      form.resetFields();
      form.setFieldsValue({
        enabled: true,
        schedule_type: 'daily',
        summary_mode: 'ai',
        empty_result_policy: 'skip',
        include_statuses: ['archived', 'failed'],
      });
      getMailboxes({ page: 1, page_size: 100 }).then(res => {
        setMailboxes(res.items || []);
      });
    }
  }, [visible, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      
      const payload = {
        ...values,
        send_time: values.send_time.format('HH:mm'),
        recipient_emails: values.recipient_emails.split(',').map((s: string) => s.trim()).filter(Boolean),
      };

      await createSummaryConfig(payload);
      message.success('配置创建成功');
      onSuccess();
    } catch {
      // Handled
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="新增汇总配置"
      open={visible}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      destroyOnClose
      width={600}
    >
      <Form form={form} layout="vertical">
        <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 16 }}>基础设置</Typography.Title>
        <Form.Item name="name" label="配置名称" rules={[{ required: true }]}>
          <Input placeholder="例如：每日处理汇总" />
        </Form.Item>
        <Form.Item name="enabled" label="启用状态" valuePropName="checked">
          <Switch checkedChildren="启用" unCheckedChildren="停用" />
        </Form.Item>
        
        <Typography.Title level={5} style={{ marginTop: 24, marginBottom: 16 }}>发送规则</Typography.Title>
        <div style={{ display: 'flex', gap: 16 }}>
          <Form.Item name="schedule_type" label="发送周期" rules={[{ required: true }]} style={{ flex: 1 }}>
            <Select options={[{ label: '每日', value: 'daily' }]} />
          </Form.Item>
          <Form.Item name="send_time" label="发送时间" rules={[{ required: true }]} style={{ flex: 1 }}>
            <TimePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
        </div>
        <Form.Item name="recipient_emails" label="收件人邮箱" rules={[{ required: true }]} help="多个邮箱请用英文逗号隔开">
          <Input placeholder="例如：admin@example.com, manager@example.com" />
        </Form.Item>

        <Typography.Title level={5} style={{ marginTop: 24, marginBottom: 16 }}>汇总范围与策略</Typography.Title>
        <Form.Item name="mailbox_ids" label="汇总邮箱范围" help="不选表示全部邮箱">
          <Select 
            mode="multiple"
            allowClear
            placeholder="请选择需要汇总的邮箱"
            options={mailboxes.map(m => ({ label: m.name, value: m.id }))}
          />
        </Form.Item>
        <Form.Item name="include_statuses" label="包含的状态">
          <Select 
            mode="multiple"
            options={[
              { label: '已归档', value: 'archived' },
              { label: '失败', value: 'failed' },
              { label: '待处理', value: 'pending' },
              { label: '已解析', value: 'parsed' },
            ]}
          />
        </Form.Item>
        <Form.Item name="empty_result_policy" label="无数据策略">
          <Select 
            options={[
              { label: '跳过发送', value: 'skip' },
              { label: '发送空汇总', value: 'send_empty' },
            ]}
          />
        </Form.Item>
        
        <Form.Item name="summary_mode" hidden>
          <Input />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ConfigModal;
