import React, { useState } from 'react';
import { Modal, Form, DatePicker, Typography } from 'antd';

const { RangePicker } = DatePicker;

interface SendModalProps {
  visible: boolean;
  configId: string | null;
  onCancel: () => void;
  onSend: (timeRange: [string, string]) => void;
}

const SendModal: React.FC<SendModalProps> = ({ visible, onCancel, onSend }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const start = values.timeRange[0].toISOString();
      const end = values.timeRange[1].toISOString();
      await onSend([start, end]);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="手动发送汇总邮件"
      open={visible}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      destroyOnHidden
      width={500}
    >
      <Form form={form} layout="vertical" style={{ marginTop: 24 }}>
        <Form.Item 
          name="timeRange" 
          label="汇总时间范围" 
          rules={[{ required: true, message: '请选择时间范围' }]}
        >
          <RangePicker showTime style={{ width: '100%' }} />
        </Form.Item>
        <Typography.Text type="secondary" style={{ fontSize: 13 }}>
          提示：手动发送将会按配置规则汇总所选时间段内的邮件数据。
        </Typography.Text>
      </Form>
    </Modal>
  );
};

export default SendModal;
