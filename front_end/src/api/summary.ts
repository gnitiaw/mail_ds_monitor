import request from './request';
import type { PaginatedData, SummaryConfig, SummarySendRecord } from './types';

export const getSummaryConfigs = () => {
  return request.get<any, { items: SummaryConfig[]; total: number }>('/summary-configs');
};

export const createSummaryConfig = (data: Partial<SummaryConfig> & { include_statuses?: string[], summary_mode?: string, empty_result_policy?: string }) => {
  return request.post<any, { id: string; enabled: boolean }>('/summary-configs', data);
};

export const sendSummary = (configId: string, data: { start_time: string; end_time: string }) => {
  return request.post<any, { send_id: string; status: string }>(`/summary-configs/${configId}/send`, data);
};

export const getSummarySends = (params?: {
  config_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}) => {
  return request.get<any, PaginatedData<SummarySendRecord>>('/summary-sends', { params });
};
