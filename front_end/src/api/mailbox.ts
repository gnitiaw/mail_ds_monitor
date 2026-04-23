import request from './request';
import type { PaginatedData, Mailbox } from './types';

export const getMailboxes = (params?: {
  status?: string;
  page?: number;
  page_size?: number;
}) => {
  return request.get<unknown, PaginatedData<Mailbox>>('/mailboxes', { params });
};

export const createMailbox = (data: Partial<Mailbox> & { password?: string, folder?: string }) => {
  return request.post<unknown, { id: string; name: string; status: string }>('/mailboxes', data);
};

export const updateMailbox = (id: string, data: Partial<Mailbox> & { password?: string, folder?: string }) => {
  return request.put<unknown, { id: string; updated_at: string }>(`/mailboxes/${id}`, data);
};

export const pullMailbox = (id: string, data: { force_full_sync: boolean }) => {
  return request.post<unknown, { job_id: string; mailbox_id: string; status: string }>(`/mailboxes/${id}/pull`, data);
};

export const processMailbox = (id: string, data?: { lookback_minutes?: number; limit?: number }) => {
  return request.post<unknown, {
    mailbox_id: string;
    archive_success_count: number;
    archive_failed_count: number;
    archive_skipped_count: number;
    failure_scanned_count: number;
    failure_matched_count: number;
    failure_deduped_count: number;
  }>(`/mailboxes/${id}/process`, data || {});
};
