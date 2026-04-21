import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { App as AntdApp, ConfigProvider, Empty } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './components/Layout';
import AppMessageBridge from './components/AppMessageBridge';
import AuthRoute from './components/AuthRoute';
import Login from './pages/Login';
import MailboxList from './pages/Mailbox/List';
import ArchiveList from './pages/Archive/List';
import ArchiveDetail from './pages/Archive/Detail';
import RawMailList from './pages/MailMessage/List';
import RawMailDetailView from './pages/MailMessage/Detail';
import SummaryConfigList from './pages/Summary/ConfigList';
import SummarySendRecords from './pages/Summary/SendRecords';
import AnalysisRuns from './pages/Summary/AnalysisRuns';
import FailureQueueList from './pages/FailureQueue/List';
import FailureQueueDetailView from './pages/FailureQueue/Detail';
import SenderList from './pages/Sender/List';
import ServiceReportConfigList from './pages/ServiceReport/ConfigList';
import ServiceReportRunList from './pages/ServiceReport/RunList';
import ServiceReportRunDetail from './pages/ServiceReport/RunDetail';

const App: React.FC = () => {
  return (
    <ConfigProvider
      locale={zhCN}
      renderEmpty={() => <Empty description="暂无数据" />}
      theme={{
        token: {
          colorPrimary: '#078a52',
          colorSuccess: '#078a52',
          colorWarning: '#fbbd41',
          colorError: '#fc7981',
          colorInfo: '#3bd3fd',
          colorTextBase: '#000000',
          colorTextSecondary: '#9f9b93',
          colorBgBase: '#ffffff',
          borderRadius: 12,
          fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          colorBorder: '#dad4c8',
          colorBorderSecondary: '#eee9df',
          colorBgLayout: '#faf9f7',
          colorBgContainer: '#ffffff',
        },
        components: {
          Card: {
            borderRadiusLG: 24,
            boxShadowTertiary: 'rgba(0,0,0,0.1) 0px 1px 1px, rgba(0,0,0,0.04) 0px -1px 1px inset, rgba(0,0,0,0.05) 0px -0.5px 1px',
            colorBorderSecondary: '#dad4c8',
          },
          Table: {
            headerBg: '#eee9df',
            headerColor: '#000000',
            rowHoverBg: '#faf9f7',
            colorBorderSecondary: '#eee9df',
          },
          Menu: {
            itemBg: 'transparent',
            itemColor: '#55534e',
            itemSelectedBg: '#eee9df',
            itemSelectedColor: '#078a52',
            itemHoverColor: '#078a52',
          },
          Layout: {
            siderBg: '#faf9f7',
            headerBg: '#ffffff',
            bodyBg: '#faf9f7',
          },
          Button: {
            borderRadius: 1584,
            fontWeight: 500,
          },
          Tag: {
            borderRadiusSM: 1584,
          },
          Modal: {
            borderRadiusLG: 24,
          },
          Input: {
            borderRadius: 4,
            colorBorder: '#dad4c8',
            activeBorderColor: '#078a52',
            hoverBorderColor: '#9f9b93',
          },
          Select: {
            colorBorder: '#dad4c8',
            colorBorderSecondary: '#dad4c8',
            activeBorderColor: '#078a52',
            optionSelectedBg: '#eee9df',
          },
          Tabs: {
            inkBarColor: '#078a52',
            itemSelectedColor: '#078a52',
          },
        }
      }}
    >
      <AntdApp>
        <AppMessageBridge />
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            
            <Route path="/" element={<AuthRoute />}>
              <Route element={<MainLayout />}>
                <Route index element={<Navigate to="/failure-queue" replace />} />
                <Route path="failure-queue" element={<FailureQueueList />} />
                <Route path="failure-queue/:id" element={<FailureQueueDetailView />} />
                <Route path="mail-messages" element={<RawMailList />} />
                <Route path="mail-messages/:id" element={<RawMailDetailView />} />
                
                {/* Existing Routes */}
                <Route path="mailboxes" element={<MailboxList />} />
                <Route path="archives" element={<ArchiveList />} />
                <Route path="archives/:id" element={<ArchiveDetail />} />
                <Route path="senders" element={<SenderList />} />
                <Route path="summary-configs" element={<SummaryConfigList />} />
                <Route path="summary-configs/:configId/analysis-runs" element={<AnalysisRuns />} />
                <Route path="summary-sends" element={<SummarySendRecords />} />
                <Route path="service-report-configs" element={<ServiceReportConfigList />} />
                <Route path="service-report-runs" element={<ServiceReportRunList />} />
                <Route path="service-report-runs/:runId" element={<ServiceReportRunDetail />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
};

export default App;
