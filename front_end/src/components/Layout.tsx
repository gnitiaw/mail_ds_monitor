import React from 'react';
import { Layout as AntLayout, Menu, Dropdown, Space, Avatar } from 'antd';
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
      type: 'group' as const,
      label: '邮件',
      children: [
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
      ],
    },
    {
      type: 'group' as const,
      label: '分析',
      children: [
        {
          key: '/failure-queue',
          icon: <WarningOutlined />,
          label: '失败邮件队列',
        },
        {
          key: '/senders',
          icon: <TeamOutlined />,
          label: '发件人管理',
        },
      ],
    },
    {
      type: 'group' as const,
      label: '汇总',
      children: [
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
      ],
    },
  ];

  const getSelectedKey = (pathname: string) => {
    if (pathname.startsWith('/archives')) return '/archives';
    if (pathname.startsWith('/mail-messages')) return '/mail-messages';
    if (pathname.startsWith('/failure-queue')) return '/failure-queue';
    if (pathname.startsWith('/senders')) return '/senders';
    if (pathname.startsWith('/summary-configs')) return '/summary-configs';
    if (pathname.startsWith('/summary-sends')) return '/summary-sends';
    return pathname;
  };

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        theme="light"
        width={220}
        style={{
          borderRight: '1px solid var(--oat-border)',
          background: 'var(--warm-cream)',
        }}
      >
        <div className="sidebar-logo">Mail Monitor</div>
        <Menu
          mode="inline"
          selectedKeys={[getSelectedKey(location.pathname)]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 'none', padding: '0 8px' }}
        />
      </Sider>
      <AntLayout>
        <Header style={{
          padding: '0 32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: 'var(--shadow-clay)',
          zIndex: 1,
          background: '#ffffff',
          borderBottom: '1px solid var(--oat-border)',
        }}>
          <span style={{
            fontSize: '15px',
            fontWeight: 500,
            color: 'var(--warm-silver)',
            letterSpacing: '-0.16px',
          }}>
            邮件监控系统
          </span>
          {user && (
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Space style={{
                cursor: 'pointer',
                padding: '6px 12px',
                borderRadius: 1584,
                border: '1px solid var(--oat-border)',
                transition: 'all 0.15s ease',
              }}>
                <Avatar
                  size={28}
                  icon={<UserOutlined />}
                  style={{ background: 'var(--matcha-600)' }}
                />
                <span style={{
                  fontSize: '14px',
                  fontWeight: 500,
                  color: 'var(--text-primary)',
                  letterSpacing: '-0.16px',
                }}>
                  {user.display_name || user.username}
                </span>
              </Space>
            </Dropdown>
          )}
        </Header>
        <Content style={{
          margin: '32px',
          minHeight: 280,
          background: 'var(--warm-cream)',
        }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default MainLayout;
