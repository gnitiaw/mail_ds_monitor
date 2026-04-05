### 项目简介

`mail_ds_monitor` 是一个围绕邮件监控相关业务场景建设的研发工作区仓库，用于统一管理：

- `back_end`：后端项目
- `front_end`：前端项目

该仓库不仅存放代码，也沉淀研发过程中的关键文档与流程约束，确保开发过程清晰、可追踪、可 review、可测试、可回滚。

### 工作区定位

本仓库的核心目标不是简单存放前后端代码，而是建立一套标准化研发协作机制，包括：

- 需求提出与功能拆解
- 功能说明文档沉淀
- 接口契约设计与确认
- 后端与前端按契约并行开发
- 联调测试
- Review 结论记录
- 发布说明归档

### 标准功能开发流程

1. 提出新功能需求  
2. 生成功能说明文档 `docs/features/`  
3. 生成接口契约文档 `docs/contracts/`  
4. 确认需求与契约  
5. 后端实现  
6. 前端实现  
7. 联调与测试  
8. Review  
9. 合并与发布  

### 目录说明

```text
mail_ds_monitor/
├─ .claude/
├─ back_end/              # 后端项目
├─ front_end/             # 前端项目
├─ docs/
│  ├─ features/           # 功能说明文档
│  ├─ contracts/          # 接口契约文档
│  ├─ reviews/            # Review 结论
│  └─ release-notes/      # 发布说明
├─ scripts/               # 工作区脚本
├─ AGENTS.md
└─ README.md
```

### 研发约定

- 未完成功能说明和接口契约前，不进入正式编码
- 前后端开发以契约为准
- 所有变更必须可 review、可测试、可回滚

### 项目特点

- 采用前后端分离的工作区管理方式
- 强调文档先行和接口契约驱动开发
- 研发流程清晰，便于协作、审计与维护
- 支持功能开发、联调、review 和发布全流程管理
- 适合作为轻量级工程化协作仓库实践

### Codex 在项目中的作用

本项目在建设和维护过程中持续使用 OpenAI Codex，用于辅助：

- 功能设计与实现
- 文档编写与整理
- 接口契约生成
- 代码优化与重构
- Review 流程支持
- 工作区协同开发

**This project is built and maintained with the help of OpenAI Codex.**

### 使用说明

该仓库为工作区仓库，具体运行方式取决于 `back_end` 和 `front_end` 子项目。

一般使用方式如下：

#### 1. 克隆仓库

```bash
git clone https://github.com/gnitiaw/mail_ds_monitor.git
cd mail_ds_monitor
```

#### 2. 阅读功能说明与契约文档

优先查看：

- `docs/features/`
- `docs/contracts/`

#### 3. 分别进入前后端项目开发

后端开发：

```bash
cd back_end
```

前端开发：

```bash
cd front_end
```

#### 4. 按工作区流程进行联调、Review 与发布

开发完成后，应补充或更新：

- `docs/reviews/`
- `docs/release-notes/`

### 适用价值

本仓库适合作为以下场景的参考：

- 前后端分离项目的统一工作区管理
- 文档驱动 / 契约驱动开发实践
- AI 辅助研发协作流程
- 使用 Codex 参与真实工程开发的案例

### 推荐 GitHub Topics

建议为仓库添加以下 Topics：

- `ai-assisted-development`
- `codex`
- `automation`
- `monitoring`
- `frontend-backend-workspace`
- `contract-first`

### 维护者说明

我是该项目的核心维护者。  
该仓库在真实工作需求驱动下持续演进，并在从 0 到 1 的建设与后续迭代过程中长期使用 Codex 参与开发与 Review。
