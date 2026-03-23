# Eng Review - A 类客户关键失败邮件捕获层

## Review 范围
- 评审对象：[a-class-failure-mail-capture-office-hours-design.md](D:/Projects/codex/mail_ds_monitor/docs/features/a-class-failure-mail-capture-office-hours-design.md)
- 评审目标：把“本周可试点上线”的工程边界锁定，避免重新滑回大而全平台
- 当前已确认的关键决策：
  - 试点只覆盖明确的一组现有邮箱
  - A 类客户名单与失败识别规则存数据库配置，先不做复杂后台
  - 新建独立失败邮件队列表
  - 采用最小后台任务模型
  - 识别链路采用五段式流水线
  - 前端新增专用失败队列页与详情页
  - 本周补最小登录与 `admin/operator` 两级角色
  - 自动轮询 + 手动补跑
  - 数据库唯一约束防重
  - 状态机为 `new -> acknowledged -> resolved`
  - 提醒采用“短窗口即时聚合 + 固定频率汇总”

## Step 0: Scope Challenge
- 结论：**Scope reduced and locked**
- 从“统一邮件监控/AI 归档平台”收敛为“试点邮箱范围内的 A 类客户关键失败邮件捕获层”
- 这个收窄是正确的。它让“100% 收住”成为可验证工程目标，而不是抽象愿景

## Architecture Review

### 推荐系统图
```text
[试点邮箱组]
     |
     v
[后台轮询任务] -----> [任务记录]
     |
     v
[邮件拉取]
     |
     v
[规则匹配]
     |
     +---- no match ----> [记录扫描结果 / 跳过]
     |
     v
[字段提取]
     |
     v
[失败邮件队列表]
     |
     +---- new ----------> [短窗口聚合提醒 -> 监督人]
     |
     v
[失败队列页 / 详情页]
     |
     +---- acknowledged
     |
     +---- resolved
     |
     v
[固定频率汇总邮件 -> 监督人]
```

### 推荐表设计
```text
mail_capture_rules
  - id
  - enabled
  - customer_scope_type
  - customer_match_config
  - sender_patterns
  - subject_patterns
  - body_patterns
  - failure_rule_key
  - priority

failure_mail_queue
  - id
  - mailbox_id
  - source_message_id
  - provider_uid
  - failure_rule_key
  - customer_name
  - task_identifier
  - subject
  - sender
  - received_at
  - status(new/acknowledged/resolved)
  - matched_snapshot
  - first_captured_at
  - last_seen_at
  - acknowledged_at
  - acknowledged_by
  - resolved_at
  - resolved_by

capture_task_runs
  - id
  - task_type(poll/manual_replay)
  - mailbox_scope
  - status
  - started_at
  - finished_at
  - scanned_count
  - matched_count
  - deduped_count
  - error_message
```

### 架构判断
- **OK** 独立失败队列表是对的，比复用通用归档模型更清晰
- **OK** 最小后台任务模型是必须项，能修正当前“伪 pending，真同步”的结构缺陷
- **OK** 五段式流水线适合测试和规则迭代
- **WARNING** 现有 `TaskLog` 已存在，但如果这次再另起一套完全平行的任务记录模型，会产生“双任务真相”

### 工程建议
- 优先复用现有 [task_log.py](D:/Projects/codex/mail_ds_monitor/back_end/app/models/task_log.py) 的概念，必要时做最小扩展，而不是再造一个同类抽象
- 失败邮件队列表应是新的业务表，因为这次状态机与归档域明显不同
- 规则配置必须带“快照落库”，否则后续规则变更后无法解释一条邮件当时为什么被命中

## Code Quality Review
- **OK** 这次不应把识别规则写死在代码里。存库是正确选择
- **OK** 不应把失败队列硬塞进 `archive_records`
- **WARNING** 如果“字段提取”阶段一上来就引入复杂 AI 解析，会破坏第一版可测性。建议严格限定为规则提取或轻量字符串抽取
- **WARNING** 状态推进必须是显式操作，不能靠“打开详情页就自动 acknowledged”这种隐式行为
- **OK** 提醒链路必须基于状态与时间窗口，不能直接绑在“每次命中就立刻发”

