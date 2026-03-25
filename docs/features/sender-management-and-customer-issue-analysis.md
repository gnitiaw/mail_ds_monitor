# 功能名称：发件人管理与客户问题归类分析

## 一、背景
当前系统已经可以拉取邮件、展示原始邮件、做 AI 归档，并支持生成汇总内容，但仍有两个明显缺口：

1. 系统只有 `sender_email` 字段，没有“发件人主数据”层，用户无法把同一个客户的发件人邮箱沉淀成可复用配置。
2. 当前汇总更偏“全局邮件清单”，缺少“按客户归类”这一层，导致不同客户的问题邮件、风险标签、摘要信息仍然混在一起，管理者很难快速判断某个客户近期到底出了什么问题。

这个功能的目标不是做一个完整 CRM，而是在现有 `Summary` 主链路上补一层轻量的“发件人识别与客户归类”能力，让页面预览和最终邮件发送共享同一份客户问题摘要口径。

## 二、目标
- 让用户可以基于已出现的发件人邮箱，建立发件人档案并映射到客户。
- 让系统在统计汇总时，按客户归并问题邮件，而不是只按时间顺序平铺。
- 输出可直接用于页面展示和后续邮件发送的“客户问题归类摘要”。
- 对未识别发件人保持可见，避免因为未建档而把邮件静默漏掉。

## 三、用户故事
- 作为售后或运营人员，我希望从系统里看到近期出现过哪些发件人邮箱，并快速把它们标记到具体客户，从而减少每次靠人工猜测客户归属。
- 作为主管，我希望在汇总配置里生成并查看某个时间窗口内不同客户的问题邮件归类结果，再决定是否发送，从而保证页面上看到的内容和最终发出的邮件一致。
- 作为系统管理员，我希望在发件人识别规则变更后，汇总分析能复用同一套映射口径，从而避免页面口径和汇总口径不一致。

## 四、主要流程
1. 系统从 `mail_messages` 和 `archive_records` 中聚合近期出现过的发件人邮箱，形成“待识别发件人池”。
2. `admin` 在“发件人管理”页查看候选发件人，选择某个邮箱并建立发件人档案。
3. `admin` 为档案填写客户名称、发件人标签、匹配方式、备注等信息。
4. 用户在现有“汇总配置”中创建或编辑 `customer_grouped` 模式的配置，设置邮箱范围、状态范围、是否包含未识别发件人、每客户样例数量、分析模式等参数。
5. 用户在现有 `Summary` 模块中触发“生成分析”，系统创建 `analysis_run` 并进入后台执行。
6. 系统按发件人档案把 `archive_records + mail_messages` 归并到客户维度，并统计问题数量、优先级、风险标签、问题类型和样例邮件。
7. 系统把结构化结果和 `summary_markdown` 写入 `analysis_runs.result_payload`，页面通过轮询看到运行状态和结果。
8. 用户确认某条 `success` 状态的 `analysis_run` 后，显式选择该结果执行发送。
9. 系统创建 `summary_send_record`，并通过 `analysis_run_id` 关联实际发送所用的分析结果。
10. 未命中任何发件人档案的邮件统一归入“未识别发件人”分组，提示后续补充建档。

## 五、边界情况
- 发件人邮箱为空或解析失败时，不参与已识别客户归类，只计入“未识别发件人”。
- 同一邮箱如果已存在启用中的发件人档案，重复创建应阻止并返回冲突。
- 第一阶段只支持两种匹配方式：
  - `exact_email`：精确邮箱匹配
  - `email_domain`：邮箱域名匹配
- 当 `exact_email` 和 `email_domain` 同时可能命中时，优先使用 `exact_email`。
- 客户问题摘要主口径只基于 `archive_records` 及其关联 `mail_messages`，不直接把 `failure_queue` 混入主统计口径。
- 固定优先级为 `exact_email > email_domain`，不支持正则、模糊名称匹配。
- 当 AI 摘要增强不可用或限流时，分析运行必须降级为基础规则汇总，不能因为 AI 失败导致整个分析不可用。
- 只有 `success` 状态的 `analysis_run` 可以执行发送。
- `customer_grouped` 模式发送必须显式绑定 `analysis_run_id`。
- 旧普通汇总 `flat` 模式暂时兼容 `start_time/end_time` 发送路径。
- 未识别发件人必须可见，不能被过滤掉或静默忽略。

## 六、前端改动范围
- 继续复用现有 `Summary` 模块，不新建独立分析子系统。
- 新增“发件人管理”页面：
  - 候选发件人列表
  - 已建档发件人列表
  - 新建/编辑发件人档案弹窗
- 在现有“汇总配置”页面扩分析参数：
  - `summary_scope_mode`
  - `include_unidentified_senders`
  - `top_n_per_customer`
  - `customer_analysis_mode`
- 在现有 `Summary` 模块新增分析运行列表/详情：
  - 展示 run 状态
  - 展示客户归类结果与 `summary_markdown`
  - 展示失败原因和是否触发 AI 降级
- 交互要求：
  - 支持从候选发件人一键带入新建表单
  - 支持按“已识别/未识别”筛选候选发件人
  - 支持 `analysis_run` 轮询
  - 支持空态、加载态、分析失败态、重跑态
- 状态管理改动：
  - 新增 sender profiles API 层
  - 新增 analysis runs API 层
  - 更新 summary config / send / send records API 层

## 七、后端改动范围
- 新增发件人档案模型 `sender_profiles`
- 扩展现有 `summary_configs` 显式字段：
  - `summary_scope_mode`
  - `include_unidentified_senders`
  - `top_n_per_customer`
  - `customer_analysis_mode`
