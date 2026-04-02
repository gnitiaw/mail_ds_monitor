# Eng Review：原始邮件提取失败重试

## Review 类型
- 类型：`/plan-eng-review`
- 分支：`feat/sender-management-and-analysis`
- 日期：`2026-04-01`
- 评审对象：
  - [raw-mail-extraction-retry.md](D:/Projects/codex/mail_ds_monitor/docs/features/raw-mail-extraction-retry.md)
  - [raw-mail-extraction-retry.yaml](D:/Projects/codex/mail_ds_monitor/docs/contracts/raw-mail-extraction-retry.yaml)

## 简要结论
- 这不是一个“点个按钮重跑一次”的小补丁，而是一次后台任务模型重构。
- 当前工作区里的同步版本实现只能算过渡稿，不建议按现状直接合并。
- 按本次 review 已确认决策收敛后，可以进入实现。

## 已确认决策
1. 保持现有 scope，单条和批量一起做，不缩回最小单条版本。
2. 批量重试改为异步任务，不再同步阻塞接口。
3. 复用 [task_log.py](D:/Projects/codex/mail_ds_monitor/back_end/app/models/task_log.py) ，不新建第三套任务模型。
4. 新增任务状态查询接口，前端可基于 `job_id` 轮询。
5. 单条/批量重试都要求登录，并做 mailbox scope 校验。
6. 批量重试使用稳定 `task_key` 去重，活跃任务复用已有 `job_id`。
7. 抽一个薄的后台任务骨架，避免第三套任务状态流转代码继续复制。
8. `extract_and_archive()` 不再内部 `commit()`，事务边界统一由外层任务编排控制。
9. 单条和批量统一成异步任务模型，前端交互一致。
10. “最大重试次数”由后端唯一来源下发，前端不再硬编码多个 `3`。
11. 后端测试按完整回归范围补齐，不接受只测 happy path。
12. 前端补最小测试基建，覆盖 MailMessage 列表/详情的任务状态流转。
13. worker 先批量取目标邮件，再按请求顺序处理，避免碎片化查询。
14. 执行层使用可恢复的持久化任务模型，启动时恢复或清理 stuck 任务。

## 阻塞问题
- 当前同步版本的批量重试不建议直接合并。
  - 原因：缺少异步任务、任务状态查询、鉴权收口、去重、可恢复执行层。
- 当前服务层事务边界不建议保留现状。
  - 原因：[extraction_service.py](D:/Projects/codex/mail_ds_monitor/back_end/app/services/extraction_service.py) 内部 `commit()` 会让任务日志、邮件状态、归档状态难以保持一致。
- 当前测试覆盖不足以支撑语义从“同步返回结果”切换到“异步任务受理”。
  - 原因：现有测试几乎全部绑定旧同步路径，异步、权限、去重、恢复都未覆盖。

## 非阻塞建议
- 后续可补批量重试的 `not_found` 统计项，改善前端提示完整度。
- 页面上建议显式展示“最大重试次数”规则，减少按钮消失带来的困惑。
- FastAPI `on_event` 弃用告警建议单独排期清理，但不阻塞这轮实现。

## NOT in scope
- `parse_status=failed` 的解析重试能力，单独规划，不并入本轮。
- 浏览器级 E2E 平台，本轮只补最小前端测试基建。
- 更通用的任务平台或独立 `retry_runs` 领域模型，本轮不扩张。
- 批量重试 `not_found` 统计项，本轮不是闭环所必需。

## What already exists
- 原始邮件列表/详情页已存在，可直接承载重试交互。
- `extract_and_archive()` 已存在，是提取主链路复用点。
- `TaskLog`、后台线程、异步 `pending` 语义已在邮件拉取和失败捕获中出现。
- `api.deps` 已有登录和 mailbox scope 相关依赖函数，可直接复用。

## 测试结论
- 现有后端测试只能证明“旧同步实现可用”，不能覆盖本轮最终方案。
- 目标测试范围应包含：
  - 单条/批量异步受理
  - `GET /task-logs/{job_id}` 查询
  - 登录与 mailbox scope 权限
  - `task_key` 去重复用
  - 外层事务统一提交与失败回滚
  - worker 恢复 / stuck 任务清理
  - 前端列表/详情轮询和状态刷新

## 风险结论
- 最大风险不是 LLM 本身，而是“任务被受理后没有可靠执行和可见状态”。
- 若只用临时线程、不做恢复，服务重启后用户会看到永远 `pending` 的静默失败，这是本轮必须消掉的 critical gap。

## 是否建议合并
- 对当前未收敛的同步实现：`不建议合并`
- 对按本次 review 决议收敛后的方案：`建议进入实现`

## 最终 verdict
- `DONE_WITH_CONCERNS`
- 结论：方案方向已经锁定，未决策项已清零，可以实施；但必须按本次 review 决议重构为“TaskLog 异步任务 + 状态查询 + 鉴权 + 去重 + 可恢复执行层”，不能把当前同步草稿直接当成最终版本上线。
