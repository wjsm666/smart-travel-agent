# 接口和数据契约

本文是字段、HTTP、错误及保存格式的唯一详细契约。它是**待实现基线**，当前应用未初始化。所有金额为非负整数人民币元，字段使用 snake_case，成功响应直接返回对象，错误统一为下文结构。

## 1. 公共模型

Pydantic 模型由 B 放在 `backend/app/contracts.py`，TypeScript 类型由 A 放在 `frontend/src/types/contracts.ts`。业务输入不接收额外字段（Pydantic `extra="forbid"`），整数不接受布尔值或小数，去除首尾空白后校验字符串。

| 模型 | 字段与约束 |
| --- | --- |
| `Attraction` | `id` 唯一非空字符串；`city`、`name`、`description` 非空字符串；`category` 为自然/人文/休闲之一；`ticket_cny` 非负整数 |
| `GenerationRequest` | `city` 为支持的城市；`day_count` 为 1–5 整数；`preferences` 为类别数组，默认空且去重；`budget_cny` 非负整数必填；`mode` 必填 `rules` 或 `agent` |
| `CandidateDay` | `day` 整数；`attraction_ids` 字符串数组；额外的顺序、去重与城市检查由业务校验执行 |
| `AgentCandidate` | 只有 `days: CandidateDay[]`；模型不能指定费用、城市、来源或保存信息 |
| `PlanInput` | `GenerationRequest` 的全部字段 + `days: CandidateDay[]`；用于调整校验与确认保存 |
| `PlanDay` | `day`、`attractions: Attraction[]`、`subtotal_cny` |
| `PlanView` | `city`、`day_count`、`preferences`、`budget_cny`、`mode`、`status="draft"`、`days: PlanDay[]`、`total_cny`、`over_budget` 布尔值、`warnings: string[]` |
| `SavedTrip` | 与 `PlanView` 相同业务字段，`status="saved"`，额外增加 `trip_id`（服务端 UUID 字符串）、`created_at`（UTC ISO 8601）；保存完整景点和费用快照 |

分日数组长度必须与天数一致，`day` 依次为 1 至 `day_count`，每天最多两个景点，全行程去重。验证接口可以返回全空草案及警告，保存全空草案为 422。

`mode` 描述生成来源；手工修改仍保留原来源，它不是签名认证或“保存内容完全由 AI 生成”的证明。校验和保存响应根据提交的当前草案重算费用及警告，`status` 由服务端决定。

## 2. 端点与归属

基础路径 `/api`。客户端用 JSON；无分页、认证或网络搜索。

| 方法与路径 | 请求 | 成功响应 | 主责 |
| --- | --- | --- | --- |
| `GET /api/health` | 无 | 200 `{"status":"ok"}`，不检查或暴露模型密钥 | B |
| `GET /api/attractions` | 可选查询参数 `city`、`keyword`、`category` | 200 `{"items":Attraction[]}` | B |
| `POST /api/plans/generate` | `GenerationRequest` | 200 `PlanView`，不保存 | B 入口 |
| `POST /api/plans/validate` | `PlanInput` | 200 `PlanView`，不保存 | A |
| `POST /api/trips` | `PlanInput`，用户明确确认后发送 | 201 `SavedTrip` | A |
| `GET /api/trips` | 无 | 200 `{"items":SavedTrip[]}`，按创建时间倒序，时间相同时按 trip_id 排序 | A |
| `GET /api/trips/{trip_id}` | ID 字符串 | 200 `SavedTrip` | A |
| `DELETE /api/trips/{trip_id}` | ID 字符串 | 204 无响应体 | A |

景点查询：不传参数返回全部。传 `city`、`category` 为精确匹配，`keyword` 在名称和简介中作包含匹配，过滤条件同时生效，按 ID 升序返回；无结果为 200 空数组。非法类别为 422；不存在城市在 GET 查询中返回空，在生成/调整/保存时为 422。前端可从完整景点列表提取城市选项，无需新增城市接口。

生成时 B 先校验需求。规则模式调用 A 的规则候选服务；Agent 模式调用 B 的 Agent，再将原请求与候选分日合并。两者最终调用 A 的统一校验，返回相同 `PlanView`。不能在模型返回中直接采信金额。

