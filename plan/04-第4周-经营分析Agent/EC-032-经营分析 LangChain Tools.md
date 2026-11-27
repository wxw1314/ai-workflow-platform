# 经营分析 LangChain Tools

- **计划 ID：** EC-032
- **所属阶段：** 第4周
- **优先级：** P0
- **依赖：** EC-031, EC-030
- **状态：** 未开始

## 1. 目标与用户价值

把有限业务查询能力暴露给 Agent，支持动态选择工具。

## 2. 功能范围

### 本次包含
- 注册 query_products、query_product_sales、compare_sales_periods、query_inventory、query_promotions、query_competitors、query_competitor_snapshots、compare_competitor_prices。
- 强类型参数和描述。

### 本次不包含
- 不重建现有 FastAPI、Agent、RAG、SSE、Checkpointer、Milvus 或前端基础设施。
- 不实现本文件未列出的相邻业务功能。

## 3. 现有能力复用与代码检查

复用现有 async tools、ToolNode 和模型工具绑定。

Codex 必须先检查当前仓库真实代码、模型、路由、迁移和测试；不得凭计划臆造文件路径或重复造轮子。

## 4. 数据与接口

工具定义、参数 schema、权限上下文和工具测试。

## 5. 业务规则与边界条件

Tool 只读；限制参数、时间范围、调用次数和返回 token；模型不得指定用户身份。

## 6. 安全、权限与隐私

Tool 内部再次校验 ownership；不暴露 SQL、shell、任意 URL、任意 Python。

## 7. 人工审核 / 人工介入

本文件仅注册只读 Tools；不得添加调价/促销执行 Tool。

## 8. 异常与恢复

模型传入非法 ID、超大时间范围、重复调用、工具超时。

## 9. 测试要求

参数校验、跨租户、工具选择和失败返回测试。

## 10. 验收标准

Agent 只能通过白名单工具读取业务数据，工具调用可观测。

## 11. Codex 执行约束

1. 先只读检查并汇报现状、差异、拟修改文件和风险。
2. 等待确认后，仅实施本计划范围。
3. 先补测试，再实现或同步实现；不得删除已有测试来通过检查。
4. 不得修改自动生成的 OpenAPI SDK 文件；如 API schema 变化，按项目既定流程重新生成。
5. 汇报实际修改文件、迁移、测试命令和真实测试结果。

## 12. 验收记录

- 实际修改：
- 测试结果：
- 未解决问题：
- 验收结论：
