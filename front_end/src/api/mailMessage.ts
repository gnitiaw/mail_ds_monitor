import request from './request';
import type { PaginatedData, RawMailDetail, RawMailItem } from './types';

export const getMailMessages = (params?: {
  mailbox_id?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}) => {
  return request.get<any, PaginatedData<RawMailItem>>('/mail-messages', { params });
};

export const getMailMessageDetail = (id: string) => {
  return request.get<any, RawMailDetail>(`/mail-messages/${id}`);
};
