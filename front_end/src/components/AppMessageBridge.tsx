import { App as AntdApp } from 'antd';
import { useEffect } from 'react';
import { setMessageApi } from '../utils/appMessage';

const AppMessageBridge: React.FC = () => {
  const { message } = AntdApp.useApp();

  useEffect(() => {
    setMessageApi(message);
    return () => {
      setMessageApi(null);
    };
  }, [message]);

  return null;
};

export default AppMessageBridge;
