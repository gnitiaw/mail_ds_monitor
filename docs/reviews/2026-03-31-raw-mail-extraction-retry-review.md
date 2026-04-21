# Review 结论：原始邮件提取失败重试

## Review 范围
- 功能说明：[raw-mail-extraction-retry.md](D:/Projects/codex/mail_ds_monitor/docs/features/raw-mail-extraction-retry.md)
- 接口契约：[raw-mail-extraction-retry.yaml](D:/Projects/codex/mail_ds_monitor/docs/contracts/raw-mail-extraction-retry.yaml)
- 后端实现：
  - [mail_messages.py](D:/Projects/codex/mail_ds_monitor/back_end/app/api/v1/routes/mail_messages.py)
  - [task_logs.py](D:/Projects/codex/mail_ds_monitor/back_end/app/api/v1/routes/task_logs.py)
  - [extraction_retry_service.py](D:/Projects/codex/mail_ds_monitor/back_end/app/services/extraction_retry_service.py)
  - [task_log_service.py](D:/Projects/codex/mail_ds_monitor/back_end/app/services/task_log_service.py)
  - [extraction_service.py](D:/Projects/codex/mail_ds_monitor/back_end/app/services/extraction_service.py)
  - [scheduler.py](D:/Projects/codex/mail_ds_monitor/back_end/app/core/scheduler.py)
- 前端实现：
  - [mailMessage.ts](D:/Projects/codex/mail_ds_monitor/front_end/src/api/mailMessage.ts)
  - [taskLog.ts](D:/Projects/codex/mail_ds_monitor/front_end/src/api/taskLog.ts)
  - [types.ts](D:/Projects/codex/mail_ds_monitor/front_end/src/api/types.ts)
  - [List.tsx](D:/Projects/codex/mail_ds_monitor/front_end/src/pages/MailMessage/List.tsx)
  - [Detail.tsx](D:/Projects/codex/mail_ds_monitor/front_end/src/pages/MailMessage/Detail.tsx)
- 测试：
  - [test_mail_messages_api.py](D:/Projects/codex/mail_ds_monitor/back_end/app/tests/test_mail_messages_api.py)
  - [List.test.tsx](D:/Projects/codex/mail_ds_monitor/front_end/src/pages/MailMessage/List.test.tsx)
  - [Detail.test.tsx](D:/Projects/codex/mail_ds_monitor/front_end/src/pages/MailMessage/Detail.test.tsx)

## 阻塞问题
- 无。

## 非阻塞建议
- 可在后续版本把原始邮件只读接口也收口到登录用户，进一步统一权限模型。
- 当前前端采用短轮询，后续若任务量持续增长，可评估推送或更细的任务状态展示。
- 前端打包产物仍有大 chunk 告警，建议单独排期做代码分割，不阻塞本功能。
- FastAPI `on_event` 弃用告警依旧存在，建议单独清理为 lifespan 写法。

## 契约一致性检查
- 符合契约。
- 原始邮件列表和详情新增字段已对齐：`parse_error`、`extraction_error`、`retry_count`、`max_retries`、`last_retry_at`。
- 单条和批量重试都已改为 `202 Accepted + job_id` 的异步受理模型。
- `GET /api/v1/task-logs/{job_id}` 已落地，支持前端轮询。
- 单条和批量重试均要求登录，并走 mailbox scope 校验。
- 批量重试已实现 `task_key` 去重，重复提交复用已有活跃任务。

## 风险说明
- 任务结果当前依赖轮询而非推送，用户可见状态会有轻微延迟。
- APScheduler 已持久化并补启动恢复，但仍需依赖运行环境正确配置数据库 job store。
- 旧客户端若仍按同步响应解析重试接口，会与新契约不兼容。

## 测试说明
- 已执行后端：`uv run pytest app/tests/test_mail_messages_api.py -v`
- 结果：`12 passed`
- 已执行前端：`npm run test:run -- src/pages/MailMessage/List.test.tsx src/pages/MailMessage/Detail.test.tsx`
- 结果：`2 passed`
- 已执行前端构建：`npm run build`
- 结果：通过

## 是否建议合并
- 建议合并。
- 前提：
  - 运行环境已包含 `mail_messages.retry_count` 与 `mail_messages.last_retry_at`
  - 生产配置中的 APScheduler SQLAlchemyJobStore 可正常持久化任务