## Test Review

### CODE PATH COVERAGE
```text
CODE PATH COVERAGE
===========================
[+] capture scheduler
    |
    ├── auto poll run
    │   ├── [GAP] 试点邮箱遍历成功
    │   ├── [GAP] 单邮箱拉取失败不拖垮整轮任务
    │   └── [GAP] 手动补跑与自动轮询重叠时的并发保护
    |
    └── manual replay run
        ├── [GAP] 指定邮箱补跑成功
        └── [GAP] 重复补跑不产生重复队列项

[+] matching pipeline
    |
    ├── rule matching
    │   ├── [GAP] 命中样本邮件
    │   ├── [GAP] 非目标邮件不命中
    │   ├── [GAP] 多规则命中时优先级处理
    │   └── [GAP] 规则禁用后不再命中
    |
    ├── field extraction
    │   ├── [GAP] 客户信息提取成功
    │   ├── [GAP] 任务标识缺失时仍可入队
    │   └── [GAP] 编码异常正文的降级行为
    |
    └── queue persist
        ├── [GAP] 新邮件入队
        ├── [GAP] 唯一约束防重
        └── [GAP] 已存在记录更新时间戳而非重复插入

[+] notification pipeline
    |
    ├── short-window alert
    │   ├── [GAP] 短窗口内聚合多封失败邮件
    │   ├── [GAP] 空窗口不发提醒
    │   └── [GAP] 邮件发送失败不影响队列入库
    |
    └── scheduled digest
        ├── [GAP] 只汇总 new/acknowledged 未解决项
        └── [GAP] resolved 项不重复提醒
```

### USER FLOW COVERAGE
```text
USER FLOW COVERAGE
===========================
[+] operator flow
    |
    ├── [GAP] 登录后查看失败队列
    ├── [GAP] 查看详情并确认命中原因
    ├── [GAP] 将 new 改为 acknowledged
    └── [GAP] 将 acknowledged 改为 resolved

[+] supervisor flow
    |
    ├── [GAP] 收到短窗口聚合提醒
    ├── [GAP] 收到固定频率汇总
    └── [GAP] 看到仍未 resolved 的积压项

[+] regression paths
    |
    ├── [GAP] 现有邮箱拉取能力不被新规则破坏
    ├── [GAP] 现有汇总邮件能力仍正常发送
    └── [GAP] 最小登录不影响现有页面基础访问流转

─────────────────────────────────
COVERAGE: 0/24 paths tested in plan
  Code paths: 0/17
  User flows: 0/7
QUALITY:  ★★★: 0  ★★: 0  ★: 0
GAPS: 24 paths need tests
CRITICAL: 必须建立真实样本回放回归测试
─────────────────────────────────
```

### 必须补进计划的测试
- 单元测试
  - 规则匹配命中/未命中/多规则优先级
  - 字段提取缺失字段与乱码降级
  - 唯一约束防重逻辑
  - 状态机合法/非法流转
  - 提醒聚合窗口计算
- 集成测试
  - 后台轮询任务从邮箱拉取到入队
  - 手动补跑不产生重复项
  - 邮件发送失败不影响入队结果
  - 最小鉴权与队列接口权限
- 样本回放测试
  - 至少 20 到 50 封真实失败邮件样本
  - 至少一组非目标邮件作为负样本
  - 至少一组重复扫描样本
  - 至少一组边界样本：主题变体、正文乱码、缺任务标识
- E2E 测试
  - operator 登录 -> 看到队列 -> 查看详情 -> acknowledged -> resolved
  - supervisor 收到提醒 -> 打开系统 -> 看到同一条记录状态变化

## Performance Review
- **OK** 试点范围限定邮箱组后，性能压力可控
- **WARNING** 自动轮询 + 手动补跑的并发，如果没有任务锁，会导致重复扫描和竞争写入
- **WARNING** 短窗口聚合提醒需要明确批次边界，否则容易重复发同一批提醒
- **OK** 独立队列表后，查询性能可以通过简单索引保障：
  - `status + received_at`
  - `mailbox_id + received_at`
  - `failure_rule_key`

