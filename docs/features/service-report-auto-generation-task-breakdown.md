# 功能名称：巡检与运维服务报告自动生成 V1 实施清单

## 一、目标
本文件用于把 [service-report-auto-generation.md](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/docs/features/service-report-auto-generation.md) 和 [service-report-auto-generation.yaml](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/docs/contracts/service-report-auto-generation.yaml) 收敛成首期可执行版本。

这份清单只回答四件事：

1. V1 最少要落哪些表和对象
2. V1 最少要提供哪些接口
3. V1 最少要做哪些页面
4. 哪些东西明确先不做

## 二、V1 实施原则
- 单项目试点是硬约束，不追求一开始支持复杂多项目协同
- 前端页面共用同一套配置、运行列表和详情页，但月报、季报、年报章节结构独立
- 只保留报告快照、统计结果、章节草稿和 `evidence_refs`
- 不把原系统全量邮件监控、归档、告警明细复制进报告域
- 导出格式先只支持 `markdown`、`html`
- 数据接入允许“API 拉取 + 手工导入”并存
- 每条配置必须明确：
  - `project_owner`
  - `template_owner`
  - `metric_owner`
- 每条报告必须明确：
  - `completeness_status`
  - 章节级 `data_status`

## 三、后端最小表结构
### P0 必做
- `service_report_configs`
  - `id`
  - `name`
  - `project_name`
  - `report_type`
  - `period_rule`
  - `template_key`
  - `project_owner_user_id`
  - `template_owner_user_id`
  - `metric_owner_user_id`
  - `enabled`
  - `recipient_emails`
  - `source_bindings`
  - `created_at`
  - `updated_at`

- `service_report_source_runs`
  - `id`
  - `config_id`
  - `window_start`
  - `window_end`
  - `status`
  - `source_results`
  - `snapshot_payload`
  - `error_message`
  - `created_at`
  - `finished_at`

- `service_report_runs`
  - `id`
  - `config_id`
  - `source_run_id`
  - `window_start`
  - `window_end`
  - `status`
  - `completeness_status`
  - `config_snapshot`
  - `source_snapshot_summary`
  - `report_payload`
  - `export_artifacts`
  - `error_message`
  - `created_at`
  - `finished_at`

### P0 结构约束
- `source_bindings` 必须至少覆盖：
  - `inspection`
  - `vulnerability`
  - `worklog`
  - `zentao_bug`
- 所有启用中的配置必须属于同一个 `project_name`
- `snapshot_payload` 是内部归一结果，可比 `source_snapshot_summary` 更细，但仍然不存来源系统全量明细
- `export_artifacts` 首期只允许 `markdown`、`html`
- `service_report_runs` 不允许保存原始邮件正文、原始归档全文、原始告警明细
- `completeness_status` 只允许：
  - `ready`
  - `partial`
  - `blocked`
- `report_payload.sections[*].data_status` 只允许：
  - `ready`
  - `partial`
  - `blocked`

### P1 可补
- 模板版本表
- 导出文件独立存储表
- 手工补充说明字段

## 四、V1 最小接口集
### P0 必做
1. `GET /api/v1/service-report-configs`
   - 配置列表

2. `POST /api/v1/service-report-configs`
   - 创建配置

3. `POST /api/v1/service-report-configs/{config_id}/source-runs`
   - 以 `multipart/form-data` 触发数据汇总
   - 必传：
     - `window_start`
     - `window_end`
     - `inspection_file`
     - `vulnerability_file`
     - `worklog_file`
     - `zentao_bug_file`

4. `POST /api/v1/service-report-configs/{config_id}/report-runs`
   - 基于时间窗口和快照生成报告

5. `GET /api/v1/service-report-runs`
   - 报告运行列表

6. `GET /api/v1/service-report-runs/{run_id}`
   - 报告运行详情

7. `POST /api/v1/service-report-runs/{run_id}/export`
   - 导出报告

### P0 接口必须满足
- `source-runs` 和 `report-runs` 必须做时间窗口级别防重
- `report-runs/{run_id}` 返回：
  - `config_snapshot`
  - `source_snapshot_summary`
  - `completeness_status`
  - `report_payload`
  - `evidence_refs`
- 不返回来源系统全量明细
- 创建配置时必须校验 owner 字段
- 创建启用中配置时必须校验单项目约束

### P1 可补
- 更新配置接口
- 删除或停用配置接口
- 获取单个 `source_run` 详情接口
- 导出文件重新生成或清理接口

## 五、V1 统一快照结构
### overview
- `inspection_total`
- `inspection_exception_total`
- `vulnerability_total`
- `vulnerability_fixed_total`
- `vulnerability_unfixed_total`
- `worklog_total`
- `zentao_bug_total`
- `zentao_bug_closed_total`
- `high_risk_count`

### sections
- `monthly`
  - `executive_summary`
  - `inspection_overview`
  - `vulnerability_fix`
  - `worklog_summary`
  - `zentao_defects`
  - `risk_and_next_steps`
