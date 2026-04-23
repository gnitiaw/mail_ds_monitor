import request from './request';
import type {
  PaginatedData,
  RawMailDetail,
  RawMailItem,
  TaskLogAcceptedResponse,
} from './types';

export const getMailMessages = (params?: {
  mailbox_id?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}) => {
  return request.get<unknown, PaginatedData<RawMailItem>>('/mail-messages', { params });
};

export const getMailMessageDetail = (id: string) => {
  return request.get<unknown, RawMailDetail>(`/mail-messages/${id}`);
};

export const retryExtraction = (messageId: string) => {
  return request.post<unknown, TaskLogAcceptedResponse>(`/mail-messages/${messageId}/retry-extraction`);
};

export const batchRetryExtraction = (messageIds: string[]) => {
  return request.post<unknown, TaskLogAcceptedResponse>('/mail-messages/batch-retry-extraction', {
    message_ids: messageIds,
  });
};
