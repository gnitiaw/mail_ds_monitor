import type { MessageInstance } from 'antd/es/message/interface';

type MessageMethod = 'success' | 'error' | 'warning' | 'info';
type MessageArg = Parameters<MessageInstance['success']>[0];
type PendingCall = {
  method: MessageMethod;
  arg: MessageArg;
};

let messageApi: MessageInstance | null = null;
const pendingCalls: PendingCall[] = [];

const callMessage = (method: MessageMethod, arg: MessageArg) => {
  if (messageApi) {
    messageApi[method](arg);
    return;
  }
  pendingCalls.push({ method, arg });
};

export const setMessageApi = (nextApi: MessageInstance | null) => {
  messageApi = nextApi;
  if (!messageApi || pendingCalls.length === 0) {
    return;
  }
  pendingCalls.splice(0).forEach(({ method, arg }) => {
    messageApi?.[method](arg);
  });
};

export const appMessage = {
  success: (arg: MessageArg) => callMessage('success', arg),
  error: (arg: MessageArg) => callMessage('error', arg),
  warning: (arg: MessageArg) => callMessage('warning', arg),
  info: (arg: MessageArg) => callMessage('info', arg),
};