## Failure Modes

| Codepath | Failure Mode | Test? | Error Handling? | User Visible? | Level |
|---|---|---:|---:|---:|---|
| 自动轮询 | 某个试点邮箱连接失败 | No | Planned | Partial | Warning |
| 自动轮询 | 自动轮询与手动补跑并发重叠 | No | Planned | No | Warning |
| 规则匹配 | 真实失败邮件未命中 | No | No | Silent | **CRITICAL** |
| 规则匹配 | 非目标邮件误命中 | No | No | Visible | Warning |
| 字段提取 | 客户名/任务号没提出来 | No | Planned | Partial | Warning |
| 入队 | 重复扫描生成重复队列项 | No | Planned | Visible | Warning |
| 状态流转 | `resolved` 被误操作回退 | No | Planned | Visible | Warning |
| 即时提醒 | 聚合窗口重复发送同一批记录 | No | No | Visible | Warning |
| 汇总提醒 | 发送失败导致监督人没看到 | No | Planned | Partial | Warning |
| 登录鉴权 | operator 看到不该看的邮箱数据 | No | Planned | Silent | **CRITICAL** |

### Critical Gaps
1. 真实失败邮件未命中且没有样本回放测试，这是第一版最大的系统性风险
2. 最小登录如果只做“有无登录”而没有邮箱范围控制，试点数据边界会失效

## What Already Exists
- 已有邮箱拉取能力：**复用**
- 已有通用归档能力：**不复用为主模型，只可借鉴字段与列表实现**
- 已有汇总发信能力：**复用**
- 已有任务日志模型：**应复用或扩展，不建议平行再造**
- 已有前端列表/详情框架：**复用布局与交互模式，不复用语义**

## NOT in Scope
- 全部门共享邮箱协作：本周试点不做
- 所有客户邮件统一管理：只做 A 类客户关键失败邮件
- 全自动 AI 处理闭环：第一版不做
- 复杂角色体系：只做最小 `admin/operator`
- 客户发信侧改造：不作为前提
- 全量邮箱覆盖：只覆盖明确试点邮箱组
- 复杂状态机：不做 `suppressed / escalated / false_positive`

## 测试计划落地建议
- 新建测试文件建议：
  - `back_end/app/tests/test_failure_capture_rules.py`
  - `back_end/app/tests/test_failure_queue_api.py`
  - `back_end/app/tests/test_capture_scheduler.py`
  - `back_end/app/tests/test_capture_notifications.py`
- 样本数据建议：
  - `back_end/app/tests/fixtures/failure_mail_samples/`
  - `positive/`
  - `negative/`
  - `duplicate/`
  - `edge_cases/`
- 前端建议：
  - `front_end/src/pages/FailureQueue/*`
  - 补最小页面交互测试或至少保留手工联调清单

## Performance 建议
- 为后台任务增加“同邮箱同时间窗只允许一个活跃任务”的锁
- 聚合提醒需要持久化“已纳入哪一批提醒”的批次标识
- 队列列表默认按 `status, received_at desc`，不要一开始做重筛选器

## 结论

### 阻塞问题
1. 必须建立真实失败邮件样本回放回归测试，否则“100% 收住”无法证明
2. 最小登录必须带试点邮箱范围控制，否则会形成数据越权或边界失效

### 非阻塞建议
1. 复用或扩展现有任务日志概念，不要再造平行任务模型
2. 即时提醒采用短窗口聚合，不要逐封发邮件
3. 前端做专用失败队列页，不要硬塞进通用归档页

### 是否建议进入实现
- **建议进入实现**
- 前提：上述 2 个阻塞问题在实现方案里被明确写入并执行

## Completion Summary
- Step 0: Scope Challenge — scope reduced per recommendation
- Architecture Review: 0 新阻塞，1 个结构性 warning
- Code Quality Review: 2 个 warning
- Test Review: diagram produced, 24 gaps identified
- Performance Review: 2 个 warning
- NOT in scope: written
- What already exists: written
- TODOS.md updates: 0
- Failure modes: 2 critical gaps flagged
- Lake Score: 9/9 recommendations chose complete option

## Unresolved Decisions
- 无