- 新增发件人候选聚合查询接口
- 新增发件人档案 CRUD 接口（本期至少列表、创建、更新）
- 新增 `analysis_runs` 模型与配置作用域接口
- 扩展 `summary_send_records`，显式关联 `analysis_run_id`
- 服务层新增：
  - 发件人匹配服务
  - 客户问题归类分析服务
  - 分析摘要生成与 AI 降级逻辑
  - 发送前校验指定 `analysis_run_id` 的服务逻辑
- 数据库变更：
  - 新建 `sender_profiles` 表
  - 新建 `analysis_runs` 表
  - 为常用查询补索引
- 日志与审计：
  - 建档、更新档案、执行分析运行、发送汇总需记录基础日志
- 权限控制：
  - 登录用户可查看分析结果
  - `admin` 可创建和更新发件人档案
  - `operator` 只读候选发件人和分析结果

## 八、验收标准
- [ ] 用户可以看到候选发件人列表，并按已识别/未识别筛选
- [ ] `admin` 可以基于候选发件人创建发件人档案
- [ ] 系统可以按 `exact_email` 和 `email_domain` 两种方式识别客户
- [ ] 用户可以在现有 `Summary` 模块中生成 `analysis_run`
- [ ] 分析结果可以按客户输出问题邮件统计结果
- [ ] 分析结果中包含未识别发件人分组
- [ ] 分析结果返回结构化数据和 `summary_markdown`
- [ ] AI 分析失败时，系统仍能返回基础规则汇总或明确失败状态
- [ ] `customer_grouped` 模式只能基于成功的 `analysis_run` 执行发送
- [ ] 旧 `flat` 模式的普通汇总发送保持兼容
- [ ] 权限范围内用户可正常访问，未登录用户会被拦截

## 九、测试点
- 正常流程：
  - 候选发件人列表加载成功
  - 从候选发件人创建档案成功
  - 精确邮箱命中客户成功
  - 域名匹配命中客户成功
  - 创建 `customer_grouped` 汇总配置成功
  - 创建 `analysis_run` 返回 `pending`
  - 轮询到 `success`
  - 基于 `analysis_run_id` 发送成功
- 参数错误：
  - `match_type` 非法
  - `match_value` 为空
  - `top_n_per_customer` 非法
  - `customer_grouped` 模式发送时缺失 `analysis_run_id`
- 权限不足：
  - 未登录访问接口
  - `operator` 查询超出 mailbox scope 的邮箱范围
  - `operator` 尝试创建或修改发件人档案
- 状态冲突：
  - 重复创建相同匹配规则
  - 更新后与现有规则冲突
  - 同一配置和同一时间窗口重复生成分析 run
  - 非 `success` run 尝试发送
- 空数据：
  - 没有候选发件人
  - 时间窗口内没有归档记录
  - 只有未识别发件人，没有任何已建档客户
- 重复提交：
  - 重复创建相同档案
  - 同一分析条件重复触发时复用已有活动 run
  - 旧 `flat` 模式重复发送兼容路径

## 十、风险点
- 发件人邮箱不一定稳定，同一客户可能使用多个邮箱或共享域名，单靠邮箱归属会有误判。
- 现有归档结果里的 `summary / business_type / risk_tags / entities` 质量不稳定时，会影响客户问题分析质量。
- 如果把域名匹配开得太宽，容易把多个客户或内部系统邮件错误归并到同一个客户。
- 候选发件人聚合如果不限制时间范围，数据量会持续变大，列表性能会下降。
- 这是对现有 `summary` 主链路的扩展，不是旁路功能，任何字段和发送语义变更都可能打坏旧普通汇总。
- `analysis_runs` 如果不保存配置快照和结果快照，后续无法解释某次邮件发送为何得出当前摘要。
- 如果 `customer_grouped` 模式和旧 `flat` 模式共存时边界不清，前后端很容易出现“双真相”。

## 十一、待确认问题
- 当前客户归类主键先固定为 `customer_name`；`customer_code` 本期仅作可选补充字段，不参与首期主匹配与汇总分组。
- 域名匹配是否允许跨多个客户共享同一域名，如果允许，需要什么冲突策略。
- 兼容迁移期预计保留旧 `flat` 发送路径多久。
- 是否需要在发送记录页中直接展示关联 `analysis_run_id` 和摘要模式。

## 十二、前后端任务拆分
### 后端
1. 新增 `sender_profiles` 模型和迁移
2. 新增 `analysis_runs` 模型和迁移
3. 扩展 `summary_configs` 和 `summary_send_records`
4. 新增候选发件人聚合查询接口
5. 新增发件人档案列表、创建、更新接口
6. 新增配置作用域分析接口：
   - `POST /summary-configs/{config_id}/analysis-runs`
   - `GET /summary-configs/{config_id}/analysis-runs`
   - `GET /analysis-runs/{run_id}`
7. 改造汇总发送接口，支持 `customer_grouped` 模式下显式绑定 `analysis_run_id`
8. 实现发件人匹配优先级：
   - `exact_email` 优先于 `email_domain`
9. 实现 `analysis_run` 状态机、幂等键、配置快照和 AI 降级逻辑
10. 补测试：
    - 匹配规则
    - 冲突校验
    - mailbox scope
    - `analysis_run` 生命周期
    - `customer_grouped` 发送路径
    - 旧 `flat` 兼容路径

### 前端
1. 新增“发件人管理”入口与页面
2. 新增候选发件人列表、发件人档案列表与表单弹窗
3. 扩展现有汇总配置页面，增加客户归类参数
4. 在现有 `Summary` 模块新增分析运行列表/详情与轮询逻辑
5. 发送动作改为显式绑定成功的 `analysis_run_id`
6. 处理空态、错误态、未识别发件人提示、兼容 flat/customer_grouped 两种模式
7. 补最小测试或手工联调清单
