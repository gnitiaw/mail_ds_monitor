import request from './request';
import type { PaginatedData, Archive, ArchiveDetail } from './types';

export const getArchives = (params?: {
  mailbox_id?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}) => {
  return request.get<any, PaginatedData<Archive>>('/archives', { params });
};

export const getArchiveDetail = (id: string) => {
  return request.get<any, ArchiveDetail>(`/archives/${id}`);
};
