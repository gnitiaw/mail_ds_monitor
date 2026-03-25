export interface BaseResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface PaginatedData<T> {
  page: number;
  page_size: number;
  total: number;
  items: T[];
}

export type MailboxStatus = 'enabled' | 'disabled';
export type MailboxProtocol = 'imap';
export type MessageProcessStatus = 'pending' | 'parsed' | 'archived' | 'failed';
export type SummaryScheduleType = 'daily';
export type SummarySendStatus = 'pending' | 'success' | 'failed';
export type ExtractionStatus = 'pending' | 'success' | 'failed';

export interface Mailbox {
  id: string;
  name: string;
  protocol: MailboxProtocol;
  host: string;
  port: number;
  username: string;
  status: MailboxStatus;
  created_at: string;
  updated_at: string;
}

export interface Archive {
  archive_id: string;
  mailbox_id: string;
  message_id: string;
  subject: string;
  sender: string;
  received_at: string;
  status: MessageProcessStatus;
  tags?: string[];
  summary?: string;
  extraction_status: ExtractionStatus;
  confidence?: number;
}

export interface ArchiveDetail extends Archive {
  recipients?: string[];
  body_text?: string;
  body_html?: string;
  extracted_fields?: Record<string, any>;
  model_name?: string;
  prompt_version?: string;
  parse_error?: string | null;
}

export interface RawMailItem {
  message_id: string;
  mailbox_id: string;
  internet_message_id?: string | null;
  provider_uid?: string | null;
  folder: string;
  subject?: string | null;
  sender?: string | null;
  received_at?: string | null;
  parse_status: MessageProcessStatus;
  extraction_status: ExtractionStatus;
  has_attachments: boolean;
  pulled_at: string;
}

export interface RawMailDetail extends RawMailItem {
  sender_name?: string | null;
  sender_email?: string | null;
  recipients_to?: string[] | null;
  recipients_cc?: string[] | null;
  recipients_bcc?: string[] | null;
  reply_to?: string[] | null;
  flags?: string[] | null;
  parse_error?: string | null;
  extraction_error?: string | null;
  body_text?: string | null;
  body_html?: string | null;
}

export interface SummaryConfig {
  id: string;
  name: string;
  enabled: boolean;
  schedule_type: SummaryScheduleType;
  recipient_emails: string[];
  mailbox_ids: string[] | null;
  send_time: string;
  summary_mode?: string;
  empty_result_policy?: string;
  include_statuses?: string[];
  // New fields
  summary_scope_mode?: 'flat' | 'customer_grouped';
  include_unidentified_senders?: boolean;
  top_n_per_customer?: number;
  customer_analysis_mode?: 'basic' | 'ai';
}

export interface SummarySendRecord {
  send_id: string;
  config_id: string;
  analysis_run_id?: string | null;
  subject: string | null;
  recipient_count: number;
  status: SummarySendStatus;
  sent_at: string | null;
  error_message?: string | null;
}

export interface SenderCandidate {
  sender_email: string;
  sender_name_sample: string | null;
  email_domain: string | null;
  message_count: number;
  archive_count: number;
  last_seen_at: string | null;
  latest_subject: string | null;
  identified_profile_id: string | null;
  identified_status: 'identified' | 'unidentified';
  customer_name: string | null;
}

export interface SenderProfile {
  profile_id: string;
  match_type: 'exact_email' | 'email_domain';
  match_value: string;
  customer_name: string;
  customer_code: string | null;
  sender_label: string | null;
  sender_type: 'customer' | 'vendor' | 'internal' | 'system' | 'unknown';
  status: 'enabled' | 'disabled';
  notes: string | null;
  last_seen_at: string | null;
  linked_message_count: number;
  created_at: string;
  updated_at: string;
}

export interface AnalysisRun {
  run_id: string;
  config_id: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'canceled';
  window_start: string;
  window_end: string;
  summary_scope_mode: 'flat' | 'customer_grouped';
  customer_analysis_mode: 'basic' | 'ai';
  ai_fallback_used: boolean;
  created_at: string;
  finished_at: string | null;
  error_message: string | null;
}

export interface AnalysisRunPayloadOverview {
  total_records?: number;
  matched_customer_count?: number;
  unidentified_record_count?: number;
  failed_record_count?: number;
  archived_record_count?: number;
  ai_fallback_used?: boolean;
}

export interface AnalysisRunPayload {
  overview?: AnalysisRunPayloadOverview;
  summary_markdown?: string;
  customers?: unknown[];
  unidentified?: Record<string, unknown>;
}

export interface AnalysisRunDetail extends AnalysisRun {
  config_snapshot: Record<string, unknown>;
  result_payload: AnalysisRunPayload | null;
  started_at: string | null;
}
