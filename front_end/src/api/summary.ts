import request from './request';
import type { PaginatedData, SummaryConfig, SummarySendRecord, AnalysisRun, AnalysisRunDetail } from './types';

export const getSummaryConfigs = () => {
  return request.get<unknown, { items: SummaryConfig[]; total: number }>('/summary-configs');
};

export const createSummaryConfig = (data: Partial<SummaryConfig> & { include_statuses?: string[], summary_mode?: string, empty_result_policy?: string }) => {
  return request.post<unknown, { id: string; enabled: boolean }>('/summary-configs', data);
};

export const sendSummary = (configId: string, data: { start_time?: string; end_time?: string; analysis_run_id?: string }) => {
  return request.post<unknown, { send_id: string; status: string }>(`/summary-configs/${configId}/send`, data);
};

export const getSummarySends = (params?: {
  config_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}) => {
  return request.get<unknown, PaginatedData<SummarySendRecord>>('/summary-sends', { params });
};

export const summaryApi = {
  getAnalysisRuns: (configId: string, params?: Record<string, unknown>) => {
    return request.get<unknown, PaginatedData<AnalysisRun>>(`/summary-configs/${configId}/analysis-runs`, { params });
  },

  createAnalysisRun: (configId: string, data: { window_start: string; window_end: string; force_rerun?: boolean }) => {
    return request.post<unknown, { run_id: string; status: string; reused_existing_run: boolean }>(`/summary-configs/${configId}/analysis-runs`, data);
  },

  getAnalysisRunDetail: (runId: string) => {
    return request.get<unknown, AnalysisRunDetail>(`/analysis-runs/${runId}`);
  }
};
