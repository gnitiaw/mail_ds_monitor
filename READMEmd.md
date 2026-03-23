# 开发工作区

本工作区用于统一管理以下项目：

- `back_end`：后端项目
- `front_end`：前端项目

## 标准功能开发流程

1. 提出新功能需求
2. 生成功能说明 `docs/features/`
3. 生成接口契约 `docs/contracts/`
4. 确认需求与契约
5. 后端实现
6. 前端实现
7. 联调与测试
8. Review
9. 合并与发布

## 目录说明

- `docs/features`：功能说明文档
- `docs/contracts`：接口契约文档
- `docs/reviews`：Review 结论
- `docs/release-notes`：发布说明
- `scripts`：工作区脚本

## 约定

- 未完成功能说明和接口契约前，不进入正式编码
- 前后端开发以契约为准
- 所有变更必须可 review、可测试、可回滚