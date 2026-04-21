# 巡检与运维服务报告 V1 工程评审

日期：2026-04-17

## 状态更新
以下 4 个阻塞项已于本轮收口修复：
- ORM 模型已对齐现网 MySQL `utf8mb4_unicode_ci`
- `source-runs` 契约已改为 `multipart/form-data + 4 个必传文件`
- V1 权限文档已收敛为 `admin / operator`
- 详情契约中的 `sections` 已改为通用数组结构

## 阻塞问题
1. [service_report.py](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/back_end/app/models/service_report.py:28) 里的外键列定义没有对齐现网 `users.id` 的字符集/排序规则，`DB_AUTO_CREATE_TABLES=true` 或任何依赖 ORM 直接建表的环境仍会失败。我们已经在迁移脚本里补了 `utf8mb4_unicode_ci`，但模型本身没有同步这层约束，所以“脚本能建，自动建表不能建”会长期埋雷。

2. [service-report-auto-generation.yaml](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/docs/contracts/service-report-auto-generation.yaml:223) 仍把 `POST /service-report-configs/{config_id}/source-runs` 定义成 JSON 请求体，字段是 `force_refresh` 和 `included_sources`；实际实现在 [service_reports.py](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/back_end/app/api/v1/routes/service_reports.py:167) 已经改成 `multipart/form-data + 4 个必传文件`。这不是小偏差，是客户端接入会直接失败的契约漂移。

3. 契约和功能说明都把只读角色写成 `viewer`，比如 [service-report-auto-generation.yaml](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/docs/contracts/service-report-auto-generation.yaml:75) 和 [service-report-auto-generation.md](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/docs/features/service-report-auto-generation.md:113)，但实际权限实现只有 `admin_required` / `operator_or_admin`，见 [deps.py](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/back_end/app/api/deps.py:30) 和 [service_reports.py](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/back_end/app/api/v1/routes/service_reports.py:144)。这意味着文档承诺了一个系统根本不存在的角色和访问路径。

4. 运行详情契约把 `report_payload.sections` 固定写成月报章节键，见 [service-report-auto-generation.yaml](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/docs/contracts/service-report-auto-generation.yaml:443)。但产品和实现都支持三套独立结构，实际季度/年报会返回不同 key。这会把后续 SDK、前端类型、外部集成全部带偏，属于必须修正的结构性错误。

## 非阻塞建议
1. [service-report-auto-generation-task-breakdown.md](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/docs/features/service-report-auto-generation-task-breakdown.md:15) 还写着“只做月报主链路，季报和年报先复用同结构”，这和已经实现的三套独立结构不一致。建议把实施清单改成“前端页面共用，章节结构独立”，避免后续评审时反向误导。

2. [service_reports.py](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/back_end/app/api/v1/routes/service_reports.py:141) 的配置列表接口没有实现契约里的 `page/page_size`，只返回 `items + total`。现阶段前端没依赖分页，还不致命，但如果继续扩配置量，最好尽快补齐。

3. `source-runs` 的时间解析现在复用了 `ServiceReportRunCreateRequest` 做占位校验，见 [service_reports.py](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/back_end/app/api/v1/routes/service_reports.py:183)。能跑，但可读性一般。建议单独补一个 multipart 表单 schema，后面加文件级校验时更稳。

## What Already Exists
- 现有统一响应包装、异常码和权限依赖已经复用，没有重造基础设施。
- 现有前端布局、列表页模式、Axios 拦截器已复用，没有额外造一套请求栈。
- 现有“脚本迁移 + 可选自动建表”是仓库既有模式，本次延续了这个方向。
- 报告模块没有重用原 `summary` 域模型，这是对的。两者语义不同，硬复用反而会把边界搞脏。

## NOT in Scope
- `PDF / DOCX` 导出：先不做，`markdown/html` 已能验证主链路。
- 自动发邮件：先不做，避免把 SMTP、审批、对外交付揉进一个版本。
- 邮件监控统计接入：先不做，当前四类主数据源已够跑通报告核心价值。
- 模板设计器：先不做，模板 owner 先通过固定模板控制变更。

## 测试与失败模式
- 已覆盖的关键路径：
  - 配置创建
  - 单项目冲突
  - `ready / partial / blocked`
  - `manual_note`
  - 导出门槛
- 当前仍需人工关注的失败模式：
  - 真实库字符集差异导致 ORM 自动建表失败。现有脚本可兜底，但自动建表路径没有测试覆盖。
  - 契约消费者按旧 JSON body 调 `source-runs` 会直接 422。
  - 如果后续真加 `viewer`，现在所有只读接口都会先被 403 卡住。

## 是否建议继续推进
建议继续推进，但先修上面 4 个阻塞问题，再把“契约、文档、实现”重新拉齐。

## 是否建议合并当前实现
`DONE_WITH_CONCERNS`

不建议现在就把这版当成“稳定契约”对外扩散。代码主链路已经能跑，真实 MySQL 冒烟也通过了，但文档和权限承诺已经和实现分叉。先修阻塞项，再合并会更稳。
