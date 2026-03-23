# CEO Review - 2026-03-23

## Review 范围
- 评审对象：当前 `mail_ds_monitor` 工作区的 MVP 文档、接口契约、前后端现状
- 评审方式：按 `plan-ceo-review` 思路，以 `HOLD SCOPE` 为主，补充少量战略修正建议
- 限制说明：当前工作区不含 `.git` 元数据，无法做分支/PR 级别的历史审计；后端测试因环境中缺少可用 Python 解释器未能执行

## 系统审计结论
- 文档层面已经具备 MVP 功能说明、接口契约和任务拆分，产品边界基本清晰
- 代码层面已经实现邮箱管理、归档查询、汇总配置和汇总发送的基础骨架，前端也已连通主页面
- 前端构建已通过，产物单包较大：`dist/assets/index-DHQS_pKV.js` 约 1.29 MB
- 后端更接近“单机原型”而不是“可持续运营的邮件监控系统”：同步执行外部 IO、缺少鉴权、缺少真正的任务编排与审计闭环

## 阻塞问题

### 1. 契约要求全接口鉴权，但实现里没有任何真实鉴权与授权链路
- 契约明确所有核心接口 `auth.required: true`，并区分 `admin/operator/viewer` 角色，例如 [mail-monitoring-mvp.yaml](D:/Projects/codex/mail_ds_monitor/docs/contracts/mail-monitoring-mvp.yaml#L9) 、 [mail-monitoring-mvp.yaml](D:/Projects/codex/mail_ds_monitor/docs/contracts/mail-monitoring-mvp.yaml#L174) 、 [mail-monitoring-mvp.yaml](D:/Projects/codex/mail_ds_monitor/docs/contracts/mail-monitoring-mvp.yaml#L371)
- 但后端依赖只有数据库会话，没有 `current_user`、角色校验或 token 解析，见 [deps.py](D:/Projects/codex/mail_ds_monitor/back_end/app/api/deps.py#L8) 和 [mailboxes.py](D:/Projects/codex/mail_ds_monitor/back_end/app/api/v1/routes/mailboxes.py#L30)
- 前端也只是“如果本地有 token 就带上”，并没有登录态来源和权限模型，见 [request.ts](D:/Projects/codex/mail_ds_monitor/front_end/src/api/request.ts#L12)
- 结论：以“需要登录的业务系统”定义这个产品时，这是阻塞级问题；现在只能算未鉴权 demo

### 2. 拉取与发送接口对外宣称异步 pending，实际上在请求线程里同步执行
- 邮箱拉取接口注明“始终返回 pending”，但直接调用同步 IMAP 拉取逻辑，见 [mail_messages.py](D:/Projects/codex/mail_ds_monitor/back_end/app/api/v1/routes/mail_messages.py#L30) 和 [mail_messages.py](D:/Projects/codex/mail_ds_monitor/back_end/app/api/v1/routes/mail_messages.py#L53)
- 汇总发送接口同样直接在请求线程里执行汇总查询、LLM 生成和 SMTP 发送，见 [summary.py](D:/Projects/codex/mail_ds_monitor/back_end/app/api/v1/routes/summary.py#L76) 和 [summary.py](D:/Projects/codex/mail_ds_monitor/back_end/app/api/v1/routes/summary.py#L114)
- 这与契约里“防重复触发/合并执行/任务记录查询”的产品承诺不一致，也让超时、重复点击、并发触发、外部服务抖动都直接落到用户请求上
- 结论：如果要把项目定位成“稳定监控系统”，必须引入真正的后台任务模型、锁和任务状态追踪；否则产品承诺与实现模型不一致

### 3. 提取失败原因没有沿 API 正确暴露到前端，用户会看到错误的失败信息
- 后端归档详情响应只暴露了 `parse_error`，没有暴露 `extraction_error`，见 [mail_message.py](D:/Projects/codex/mail_ds_monitor/back_end/app/schemas/mail_message.py#L49)
- 前端在“AI 提取失败”时却展示 `parse_error` 作为“提取失败原因”，见 [Detail.tsx](D:/Projects/codex/mail_ds_monitor/front_end/src/pages/Archive/Detail.tsx#L175)
- 结果是：LLM 超时、JSON 解析失败、模型拒答这类真正的提取失败，用户界面很可能看不到准确原因
- 结论：这会直接削弱运营排障能力，也破坏“失败可追踪”的产品信任

## 非阻塞建议

### 1. 任务日志模型已经存在，但没有进入主流程
- `TaskLog` 模型已定义，见 [task_log.py](D:/Projects/codex/mail_ds_monitor/back_end/app/models/task_log.py#L14)
- 但邮件拉取、AI 提取、汇总发送并未创建或更新任务日志，只把结果散落在 `last_pull_status`、`error_message` 等字段上
- 建议把“任务记录”升级为系统第一公民，否则后面做重试、告警、审计、回溯都会越做越乱

### 2. 汇总配置的数据模型有历史包袱
- `SummaryConfig` 同时保留了 `mailbox_id` 和 `mailbox_ids`，见 [summary.py](D:/Projects/codex/mail_ds_monitor/back_end/app/models/summary.py#L29)
- 但契约只围绕 `mailbox_ids` 展开，这会让后续前后端联调和迁移出现歧义
- 建议尽快收敛成单一模型，避免“看似兼容，实则双真相”

### 3. 当前前端是整包加载，演示没问题，扩功能会开始拖慢首屏
- 路由全部静态引入，没有代码分割，见 [App.tsx](D:/Projects/codex/mail_ds_monitor/front_end/src/App.tsx#L2)
- 构建产物已出现大包告警，说明这个问题不是未来才会发生，而是已经开始出现
- 建议在进入下一轮页面扩展前就把路由级拆包补上

## CEO 判断
- 这个项目的方向是对的：`多邮箱接入 + 结构化提取 + 汇总发送` 是一条清晰、可讲故事、也有真实业务落点的主线
- 但现在最大的战略风险不是“功能不够多”，而是“产品承诺已经像系统，工程形态却还像原型”
- 如果继续在当前形态上叠加页面和字段，团队会很快陷入一种错觉：看起来功能越来越全，实际稳定性、审计、权限和运维能力始终没建立起来

## 建议的下一步
1. 先收口为一个真正成立的 P0 版本：
   - 真实鉴权/角色
   - 真异步任务 + 幂等锁
   - 可见的任务日志/失败原因
2. 然后再扩展：
   - 更丰富的 AI 字段
   - 更复杂的汇总策略
   - 更多前端交互优化

## Review 结论
- 阻塞问题：3 个
- 非阻塞建议：3 个
- 是否建议合并：
  - 如果目标是“本地演示/内部原型”，可以继续迭代
  - 如果目标是“可交付 MVP / 可上线内部系统”，当前不建议进入上线或大规模扩 scope 阶段
