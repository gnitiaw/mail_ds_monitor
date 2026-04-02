import type { ExtractionRetryTaskResult, TaskLogDetail, TaskStatus } from '../../api/types';

export const TASK_POLL_INTERVAL_MS = 1500;

export const isTaskTerminal = (status: TaskStatus) => status === 'success' || status === 'failed';

export const buildBatchRetrySummary = (result?: ExtractionRetryTaskResult | null) => {
  if (!result) {
    return '重试任务已完成';
  }

  const parts = [`成功处理 ${result.succeeded_count} 条`];
  if (result.failed_count > 0) {
    parts.push(`失败 ${result.failed_count} 条`);
  }
  if (result.already_max_retries > 0) {
    parts.push(`达到上限 ${result.already_max_retries} 条`);
  }
  if (result.not_failed_status > 0) {
    parts.push(`状态不符 ${result.not_failed_status} 条`);
  }
  if (result.not_found > 0) {
    parts.push(`未找到 ${result.not_found} 条`);
  }
  return parts.join('，');
};

export const buildSingleRetryMessage = (task: TaskLogDetail) => {
  const detail = task.result?.details?.[0];
  if (!detail) {
    return task.status === 'failed' ? '重试任务失败' : '重试任务已完成';
  }

  if (detail.status === 'success') {
    return `重试完成，当前重试次数: ${detail.retry_count}/${detail.max_retries}`;
  }
  if (detail.status === 'max_retries_reached') {
    return `已达到最大重试次数 (${detail.max_retries} 次)`;
  }
  if (detail.status === 'not_failed_status') {
    return '邮件当前不是 failed 状态，未执行重试';
  }
  if (detail.status === 'not_found') {
    return '邮件不存在或已被删除';
  }
  return detail.error_message || task.error_message || '重试任务失败';
};