- `quarterly`
  - `executive_summary`
  - `quarterly_service_overview`
  - `quarterly_inspection_summary`
  - `quarterly_vulnerability_trend`
  - `quarterly_worklog_highlights`
  - `quarterly_defect_trend`
  - `next_quarter_focus`
- `annual`
  - `executive_summary`
  - `annual_service_overview`
  - `annual_inspection_summary`
  - `annual_vulnerability_governance`
  - `annual_worklog_highlights`
  - `annual_defect_summary`
  - `next_year_plan`

每个 section 必须包含：
- `title`
- `content_markdown`
- `data_status`
- `blocking_reason`

### evidence_refs
每个引用只保留：
- `source_type`
- `ref_type`
- `ref_id`
- `title`
- `summary`

不要在 V1 里加入：
- 原始正文全文
- 大块附件内容
- 原系统整条明细 JSON

## 六、前端最小页面集
### P0 必做
1. 服务报告配置列表页
   - 展示配置名称、项目、报告类型、模板、启用状态
   - 支持创建配置

2. 服务报告配置弹窗
   - 填写 `project_name`
   - 选择 `report_type`
   - 选择 `period_rule`
   - 选择 `template_key`
   - 选择 `project_owner`
   - 选择 `template_owner`
   - 选择 `metric_owner`
   - 填写 `recipient_emails`
   - 维护四类 `source_bindings`

3. 报告运行列表页
   - 展示状态、时间窗口、配置名、导出状态
   - 支持进入详情

4. 报告运行详情页
   - 展示 `source_snapshot_summary`
   - 展示 `completeness_status`
   - 展示章节草稿
   - 展示章节 `data_status`
   - 展示少量 `evidence_refs`
   - 支持导出

### P0 页面不做
- 富文本在线编辑器
- PDF 在线预览
- 原系统明细嵌入式查询页
- 复杂审批流 UI
- 多模板可视化设计器

### P1 可补
- 配置编辑
- 配置停用
- source run 单独状态页
- 人工补充说明区块

## 七、明确可砍项
这些项只要影响进度，V1 可以直接砍，不要犹豫：

- PDF 导出
- DOCX 导出
- 自动发送邮件
- 多项目批量生成
- 报告审批流
- 邮件监控统计接入
- 邮件监控典型事件引用
- 外部系统实时双向同步
- 模板设计器
- 历史版本 diff

## 八、后端开发任务
### P0
- 新建三张核心表或对应模型：
  - `service_report_configs`
  - `service_report_source_runs`
  - `service_report_runs`
- 实现配置列表、创建接口
- 实现时间窗口归一逻辑
- 实现四类数据源的统一快照映射
- 实现单项目启用约束
- 实现 owner 字段校验与回传
- 实现报告章节生成逻辑
- 实现 `completeness_status` 和章节 `data_status` 计算
- 实现 `markdown/html` 导出
- 实现最小权限控制
  - V1 仅 `admin / operator`
- 实现时间窗口幂等和状态机
- 实现 `evidence_refs` 结构

### P1
- 配置更新/停用
- source run 详情
- 人工补充说明
- 模板版本治理

## 九、前端开发任务
### P0
- 新增服务报告路由和导航入口
- 实现配置列表页
- 实现配置创建弹窗
- 实现报告运行列表页
- 实现报告运行详情页
- 实现 `ready / partial / blocked` 状态展示
- `partial` 显示内部复核提示
- `blocked` 禁用导出
- 实现导出按钮和下载提示
- 实现加载态、空态、失败态、部分数据缺失提示

### P1
- 配置编辑能力
- source run 状态明细展示
- 人工补充说明

## 十、联调顺序
1. 先联调配置创建和列表接口
2. 再联调 `source-runs`
3. 再联调 `report-runs`
4. 最后联调导出

不要一开始就联动所有数据源真接入。先用 mock 或标准化样本把快照结构跑通，再接真实来源。

## 十一、验收标准
- 可以创建月报、季报、年报配置
- 只能创建单项目启用配置
- 四类数据源可以形成统一快照
- 可以生成一条 `success` 的报告记录
- 报告记录带 `completeness_status`
- 各章节带 `data_status`
- 报告详情能展示统计摘要、章节草稿和 `evidence_refs`
- 可以导出 `markdown` 或 `html`
- 详情接口不返回原系统全量明细
- 配置列表支持 `page / page_size`

## 十二、风险清单
- 四类数据源字段差异过大，会拖慢快照结构收敛
- 运维工作记录若太散，会导致章节质量很弱
- 若模板章节在开发中频繁变化，前后端都会反复返工
- 若中途把邮件监控全量数据加进来，整个边界会立刻失控
- 若 owner 不明确，数据口径争议会卡死联调
- 若 `completeness_status` 规则不清，团队会不知道什么报告能发

## 十三、待确认问题
- 单项目试点的目标项目是谁
- 四类数据源各自首期接入方式是 API 还是导入
- 月报模板是否固定为单一模板
- 首期是否只允许手动导出，不自动发邮件
- `project_owner_user_id`、`template_owner_user_id`、`metric_owner_user_id` 分别是谁
