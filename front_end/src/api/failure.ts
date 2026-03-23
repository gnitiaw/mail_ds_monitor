import request from './request';
import type { PaginatedData } from './types';

export type FailureQueueStatus = 'new' | 'acknowledged' | 'resolved';

export interface FailureQueueItem {
  queue_id: string;
  mailbox_id: string;
  source_message_id: string | null;
  failure_rule_key: string;
  customer_name: string;
  task_identifier: string | null;
  subject: string;
  sender: string;
  received_at: string | null;
  status: FailureQueueStatus;
  first_captured_at: string;
  last_seen_at: string;
}

export interface FailureQueueDetail extends FailureQueueItem {
  provider_uid: string | null;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  body_text: string | null;
  body_html: string | null;
  matched_snapshot: {
    matched_fields: Record<string, unknown>;
    extracted_fields: Record<string, unknown>;
  } | null;
}

export interface GetFailureQueueParams {
  status?: FailureQueueStatus;
  mailbox_id?: string;
  keyword?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}

export interface CaptureReplayParams {
  mailbox_ids: string[];
  lookback_minutes: number;
}

export interface CaptureReplayResponse {
  run_id: string;
  status: string;
  mailbox_ids: string[];
}

export const failureApi = {
  getList: (params: GetFailureQueueParams) => {
    return request.get<unknown, PaginatedData<FailureQueueItem>>('/failure-queue', { params });
  },
  
  getDetail: (queue_id: string) => {
    return request.get<unknown, FailureQueueDetail>(`/failure-queue/${queue_id}`);
  },
  
  updateStatus: (queue_id: string, status: FailureQueueStatus) => {
    return request.patch<unknown, {
      queue_id: string;
      status: FailureQueueStatus;
      acknowledged_at: string | null;
      acknowledged_by: string | null;
      resolved_at: string | null;
      resolved_by: string | null;
      updated_at: string;
    }>(`/failure-queue/${queue_id}/status`, { status });
  },
  
  replayCapture: (data: CaptureReplayParams) => {
    return request.post<unknown, CaptureReplayResponse>('/failure-capture-runs/replay', data);
  }
};
