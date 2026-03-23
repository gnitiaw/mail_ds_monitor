import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './components/Layout';
import AuthRoute from './components/AuthRoute';
import Login from './pages/Login';
import MailboxList from './pages/Mailbox/List';
import ArchiveList from './pages/Archive/List';
import ArchiveDetail from './pages/Archive/Detail';
import SummaryConfigList from './pages/Summary/ConfigList';
import SummarySendRecords from './pages/Summary/SendRecords';
import FailureQueueList from './pages/FailureQueue/List';
import FailureQueueDetailView from './pages/FailureQueue/Detail';

const App: React.FC = () => {
  return (
    <ConfigProvider 
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1677FF',
          colorSuccess: '#31A46C',
          colorWarning: '#F5A623',
          colorError: '#E14D4D',
          colorInfo: '#1677FF',
          colorTextBase: '#16324F',
          colorTextSecondary: '#5B7594',
          colorBgBase: '#FFFFFF',
          borderRadius: 10,
          fontFamily: '"PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif',
        },
        components: {
          Card: {
            borderRadiusLG: 16,
            boxShadowTertiary: '0 10px 30px rgba(22, 50, 79, 0.06)',
            colorBorderSecondary: '#DCE9F7',
          },
          Table: {
            headerBg: '#F0F7FF',
            headerColor: '#16324F',
            rowHoverBg: '#F0F7FF',
          },
          Menu: {
            itemBg: 'transparent',
            itemColor: '#5B7594',
            itemSelectedBg: '#F0F7FF',
            itemSelectedColor: '#1677FF',
          },
          Layout: {
            siderBg: '#F7FBFF',
            headerBg: '#FFFFFF',
            bodyBg: '#F5F9FF',
          }
        }
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route path="/" element={<AuthRoute />}>
            <Route element={<MainLayout />}>
              <Route index element={<Navigate to="/failure-queue" replace />} />
              <Route path="failure-queue" element={<FailureQueueList />} />
              <Route path="failure-queue/:id" element={<FailureQueueDetailView />} />
              
              {/* Existing Routes */}
              <Route path="mailboxes" element={<MailboxList />} />
              <Route path="archives" element={<ArchiveList />} />
              <Route path="archives/:id" element={<ArchiveDetail />} />
              <Route path="summary-configs" element={<SummaryConfigList />} />
              <Route path="summary-sends" element={<SummarySendRecords />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
