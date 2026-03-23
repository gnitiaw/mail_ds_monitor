import request from './request';
import type { PaginatedData, Mailbox } from './types';

export const getMailboxes = (params?: {
  status?: string;
  page?: number;
  page_size?: number;
}) => {
  return request.get<any, PaginatedData<Mailbox>>('/mailboxes', { params });
};

export const createMailbox = (data: Partial<Mailbox> & { password?: string, folder?: string }) => {
  return request.post<any, { id: string; name: string; status: string }>('/mailboxes', data);
};

export const updateMailbox = (id: string, data: Partial<Mailbox> & { password?: string, folder?: string }) => {
  return request.put<any, { id: string; updated_at: string }>(`/mailboxes/${id}`, data);
};

export const pullMailbox = (id: string, data: { force_full_sync: boolean }) => {
  return request.post<any, { job_id: string; mailbox_id: string; status: string }>(`/mailboxes/${id}/pull`, data);
};
