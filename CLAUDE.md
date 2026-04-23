# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

邮件数据监控系统（Mail DS Monitor）：自动拉取邮箱邮件，通过 AI 提取结构化信息，生成每日汇总报告并发送。

## 常用命令

### 后端（`back_end/`）

```bash
cd back_end
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -e .
uvicorn app.main:app --reload                     # 开发服务器 :8000
pytest                                            # 全部测试
pytest app/tests/test_xxx.py -k "test_name"       # 单个测试
ruff check .                                      # Lint
ruff check . --fix                                # 自动修复
```

### 前端（`front_end/`）

```bash
cd front_end
npm install
npm run dev           # 开发服务器 :5173，代理到 :8000
npm run build         # 生产构建（先 tsc 再 vite build）
npm run lint          # ESLint
npm run test          # Vitest（watch 模式）
npm run test:run      # Vitest（单次运行）
```

## 架构

Monorepo，前后端分离，通过 REST API 通信。

### 后端架构（FastAPI + SQLAlchemy + MySQL）

分层结构，严格单向依赖：`api/ → services/ → models/`，schemas 独立于 models。

- `app/main.py` — 应用入口，中间件、启动/关闭钩子、APScheduler 调度器初始化
- `app/api/v1/` — REST 路由，按领域组织（auth, mailboxes, messages, archives, summary, failures, analysis, senders, service_reports）
- `app/services/` — 业务逻辑层，每个服务封装一个领域（IMAP 拉取、AI 提取、SMTP 发送、失败重试、客户分析、服务报告生成等）
- `app/models/` — SQLAlchemy ORM 模型，关系和约束定义在此
- `app/schemas/` — Pydantic 请求/响应 schema，与 ORM 模型分离
- `app/core/` — 配置（`config.py` 从 `.env` 加载）、安全（JWT）、异常处理、调度器
- `app/db/` — 数据库会话管理、初始化

**关键业务流程：**
1. IMAP 拉取邮件 → `mail_messages` 表
2. AI（LLM）提取结构化数据 → `archive_records` 表
3. 提取失败的邮件进入 `failure_mail_queue`，支持重试
4. 每日汇总按 `summary_configs` 配置生成并发送
5. 发件人画像（`sender_profiles`）关联客户分析（`analysis_runs`）
6. 服务报告按配置（`service_report_configs`）聚合多源数据（巡检、漏洞、工时、禅道缺陷），生成报告（`service_report_runs`）

**认证：** JWT token，角色为 admin/operator，operator 只能访问被授权的邮箱。

**API 前缀：** `/api/v1`，统一响应格式 `{code, message, data}`

### 前端架构（React 19 + TypeScript + Ant Design 6 + Vite 8）

- `src/pages/` — 按功能域组织的页面组件（Mailbox, MailMessage, Archive, FailureQueue, Summary, Analysis, Sender, ServiceReport）
- `src/components/` — 共享组件（Layout 布局、AuthRoute 路由守卫）
- `src/api/` — Axios API 客户端模块，含 TypeScript 接口定义
- `src/utils/` — 工具函数

**设计系统：** 遵循 `DESIGN.md` 中的 Clay 设计规范（暖色调 `#faf9f7` 背景、燕麦色边框 `#dad4c8`、圆润的卡片风格）。前端修改必须遵守此设计规范。

## 开发流程约束

**禁止直接编码。** 新功能必须先完成：
1. `docs/features/` 功能说明
2. `docs/contracts/` 接口契约
3. 确认后才可进入实现

接口契约变更必须输出 diff、影响分析、兼容性说明。

## 目录边界

- 后端代码：`./back_end/**`
- 前端代码：`./front_end/**`
- 功能文档：`./docs/features/**`
- 接口契约：`./docs/contracts/**`
- Review 结论：`./docs/reviews/**`
- 脚本：`./scripts/**`

## 数据库

开发阶段设置 `DB_AUTO_CREATE_TABLES=true` 自动建表。手动迁移脚本在 `scripts/`。

关键幂等约束：`mailbox_id + internet_message_id` 或 `mailbox_id + provider_uid`。
