# 服务报告 V1 联调手册

## 一、目的
本手册用于指导测试、交付或研发同学完成服务报告 V1 的本地联调，覆盖以下主链路：

1. 登录系统
2. 进入服务报告配置页
3. 新增配置
4. 运行时上传四类文件
5. 生成报告
6. 验证 `ready / partial / blocked`
7. 保存 `manual_note`
8. 导出 `markdown / html`

## 二、联调环境

### 后端
工作目录：

```powershell
cd C:\Users\sunrui\.codex\worktrees\701b\mail_ds_monitor\back_end
```

启动命令：

```powershell
$env:CAPTURE_POLL_ENABLED='false'
$env:MAIL_PULL_ENABLED='false'
$env:SUMMARY_ENABLED='false'
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/v1/health
```

### 前端
工作目录：

```powershell
cd C:\Users\sunrui\.codex\worktrees\701b\mail_ds_monitor\front_end
```

启动命令：

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

访问地址：

- 前端首页：`http://127.0.0.1:5173`
- 后端接口文档：`http://127.0.0.1:8000/api/v1/docs`

## 三、数据库准备

如需补建服务报告表，先执行迁移：

```powershell
cd C:\Users\sunrui\.codex\worktrees\701b\mail_ds_monitor\back_end
uv run python ..\scripts\migrate_service_report_v1.py
```

说明：

- 当前仓库使用独立迁移脚本，不使用 Alembic
- 脚本支持幂等执行，已存在的表会自动跳过

## 四、联调账号
可直接使用以下账号登录：

- 用户名：`service_report_admin`
- 密码：`password123`

账号用途：

- `admin` 可创建配置
- `admin` 也可直接走上传、生成、导出主流程

## 五、联调样本文件
样本目录：

- [service-report-samples](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-samples)

四类标准文件：

- [inspection.csv](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-samples/inspection.csv)
- [vulnerability.csv](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-samples/vulnerability.csv)
- [worklog.csv](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-samples/worklog.csv)
- [worklog-partial.csv](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-samples/worklog-partial.csv)
- [zentao_bug.csv](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-samples/zentao_bug.csv)

## 六、页面联调步骤

### 1. 登录
- 打开 `http://127.0.0.1:5173/login`
- 使用 `service_report_admin / password123` 登录
- 成功后应进入主系统页面

### 2. 创建配置
- 进入“服务报告配置”
- 点击“新增配置”
- 填写：
  - 配置名称：`服务报告月报联调`
  - 项目名称：`Smoke Service Report Project`
  - 报告类型：`月报`
  - 周期规则：`natural_month`
  - 模板：`ops_service_monthly_v1`
  - 负责人：
    - `project_owner`
    - `template_owner`
    - `metric_owner`
  - 收件人：任意测试邮箱
- 保存成功后，应在列表页看到新配置

### 3. 运行时上传并生成 `ready`
- 在配置列表点击“上传并生成”
- 时间窗口填写：
  - `2026-04-01T00:00:00Z`
  - `2026-04-30T23:59:59Z`
- 上传文件：
  - `inspection.csv`
  - `vulnerability.csv`
  - `worklog.csv`
  - `zentao_bug.csv`
- 提交后应跳转到运行详情页

预期：

- 报告级 `completeness_status = ready`
- 所有章节 `data_status = ready`
- 导出按钮可用
- 保存 `manual_note` 后刷新仍能看到
- 导出的 markdown 不应出现“仅供内部复核”

### 4. 验证 `partial`
- 创建或使用一条季报配置
- 时间窗口填写：
  - `2026-04-01T00:00:00Z`
  - `2026-06-30T23:59:59Z`
- 上传文件：
  - `inspection.csv`
  - `vulnerability.csv`
  - `worklog-partial.csv`
  - `zentao_bug.csv`

预期：

- 报告级 `completeness_status = partial`
- `worklog` 相关章节应显示降级或内部复核提示
- 页面应提示“仅供内部复核”
- 导出按钮可用
- 导出的 markdown 必须包含“仅供内部复核”

### 5. 验证 `blocked`
- 创建或使用一条年报配置
- 时间窗口填写：
  - `2026-01-01T00:00:00Z`
  - `2026-12-31T23:59:59Z`
- 上传时故意不提供 `zentao_bug_file`

预期：

- 报告级 `completeness_status = blocked`
- 至少一个章节 `data_status = blocked`
- 导出按钮应禁用
- 若直接调导出接口，应返回 `40903`

## 七、页面验收清单
- 配置列表能展示：
  - 配置名称
  - 项目名
  - 报告类型
  - 三个 owner
  - 启用状态
- 上传弹窗要求四类文件都存在
- 运行详情能展示：
  - 时间窗口
  - `completeness_status`
  - 章节级 `data_status`
  - `manual_note`
  - `evidence_refs`
- `partial` 时明确出现内部复核提示
- `blocked` 时导出入口不可用

## 八、接口核对点
- `GET /api/v1/service-report-configs`
  - 支持 `page / page_size`
- `POST /api/v1/service-report-configs/{config_id}/source-runs`
  - 只接受 `multipart/form-data`
  - 必传四类文件
- `GET /api/v1/service-report-runs/{run_id}`
  - `report_payload.sections` 为通用数组
  - 不应把章节 key 固定死成月报结构
- 权限：
  - V1 只有 `admin / operator`
  - 不存在独立 `viewer` 承诺

## 九、自动化验证参考
如需跳过页面手动点击，可直接运行冒烟脚本：

```powershell
cd C:\Users\sunrui\.codex\worktrees\701b\mail_ds_monitor\back_end
uv run python ..\scripts\run_service_report_smoke.py
```

最新一轮输出：

- [smoke-results.json](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-smoke-output/20260417T032824Z/smoke-results.json)
- [ready markdown 示例](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-smoke-output/20260417T032824Z/smoke-service-report-project-monthly-2026-04-01.md)
- [partial markdown 示例](C:/Users/sunrui/.codex/worktrees/701b/mail_ds_monitor/scripts/service-report-smoke-output/20260417T032824Z/smoke-service-report-project-quarterly-2026-04-01.md)

## 十、结束后清理
如果本地是手动启动的开发服务，结束后可关闭对应终端，或手动停止进程。

当前常用端口：

- 后端：`8000`
- 前端：`5173`
