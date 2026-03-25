import React from 'react';
import { Layout as AntLayout, Menu, Typography, Dropdown, Space, Avatar } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { MailOutlined, InboxOutlined, ProfileOutlined, FileTextOutlined, WarningOutlined, UserOutlined, TeamOutlined } from '@ant-design/icons';

const { Header, Content, Sider } = AntLayout;

const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login', { replace: true });
  };

  const userMenuItems = [
    {
      key: 'logout',
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  const menuItems = [
    {
      key: '/failure-queue',
      icon: <WarningOutlined />,
      label: '失败邮件队列',
    },
    {
      key: '/mailboxes',
      icon: <MailOutlined />,
      label: '邮箱管理',
    },
    {
      key: '/mail-messages',
      icon: <InboxOutlined />,
      label: '原始邮件',
    },
    {
      key: '/archives',
      icon: <InboxOutlined />,
      label: '归档列表',
    },
    {
      key: '/senders',
      icon: <TeamOutlined />,
      label: '发件人管理',
    },
    {
      key: '/summary-configs',
      icon: <ProfileOutlined />,
      label: '汇总配置',
    },
    {
      key: '/summary-sends',
      icon: <FileTextOutlined />,
      label: '汇总记录',
    },
  ];

  const selectedKey = location.pathname.startsWith('/archives') 
    ? '/archives' 
    : location.pathname.startsWith('/mail-messages')
    ? '/mail-messages'
    : location.pathname.startsWith('/failure-queue')
    ? '/failure-queue'
    : location.pathname;

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider 
        collapsible 
        theme="light"
        width={220}
        style={{ borderRight: '1px solid var(--border-color)' }}
      >
        <div style={{ 
          height: 64, 
          margin: '16px', 
          background: 'linear-gradient(135deg, #1677FF 0%, #4096FF 100%)', 
          borderRadius: 'var(--border-radius-base)', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center', 
          color: '#fff', 
          fontWeight: 600,
          fontSize: '18px',
          boxShadow: '0 4px 12px rgba(22, 119, 255, 0.3)'
        }}>
          Mail Monitor
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 'none', padding: '0 8px' }}
        />
      </Sider>
      <AntLayout>
        <Header style={{ 
          padding: '0 24px', 
          display: 'flex', 
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 2px 8px rgba(22, 50, 79, 0.04)',
          zIndex: 1,
          background: '#fff'
        }}>
          <Typography.Title level={4} style={{ margin: 0, color: 'var(--text-primary)' }}>
            邮件监控系统
          </Typography.Title>
          {user && (
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <span>{user.display_name || user.username}</span>
              </Space>
            </Dropdown>
          )}
        </Header>
        <Content style={{ margin: '24px', minHeight: 280 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default MainLayout;
