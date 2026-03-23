# 后端初始化说明

当前后端已经补上最小 FastAPI 骨架和配置加载模块，可作为后续业务开发的起点。

## 当前目录结构
- `back_end/.env.example`：运行配置模板
- `back_end/app/main.py`：FastAPI 入口
- `back_end/app/core/config.py`：统一配置加载
- `back_end/app/db/`：数据库连接、基类和初始化逻辑
- `back_end/app/api/`：路由骨架
- `back_end/app/models/`：MySQL ORM 模型
- `back_end/app/schemas/`：基础响应模型
- `back_end/pyproject.toml`：依赖定义

## 文件约定
- `.env.example`：仓库内保留的配置模板
- `.env`：服务器或本地实际运行配置，不应提交到仓库

## 初始化方式
1. 复制 `back_end/.env.example` 为 `back_end/.env`
2. 将数据库、SMTP、大模型相关占位值替换为真实配置
3. 安装依赖
4. 启动 FastAPI 服务

## 参考命令
```bash
cd back_end
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload
```

## 已预留的配置分类
- 应用基础配置
- MySQL 数据库配置
- 邮件拉取基础配置
- AI 提取智能体配置
- 每日汇总邮件配置
- SMTP 发信配置

## 已提供的基础接口
- `GET /api/v1/health`：健康检查
- `GET /api/v1/meta`：读取当前服务基础配置摘要
- `GET /api/v1/mailboxes`：分页查询邮箱配置
- `POST /api/v1/mailboxes`：创建邮箱配置
- `PUT /api/v1/mailboxes/{mailbox_id}`：更新邮箱配置

## 已预留的核心数据表
- `mailboxes`：邮箱接入配置
- `mail_messages`：原始邮件记录
- `archive_records`：AI 结构化归档结果
- `summary_configs`：每日汇总配置
- `summary_send_records`：汇总发送记录
- `task_logs`：拉取、提取、发送任务日志

## 当前数据库设计原则
- 原始邮件和 AI 提取结果分表保存
- 邮件记录落 MySQL，后续支持按邮箱和时间维度查询
- 归档记录以邮件记录为基础，支持重复提取和追踪失败原因
- 同一邮箱下通过 `mailbox_id + internet_message_id` 或 `mailbox_id + provider_uid` 做幂等约束

## 大模型接入后需要填写的关键项
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`

## 说明
- 多邮箱账号信息不放在 `.env` 中，后续通过系统页面写入数据库
- 首期附件解析固定关闭，对应 `MAIL_PARSE_ATTACHMENTS=false`
- 汇总发送周期已预设为按日，对应 `SUMMARY_SCHEDULE_TYPE=daily`
- `app/core/config.py` 已对汇总周期和发送时间做基础校验
- 如需在开发阶段自动建表，可将 `DB_AUTO_CREATE_TABLES=true`
