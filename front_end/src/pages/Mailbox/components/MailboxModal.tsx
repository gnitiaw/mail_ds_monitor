import React, { useEffect, useState } from 'react';
import { Modal, Form, Input, InputNumber, Select, Switch, message, Typography } from 'antd';
import { createMailbox, updateMailbox } from '../../../api/mailbox';
import type { Mailbox } from '../../../api/types';

interface MailboxModalProps {
  visible: boolean;
  mailbox: Mailbox | null;
  onCancel: () => void;
  onSuccess: () => void;
}

const MailboxModal: React.FC<MailboxModalProps> = ({ visible, mailbox, onCancel, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      if (mailbox) {
        form.setFieldsValue({
          ...mailbox,
          status: mailbox.status === 'enabled',
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          protocol: 'imap',
          port: 993,
          status: true,
          folder: 'INBOX',
        });
      }
    }
  }, [visible, mailbox, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const payload = {
        ...values,
        status: values.status ? 'enabled' : 'disabled',
      };

      if (mailbox) {
        // Edit mode - only send fields defined in update contract
        const updatePayload: any = {
          name: values.name,
          host: values.host,
          port: values.port,
          status: values.status ? 'enabled' : 'disabled',
          folder: values.folder,
        };
        if (values.password) {
          updatePayload.password = values.password;
        }

        await updateMailbox(mailbox.id, updatePayload);
        message.success('邮箱更新成功');
      } else {
        await createMailbox(payload);
        message.success('邮箱创建成功');
      }
      onSuccess();
    } catch {
      // form validation error or api error handled in interceptor
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={mailbox ? '编辑邮箱' : '新增邮箱'}
      open={visible}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      destroyOnClose
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
      >
        <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 16 }}>基础信息</Typography.Title>
        <Form.Item
          name="name"
          label="名称"
          rules={[{ required: true, message: '请输入邮箱名称' }]}
        >
          <Input placeholder="例如：客服支持邮箱" />
        </Form.Item>
        <Form.Item
          name="username"
          label="账号"
          rules={[{ required: true, message: '请输入账号' }]}
        >
          <Input placeholder="例如：support@example.com" disabled={!!mailbox} />
        </Form.Item>
        <Form.Item
          name="password"
          label="密码/授权码"
          rules={[{ required: !mailbox, message: '请输入密码/授权码' }]}
        >
          <Input.Password placeholder={mailbox ? "留空表示不修改" : "请输入密码/授权码"} />
        </Form.Item>

        <Typography.Title level={5} style={{ marginTop: 24, marginBottom: 16 }}>服务器配置</Typography.Title>
        <div style={{ display: 'flex', gap: 16 }}>
          <Form.Item
            name="protocol"
            label="协议"
            rules={[{ required: true }]}
            style={{ flex: 1 }}
          >
            <Select disabled options={[{ label: 'IMAP', value: 'imap' }]} />
          </Form.Item>
          <Form.Item
            name="host"
            label="服务器地址"
            rules={[{ required: true, message: '请输入服务器地址' }]}
            style={{ flex: 2 }}
          >
            <Input placeholder="例如：imap.exmail.qq.com" />
          </Form.Item>
          <Form.Item
            name="port"
            label="端口"
            rules={[{ required: true, message: '请输入端口' }]}
            style={{ flex: 1 }}
          >
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
        </div>
        
        <div style={{ display: 'flex', gap: 16 }}>
          <Form.Item
            name="folder"
            label="邮箱目录"
            style={{ flex: 1 }}
          >
            <Input placeholder="默认 INBOX" />
          </Form.Item>
          <Form.Item
            name="status"
            label="状态"
            valuePropName="checked"
            style={{ flex: 1 }}
          >
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
};

export default MailboxModal;
