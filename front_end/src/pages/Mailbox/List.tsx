import React, { useState, useEffect } from 'react';
import { Table, Button, Tag, Card, Typography, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import { PlusOutlined, SyncOutlined, EditOutlined, InboxOutlined, MoreOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { getMailboxes, processMailbox, pullMailbox } from '../../api/mailbox';
import type { Mailbox } from '../../api/types';
import MailboxModal from './components/MailboxModal';
import { appMessage } from '../../utils/appMessage';

const MailboxList: React.FC = () => {
  const [data, setData] = useState<Mailbox[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  
  const [modalVisible, setModalVisible] = useState(false);
  const [editingMailbox, setEditingMailbox] = useState<Mailbox | null>(null);
  const navigate = useNavigate();

  const fetchMailboxes = async (p = page, ps = pageSize) => {
    setLoading(true);
    try {
      const res = await getMailboxes({ page: p, page_size: ps });
      setData(res.items || []);
      setTotal(res.total || 0);
    } catch {
      // error handled in interceptor
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMailboxes();
    // fetchMailboxes uses current pagination state and is intentionally triggered by page changes only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize]);

  const handlePull = async (id: string) => {
    try {
      await pullMailbox(id, { force_full_sync: false });
      appMessage.success('已触发拉取任务');
    } catch {
      // error handled in interceptor
    }
  };

  const handleProcess = async (id: string) => {
    try {
      const res = await processMailbox(id, { lookback_minutes: 1440, limit: 50 });
      appMessage.success(`处理完成：归档 ${res.archive_success_count} 封，失败命中 ${res.failure_matched_count} 封`);
    } catch {
      // error handled in interceptor
    }
  };

  const buildMoreMenuItems = (record: Mailbox): MenuProps['items'] => [
    {
      key: 'pull',
      icon: <SyncOutlined />,
      label: '拉取邮件',
      disabled: record.status !== 'enabled',
      onClick: () => handlePull(record.id),
    },
    {
      key: 'process',
      icon: <PlayCircleOutlined />,
      label: '处理已拉取邮件',
      disabled: record.status !== 'enabled',
      onClick: () => handleProcess(record.id),
    },
    {
      key: 'edit',
      icon: <EditOutlined />,
      label: '编辑邮箱',
      onClick: () => {
        setEditingMailbox(record);
        setModalVisible(true);
      },
    },
    {
      key: 'messages',
      icon: <InboxOutlined />,
      label: '查看原始邮件',
      onClick: () => navigate(`/mail-messages?mailbox_id=${record.id}`),
    },
  ];

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '账号',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '协议',
      dataIndex: 'protocol',
      key: 'protocol',
      render: (text: string) => <Tag color="blue">{text?.toUpperCase()}</Tag>,
    },
    {
      title: '服务器',
      key: 'server',
      render: (_: unknown, record: Mailbox) => `${record.host}:${record.port}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'enabled' ? 'success' : 'default'}>
          {status === 'enabled' ? '已启用' : '已停用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val: string) => dayjs(val).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      align: 'center' as const,
      render: (_: unknown, record: Mailbox) => (
        <Dropdown menu={{ items: buildMoreMenuItems(record) }} trigger={['click']} placement="bottomRight">
          <Button type="link" icon={<MoreOutlined />}>
            操作
          </Button>
        </Dropdown>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <Typography.Title level={3} className="page-title">邮箱管理</Typography.Title>
          <div className="page-desc">管理和配置需要监控拉取的企业或个人邮箱</div>
        </div>
        <Button type="primary" size="large" style={{ borderRadius: 'var(--border-radius-small)' }} icon={<PlusOutlined />} onClick={() => {
          setEditingMailbox(null);
          setModalVisible(true);
        }}>
          新增邮箱
        </Button>
      </div>

      <Card className="main-card">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            }
          }}
        />
      </Card>
      
      <MailboxModal
        visible={modalVisible}
        mailbox={editingMailbox}
        onCancel={() => setModalVisible(false)}
        onSuccess={() => {
          setModalVisible(false);
          fetchMailboxes();
        }}
      />
    </div>
  );
};

export default MailboxList;
