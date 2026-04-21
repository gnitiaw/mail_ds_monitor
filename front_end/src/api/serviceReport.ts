import axios from 'axios';
import request from './request';
import type {
  ServiceReportConfig,
  ServiceReportExportArtifact,
  ServiceReportRunDetail,
  ServiceReportRunItem,
  ServiceReportSourceRun,
  ServiceReportType,
  UserOption,
} from './types';

export interface ServiceReportConfigCreatePayload {
  name: string;
  project_name: string;
  report_type: ServiceReportType;
  period_rule: 'natural_month' | 'natural_quarter' | 'natural_year' | 'custom';
  template_key: 'ops_service_monthly_v1' | 'ops_service_quarterly_v1' | 'ops_service_annual_v1';
  project_owner_user_id: string;
  template_owner_user_id: string;
  metric_owner_user_id: string;
  enabled: boolean;
  recipient_emails: string[];
  source_bindings: Array<{
    source_type: 'inspection' | 'vulnerability' | 'worklog' | 'zentao_bug';
    ingest_mode: 'file_import';
  }>;
}

export interface CreateServiceReportSourceRunPayload {
  window_start: string;
  window_end: string;
  inspection_file: File;
  vulnerability_file: File;
  worklog_file: File;
  zentao_bug_file: File;
}

export interface CreateServiceReportRunPayload {
  window_start: string;
  window_end: string;
  source_run_id: string;
  force_regenerate?: boolean;
}

export interface ServiceReportRunsQuery {
  config_id?: string;
  report_type?: ServiceReportType;
  status?: string;
  page?: number;
  page_size?: number;
}

export const getUserOptions = () => {
  return request.get<unknown, { items: UserOption[] }>('/users/options');
};

export const getServiceReportConfigs = (params?: {
  report_type?: ServiceReportType;
  enabled?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
}) => {
  return request.get<unknown, { items: ServiceReportConfig[]; total: number; page: number; page_size: number }>(
    '/service-report-configs',
    { params },
  );
};

export const createServiceReportConfig = (payload: ServiceReportConfigCreatePayload) => {
  return request.post<unknown, ServiceReportConfig>('/service-report-configs', payload);
};

export const createServiceReportSourceRun = (configId: string, payload: CreateServiceReportSourceRunPayload) => {
  const formData = new FormData();
  formData.append('window_start', payload.window_start);
  formData.append('window_end', payload.window_end);
  formData.append('inspection_file', payload.inspection_file);
  formData.append('vulnerability_file', payload.vulnerability_file);
  formData.append('worklog_file', payload.worklog_file);
  formData.append('zentao_bug_file', payload.zentao_bug_file);

  return request.post<unknown, ServiceReportSourceRun>(
    `/service-report-configs/${configId}/source-runs`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
};

export const createServiceReportRun = (configId: string, payload: CreateServiceReportRunPayload) => {
  return request.post<unknown, {
    run_id: string;
    config_id: string;
    source_run_id: string;
    status: string;
    completeness_status: string;
    window_start: string;
    window_end: string;
    report_type: string;
    template_key: string;
    created_at: string;
  }>(`/service-report-configs/${configId}/report-runs`, payload);
};

export const getServiceReportRuns = (params?: ServiceReportRunsQuery) => {
  return request.get<unknown, { items: ServiceReportRunItem[]; total: number; page: number; page_size: number }>(
    '/service-report-runs',
    { params },
  );
};

export const getServiceReportRunDetail = (runId: string) => {
  return request.get<unknown, ServiceReportRunDetail>(`/service-report-runs/${runId}`);
};

export const updateServiceReportManualNote = (runId: string, manual_note: string | null) => {
  return request.patch<unknown, { run_id: string; manual_note: string | null }>(
    `/service-report-runs/${runId}/manual-note`,
    { manual_note },
  );
};

export const createServiceReportExport = (runId: string, format: 'markdown' | 'html', overwrite = false) => {
  return request.post<unknown, {
    run_id: string;
    format: 'markdown' | 'html';
    file_name: string;
    download_url: string;
    generated_at: string;
  }>(`/service-report-runs/${runId}/export`, { format, overwrite });
};

export const downloadServiceReportExport = async (
  runId: string,
  artifact: Pick<ServiceReportExportArtifact, 'format' | 'file_name'>,
) => {
  const token = localStorage.getItem('token');
  const response = await axios.get(`/api/v1/service-report-runs/${runId}/export`, {
    params: { format: artifact.format },
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });

  const blob = new Blob([response.data], {
    type: artifact.format === 'html' ? 'text/html;charset=utf-8' : 'text/markdown;charset=utf-8',
  });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = artifact.file_name;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};
