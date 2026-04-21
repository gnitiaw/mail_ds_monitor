import React, { useState } from 'react';
import { Form, Input, Button } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../../api/auth';
import { appMessage } from '../../utils/appMessage';

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values: Record<string, string>) => {
    try {
      setLoading(true);
      const res = await authApi.login(values);
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('user', JSON.stringify(res.user));
      appMessage.success('登录成功');
      navigate('/failure-queue', { replace: true });
    } catch {
      // Error handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-icon">
            <MailOutlined style={{ fontSize: 24, color: '#ffffff' }} />
          </div>
          <h1 className="login-title">Mail Monitor</h1>
          <p className="login-subtitle">邮件监控系统登录</p>
        </div>
        <Form
          name="login"
          size="large"
          onFinish={onFinish}
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#9f9b93' }} />}
              placeholder="用户名"
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#9f9b93' }} />}
              placeholder="密码"
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, marginTop: 32 }}>
            <Button
              htmlType="submit"
              block
              loading={loading}
              className="login-submit-btn"
            >
              登录
            </Button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
};

export default Login;
