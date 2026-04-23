# TODOS

## TODO 1: 为解析失败邮件设计独立的解析重试能力

- What: 为 `parse_status=failed` 的原始邮件新增独立的”解析重试”能力，与本轮”提取失败重试”分开设计和交付。
- Why: 当前这轮只覆盖 `extraction_status=failed`，解析失败邮件仍然只能停留在错误态，用户容易误以为”重试功能已经全覆盖”。
- Depends on / blocked by: 依赖本轮异步重试任务模型先落地。

## TODO 2: 服务报告 v1 合并前联调

- [ ] 人工页面联调：配置创建、四文件上传、ready/partial/blocked 展示、manual_note 保存、导出按钮状态
- [ ] 试点项目验收：至少 1 个真实项目跑一次月报闭环
- [ ] 导入模板定稿：inspection/vulnerability/worklog/zentao_bug 四类文件标准表头

## TODO 3: 服务报告 v1 提测前建议

- [ ] 补测试验收单（ready/partial/blocked、单项目约束、导出门槛、权限边界）
- [ ] 补试点上线操作手册（建表、启动、配置、上传、生成、导出、常见报错）
- [ ] 再跑一轮真实样本回归（日期格式、空值、字段别名、坏行处理）

## TODO 4: 服务报告 v2 规划

- PDF / DOCX 导出
- 自动发邮件
- 审批流
- 邮件监控统计接入
- 多项目并行
- 模板设计器

## TODO 5: 技术优化

- [ ] 处理 FastAPI `on_event` 弃用告警
- [ ] 前端 bundle size 优化（code splitting，当前 >500kB）
- [ ] 替换 Ant Design 6 弃用组件（`List` → 自定义列表）
- [ ] 数据库正式迁移体系（替代脚本式迁移）
