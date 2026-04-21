import request from './request';
import type { TaskLogDetail } from './types';

export const getTaskLogDetail = (jobId: string) => {
  return request.get<any, TaskLogDetail>(`/task-logs/${jobId}`);
};
