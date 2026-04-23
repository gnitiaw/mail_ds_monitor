# Mail DS Monitor

邮件数据监控系统：自动拉取邮箱邮件，通过 AI 提取结构化信息，生成每日汇总报告并发送。

## Quick Start

### Prerequisites

- Python >= 3.12
- Node.js >= 18
- MySQL 8.0+
- Git

### 1. Clone

```bash
git clone https://github.com/gnitiaw/mail_ds_monitor.git
cd mail_ds_monitor
```

### 2. Backend Setup

```bash
cd back_end

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Install dependencies (includes dev tools: pytest, ruff)
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env — at minimum set MySQL credentials and LLM API key
```

Key `.env` fields to configure:

| Field | Description |
|-------|-------------|
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_DATABASE` / `MYSQL_USER` / `MYSQL_PASSWORD` | Database connection |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | AI extraction (OpenAI-compatible endpoint) |
| `SECRET_KEY` | JWT signing key (change from default!) |

Set `DB_AUTO_CREATE_TABLES=true` for auto table creation on first run.

```bash
# Start backend
uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000, API docs at http://localhost:8000/docs.

### 3. Frontend Setup

```bash
cd front_end
npm install
npm run dev
```

Frontend runs at http://localhost:5173, proxies `/api` to backend.

### 4. Seed Demo Data

```bash
cd back_end
.venv\Scripts\activate
python scripts/seed_pilot_data.py
```

Creates demo users: `admin` / `admin123` (admin role), `operator` / `operator123` (operator role).

### 5. Verify

Open http://localhost:5173, log in with `admin` / `admin123`.

## Architecture

Monorepo, 前后端分离，REST API 通信。

**Backend** (FastAPI + SQLAlchemy + MySQL):
- `app/api/v1/` — REST 路由，按领域组织
- `app/services/` — 业务逻辑层（IMAP、AI 提取、SMTP、调度）
- `app/models/` — SQLAlchemy ORM 模型
- `app/schemas/` — Pydantic 请求/响应 schema
- `app/core/` — 配置、安全（JWT）、异常处理

**Frontend** (React 19 + TypeScript + Ant Design 6 + Vite 8):
- `src/pages/` — 按功能域组织的页面组件
- `src/components/` — 共享组件（Layout、AuthRoute）
- `src/api/` — Axios API 客户端

## Commands

### Backend

```bash
cd back_end
uvicorn app.main:app --reload       # Dev server :8000
pytest                               # Run tests
pytest app/tests/test_xxx.py -k "test_name"  # Single test
ruff check .                         # Lint
ruff check . --fix                   # Auto-fix lint issues
```

### Frontend

```bash
cd front_end
npm run dev           # Dev server :5173
npm run build         # Production build (tsc + vite)
npm run lint          # ESLint
npm run test          # Vitest (watch mode)
npm run test:run      # Vitest (single run)
```

## Business Flows

1. IMAP 拉取邮件 → `mail_messages` 表
2. AI (LLM) 提取结构化数据 → `archive_records` 表
3. 提取失败的邮件进入 `failure_mail_queue`，支持重试
4. 每日汇总按 `summary_configs` 配置生成并发送
5. 发件人画像关联客户分析
6. 服务报告聚合多源数据（巡检、漏洞、工时、禅道缺陷）

## Directory Structure

```
mail_ds_monitor/
├─ back_end/              # Backend (FastAPI)
├─ front_end/             # Frontend (React + Vite)
├─ scripts/               # Utility scripts (seed data, migrations)
├─ docs/
│  ├─ features/           # Feature specifications
│  ├─ contracts/          # API contracts
│  ├─ reviews/            # Review records
│  └─ release-notes/      # Release notes
├─ CLAUDE.md              # AI assistant instructions
└─ DESIGN.md              # Clay design system spec
```

## Development Workflow

- 新功能先完成 `docs/features/` 功能说明和 `docs/contracts/` 接口契约
- 接口契约变更需输出 diff、影响分析、兼容性说明
- 所有变更可 review、可测试、可回滚
