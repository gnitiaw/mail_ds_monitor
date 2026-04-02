import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Detail from './Detail';

const {
  getMailMessageDetail,
  retryExtraction,
  getTaskLogDetail,
  appMessage,
} = vi.hoisted(() => ({
  getMailMessageDetail: vi.fn(),
  retryExtraction: vi.fn(),
  getTaskLogDetail: vi.fn(),
  appMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock('../../api/mailMessage', () => ({
  getMailMessageDetail,
  retryExtraction,
}));

vi.mock('../../api/taskLog', () => ({
  getTaskLogDetail,
}));

vi.mock('../../utils/appMessage', () => ({
  appMessage,
}));

vi.mock('./retryTaskUtils', () => ({
  TASK_POLL_INTERVAL_MS: 0,
  isTaskTerminal: (status: string) => status === 'success' || status === 'failed',
  buildSingleRetryMessage: () => '重试完成，当前重试次数: 1/3',
}));

describe('RawMailDetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('polls accepted retry task and refreshes detail when completed', async () => {
    getMailMessageDetail
      .mockResolvedValueOnce({
        message_id: 'msg-1',
        mailbox_id: 'mailbox-1',
        folder: 'INBOX',
        subject: 'detail failed message',
        sender_email: 'sender@example.com',
        has_attachments: false,
        parse_status: 'parsed',
        extraction_status: 'failed',
        retry_count: 0,
        max_retries: 3,
        pulled_at: '2026-04-01T10:00:00Z',
        extraction_error: 'temporary llm error',
        body_text: 'hello world',
      })
      .mockResolvedValueOnce({
        message_id: 'msg-1',
        mailbox_id: 'mailbox-1',
        folder: 'INBOX',
        subject: 'detail failed message',
        sender_email: 'sender@example.com',
        has_attachments: false,
        parse_status: 'parsed',
        extraction_status: 'success',
        retry_count: 1,
        max_retries: 3,
        pulled_at: '2026-04-01T10:00:00Z',
        extraction_error: null,
        body_text: 'hello world',
      });
    retryExtraction.mockResolvedValue({
      job_id: 'job-1',
      status: 'pending',
      reused_existing_job: false,
      requested_count: 1,
      max_retries: 3,
    });
    getTaskLogDetail
      .mockResolvedValueOnce({
        job_id: 'job-1',
        status: 'pending',
      })
      .mockResolvedValueOnce({
        job_id: 'job-1',
        status: 'success',
        result: {
          total_requested: 1,
          succeeded_count: 1,
          failed_count: 0,
          already_max_retries: 0,
          not_failed_status: 0,
          not_found: 0,
          max_retries: 3,
          details: [
            {
              message_id: 'msg-1',
              status: 'success',
              retry_count: 1,
              max_retries: 3,
            },
          ],
        },
      });

    render(
      <MemoryRouter initialEntries={['/mail-messages/msg-1']}>
        <Routes>
          <Route path="/mail-messages/:id" element={<Detail />} />
        </Routes>
      </MemoryRouter>,
    );

    const user = userEvent.setup();
    await screen.findByText('detail failed message');
    await user.click(screen.getByRole('button', { name: /重试提取/ }));

    await waitFor(() => {
      expect(retryExtraction).toHaveBeenCalledWith('msg-1');
      expect(getTaskLogDetail).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(getTaskLogDetail).toHaveBeenCalledTimes(2);
      expect(getMailMessageDetail).toHaveBeenCalledTimes(2);
    }, { timeout: 5000 });

    expect(appMessage.success).toHaveBeenCalledWith('重试任务已受理，正在后台处理');
    expect(appMessage.success).toHaveBeenCalledWith('重试完成，当前重试次数: 1/3');
  });
});