## 3. 可直接对接的示例

以下名称和费用均为虚构示例。完整初始化数据应至少包含本文使用的两个 ID。

生成请求：

```json
{"city":"厦门","day_count":2,"preferences":["自然"],"budget_cny":50,"mode":"rules"}
```

标准草案（这里演示两个景点的结构，实际结果根据初始化数据确定）：

```json
{
  "city":"厦门",
  "day_count":2,
  "preferences":["自然"],
  "budget_cny":50,
  "mode":"rules",
  "status":"draft",
  "days":[
    {"day":1,"attractions":[{"id":"xm-001","city":"厦门","name":"示例海滨公园","category":"自然","description":"虚构课程景点。","ticket_cny":30}],"subtotal_cny":30},
    {"day":2,"attractions":[{"id":"xm-002","city":"厦门","name":"示例山林步道","category":"自然","description":"虚构课程景点。","ticket_cny":25}],"subtotal_cny":25}
  ],
  "total_cny":55,
  "over_budget":true,
  "warnings":["费用仅包含示例景点门票，不含交通、餐饮和住宿。","门票估算超过预算。"]
}
```

调整校验与保存使用同一 `PlanInput`，由前端把响应的景点对象转回 ID：

```json
{
  "city":"厦门","day_count":2,"preferences":["自然"],"budget_cny":50,"mode":"rules",
  "days":[{"day":1,"attraction_ids":["xm-001"]},{"day":2,"attraction_ids":["xm-002"]}]
}
```

保存响应为上述草案业务字段加 `trip_id`、`created_at`，并将 `status` 改为 `saved`。客户端不得发送价格、警告、状态、保存 ID 或时间，否则按额外字段拒绝。保存前端显示的估算不是跳过服务端校验的理由。

`warnings` 由服务端根据当前内容生成：始终说明门票范围；超预算、空白日期、没有偏好匹配或使用了非偏好类别时增加相应提示。文案可调整，逻辑语义固定，前端不靠匹配文案决定业务行为。

## 4. 错误约定

```json
{"code":"VALIDATION_ERROR","message":"第 2 天存在重复景点。"}
```

| HTTP | code | 适用情形 |
| --- | --- | --- |
| 422 | `VALIDATION_ERROR` | 输入类型、天数、预算、字段、城市、ID、日期结构、重复或全空保存不合法 |
| 404 | `NOT_FOUND` | 保存记录不存在，包括重复删除 |
| 503 | `AGENT_UNAVAILABLE` | 凭据未配置、服务失败或模型不支持所需能力 |
| 504 | `AGENT_TIMEOUT` | 总请求期限内未完成，停止调用 |
| 502 | `AGENT_INVALID_OUTPUT` | 输出不是有效候选、未调用查询工具、含未查询到 ID 或业务校验不通过 |
| 502 | `AGENT_LIMIT_EXCEEDED` | 工具或模型调用超过本版上限 |
| 500 | `STORAGE_ERROR` | 景点文件或行程文件损坏、读写失败；保留原数据 |

B 在应用入口统一映射 FastAPI 请求校验错误和模块业务错误；A 使用公共异常而不是再造另一套错误格式。异常细节可记录脱敏调试信息，响应不得包含密钥和原始请求头。

## 5. 文件格式

`attractions.json` 是 `Attraction[]`，初始化至少两个城市（厦门、泉州），每城 6 个虚构景点，三类各两个。`xm-001`、`xm-002` 使用上例的名称、类别和门票，其余 ID 使用 `xm-003…006`、`qz-001…006`，数据由 B 维护。完整性错误要报告，不能在启动时默默修补。

`trips.json` 是 `SavedTrip[]`。A 在保存时生成 UUID 和 UTC 时间，并保存完整景点与金额快照。文件缺失为空历史，损坏或读取失败返回 `STORAGE_ERROR`。前端查看历史直接展示快照，不通过当前景点数据重算；历史费用不因样例更新而改变。

多次主动保存同一内容可产生不同 ID；本版不做跨请求幂等键。前端禁用正在提交的保存按钮即可；客户端或模型不得自行指定记录 ID 来覆盖已有数据。
