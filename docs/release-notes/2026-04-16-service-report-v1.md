# 巡检与运维服务报告 V1 发布说明

发布日期：2026-04-16

## 本次新增
- 新增服务报告配置能力：
  - 支持 `monthly / quarterly / annual`
  - 强制配置 `project owner / template owner / metric owner`
  - V1 保持单项目试点硬约束
  - 配置列表支持 `page / page_size`
- 新增服务报告运行链路：
  - 运行时上传 `inspection / vulnerability / worklog / zentao_bug` 四类标准文件
  - 自动生成 `source_run`
  - 基于 `source_run` 生成 `report_run`
  - `source-runs` 唯一合法请求格式为 `multipart/form-data`
- 新增报告可信度机制：
  - 报告级 `completeness_status = ready / partial / blocked`
  - 章节级 `data_status = ready / partial / blocked`
  - `blocked` 禁止导出
  - `partial` 导出内容自动带“仅供内部复核”标识
- 新增报告详情能力：
  - 章节预览
  - 数据源状态摘要
  - `manual_note` 人工补充说明
  - `markdown / html` 导出

## 数据库变更
新增 3 张表：
- `service_report_configs`
- `service_report_source_runs`
- `service_report_runs`

新增脚本：
- [migrate_service_report_v1.py](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/migrate_service_report_v1.py)

执行方式：

```powershell
cd C:\Users\sunrui\.codex\worktrees\701b\mail_ds_monitor\back_end
uv run python ..\scripts\migrate_service_report_v1.py
```

说明：
- 当前仓库没有 Alembic，本次继续沿用“独立迁移脚本”方式
- 若环境启用了 `DB_AUTO_CREATE_TABLES=true`，本次已将 ORM 模型字符集/排序规则对齐现网 MySQL，可自动建表
- 生产环境仍建议显式执行迁移脚本

## 前端入口
- `服务报告配置`
- `服务报告记录`
- 联调手册：
  - [service-report-v1-joint-debug-guide.md](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/docs/features/service-report-v1-joint-debug-guide.md)

主流程：
1. 新建配置
2. 运行时上传四类文件
3. 生成报告
4. 查看详情与章节状态
5. 保存人工补充说明
6. 导出 `markdown / html`

## 验证结果
- 后端专项测试：

```powershell
cd C:\Users\sunrui\.codex\worktrees\701b\mail_ds_monitor\back_end
uv run --with pytest pytest app/tests/test_service_report_api.py -q
```

- 前端构建：

```powershell
cd C:\Users\sunrui\.codex\worktrees\701b\mail_ds_monitor\front_end
npm run build
```

- 真实 MySQL 冒烟联调：

```powershell
cd C:\Users\sunrui\.codex\worktrees\701b\mail_ds_monitor\back_end
uv run python ..\scripts\run_service_report_smoke.py
```

联调输出：
- [smoke-results.json](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-smoke-output/20260417T032824Z/smoke-results.json)
- [ready markdown 示例](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-smoke-output/20260417T032824Z/smoke-service-report-project-monthly-2026-04-01.md)
- [partial markdown 示例](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-smoke-output/20260417T032824Z/smoke-service-report-project-quarterly-2026-04-01.md)

## 已知事项
- 当前未接入 `PDF / DOCX` 导出
- 当前未接入自动发邮件
- 当前未接入邮件监控统计与典型事件引用
- V1 权限收敛为 `admin / operator`，未引入独立 `viewer`
- 当前仍存在 FastAPI `on_event` 的旧式生命周期告警
- 前端构建存在 bundle size 警告，但不阻塞本次发布
