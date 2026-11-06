# B 模块对接说明

本次集成进度：已有规则与统一校验服务继续复用，A 已初始化前端工程并接入 B 的组件事件，完成草案编辑和重新校验。B 源码、原提交及作者保持不变；保存管理仍待完成。见 [当前交付说明](member-a-half.md) 和 [前期框架说明](member-one-framework.md)。

## 已实现的部分

- 后端 Python 3.13 / FastAPI 工程、依赖锁文件、公共 Pydantic 模型、配置、统一错误及健康检查。
- 汕头真实景点的人工参考资料，`list_attractions`、`get_catalog` 和景点查询接口；资料非实时、部分门票待确认。
- 规划入口与单 Agent：一个只读查询工具，每次最多一次工具调用、两次模型调用；超时、非法输出和服务错误按契约返回。
- 前端 `PlanningPanel.vue`：旅游需求、景点搜索和筛选、生成请求与结果事件。

后端已做离线自动化测试，Agent 工具循环使用替身模型；没有真实模型调用记录。A 主工程的类型检查、构建及组件事件对接测试已通过，另以真实本机 HTTP 验证 Vite 代理到规则生成与重新校验；这仍不代表保存闭环或真实 Agent 已验收。

## A 的工作和交接点

1. **后端**：实现 `app.itineraries.rules.make_rule_candidate(request)`、`app.itineraries.service.validate_and_enrich(draft)`，以及 `app.itineraries.router.router`。完整签名和输入/输出见 [架构约定](architecture.md)、[接口契约](api.md)。B 的入口会使用 A 的函数，不在 B 模块重复计算费用。
2. **前端（已接入）**：Vue 工程、`src/types/contracts.ts` 和 `src/api/client.ts` 已提供；公共客户端保持 `requestJson<T>(path: string, init?: RequestInit): Promise<T>`。`App.vue` 引入 B 的 `PlanningPanel.vue`，接收 `catalog-loaded`（完整景点数组）和 `plan-generated`（标准草案），传给 A 的 `TripWorkspace.vue`；新草案替换前确认，取消保留当前修改。
3. 当前入口已注册 A 的校验路由，两种生成模式均使用统一校验；缺少行程服务时的 `SERVICE_NOT_READY` 是此前交接阶段的保护分支。保存、历史与删除接口尚未实现。
4. B 的隔离前端检查使用 Vue 3.5.44、Element Plus 2.14.7、Vite 8.3.5、`vue-tsc` 3.3.14、TypeScript 5.9.3。A 主工程沿用并锁定该组合，类型检查和构建通过；不使用此前不兼容的 TypeScript 7.0.2 组合。

**汕头方案的契约变更：** `Attraction.ticket_cny` 可以为 `null`，新增 `area`、`duration_min` 与资料来源；`CandidateDay` 和 `PlanDay` 新增可选 `note`；`PlanView`/`SavedTrip` 新增 `has_unknown_prices`，`over_budget` 可以为 `null`。A 需要在类型、校验、费用、显示和快照中处理这些字段；详见 [接口契约](api.md)。已知费用未超预算且有未知价格时，不能判定预算满足。每日景点安排也需检查 BR13 的时长与南澳区域规则。

A 不需要为 B 再实现景点数据、公共 Pydantic 模型或 Agent。B 不在生产代码中提供 A 的行程服务替身，单元测试中的替身仅用于检查接口衔接。

## 后续联调

- 先核对实际分支和双方改动，再合入代码；运行后端测试及 A 的前端检查，验证规则生成、编辑、保存和删除。
- 用户自行在本地 `backend/.env` 或环境变量中提供 `LLM_MODEL`、`LLM_API_KEY`，必要时提供 OpenAI 兼容的 `LLM_BASE_URL`。请勿把真实密钥发到仓库或提交到版本控制。
- 有实际可用的支持工具调用的模型服务后，再验证真实工具查询、候选校验和超时。离线测试与真实模型联调分别记录。
