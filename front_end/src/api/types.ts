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

export interface SummaryConfig {
  id: string;
  name: string;
  enabled: boolean;
  schedule_type: SummaryScheduleType;
  recipient_emails: string[];
  mailbox_ids: string[];
  send_time: string;
}

export interface SummarySendRecord {
  send_id: string;
  config_id: string;
  subject: string;
  recipient_count: number;
  status: SummarySendStatus;
  sent_at: string;
  error_message?: string | null;
}
