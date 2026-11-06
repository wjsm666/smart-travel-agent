# 架构与模块约定

## 1. 技术基线

Vue 3、TypeScript、Vite、Element Plus 构成前端，使用浏览器 `fetch` 封装 HTTP；Python 3.13、FastAPI、Pydantic 2 构成后端。LangChain `create_agent` 用于一个小型规划助手，模型适配依赖由 B 根据实际可用服务验证后添加。它替代手写 LangGraph 编排；不增加第二个 Agent 框架。

前端使用 `pnpm`，后端使用 `uv`，沿用原方案的包管理方向。A/B 初始化时验证兼容版本并提交各自锁文件。Node 环境满足所选 Vite 的要求，初始化时再次核对。B 的后端已初始化，A 的规则与校验基础服务已接入，前端主工程和保存管理待做。

本版数据为 UTF-8 JSON，PostgreSQL、SQLAlchemy、Alembic、Pinia、Docker、CI 暂不启用；不另换语言、UI 框架或数据库。

参考：[Vite 环境要求](https://vite.dev/guide/)、[LangChain Agent](https://docs.langchain.com/oss/python/langchain/agents)、[调用次数限制](https://docs.langchain.com/oss/python/langchain/middleware/built-in)。

## 2. 目标目录和负责人

以下为目标结构；B 的景点和规划部分已开发，A 的规则、统一校验和校验路由已接入。前端主工程与保存管理仍是后续目标。不要提交无意义空模块。

```text
frontend/                          A 初始化工程与依赖
  src/App.vue                      A 维护页面入口
  src/api/client.ts                A 统一请求和错误处理
  src/types/contracts.ts           A 按 api.md 实现公共类型
  src/modules/planning/            B 需求表单、景点浏览、生成操作
  src/modules/trips/               A 草案编辑、费用显示、历史管理
backend/                           B 初始化工程与依赖
  app/main.py                      B 初始化应用、异常映射和路由注册
  app/contracts.py                 B 按 api.md 实现公共 Pydantic 模型
  app/errors.py                    B 公共业务异常与 HTTP 映射
  app/config.py                    B 本地配置及环境变量读取
  app/catalog/                     B 景点读取、查询、lookup
  app/planning/                    B 生成入口、模型与工具调用
  app/itineraries/                 A 规则推荐、统一校验、费用、保存
  data/attractions.json            B 整理汕头景点参考资料，可提交
  data/trips.json                  A 本地保存结果，忽略不提交
  tests/test_catalog_planning*     B 的测试
  tests/test_itineraries*          A 的测试
docs/experiments/                  按实验主责整理
```

公共模型、错误映射不依赖业务模块；业务层不相互复制代码。目录可以按实际实现略作内部组织，公开入口与约定保持一致。

## 3. 后端内部交接

以下服务签名已接通，模型结构以 `api.md` 为准。行程路由当前只提供校验，保存管理尚未实现。除 Agent 入口外均可为普通同步函数。

| 提供者 | 模块出口 | 使用者与责任 |
| --- | --- | --- |
| B | `app.contracts` 提供 `Attraction`、`GenerationRequest`、`PlanInput`、`PlanView`、`SavedTrip`、`AgentCandidate` | A/B 共用，不各自重定义 |
| B | `app.catalog.service.list_attractions(city=None, keyword=None, category=None) -> list[Attraction]` | 页面查询、工具与规则推荐共用；过滤语义见 API |
| B | `app.catalog.service.get_catalog() -> dict[str, Attraction]` | A 校验 ID、城市和费用；B 初始化时一并提供 |
| A | `app.itineraries.service.validate_and_enrich(draft: PlanInput) -> PlanView` | 普通编辑、规则/Agent 结果和保存共同使用；不写文件 |
| A | `app.itineraries.rules.make_rule_candidate(request: GenerationRequest) -> PlanInput` | B 的规则模式入口使用；生成确定草案，不写文件 |
| B | `app.planning.agent.generate_candidate(request: GenerationRequest) -> AgentCandidate` | 内部可异步；返回分日 ID 和可选说明，B 合并原请求后调用 A 的统一校验 |
| A | `app.itineraries.router.router` | 应用入口已注册校验路由；保存、列表、详情、删除待实现 |

`GET /api/attractions`、`GET /api/health` 和 `POST /api/plans/generate` 由 B 提供；其他行程接口由 A 提供。B 的生成入口把两种模式的候选都交给 A 校验：用户输入非法为 422，Agent 候选非法转换成 502，不直接返回原始模型结果。

依赖方向：`catalog → contracts/config`；`itineraries → catalog/contracts/errors/config`；`planning → catalog/itineraries/contracts/errors/config`；`main → 各路由`。不允许 `itineraries` 反过来依赖 `planning`，避免循环。

初始化完成后公共模型、景点服务和配置可同时供双方使用。Agent 可先用测试替身的统一校验验证生成逻辑，待 A 模块合入后接入；替身只留在测试中，不另写生产校验服务。

## 4. 前端组件交接

规划模块提供 `PlanningPanel.vue`，B 维护。它自行使用公共客户端调用景点和生成接口，通过 `plan-generated` 事件向父页面发出 `PlanView`，通过 `catalog-loaded` 事件发出完整汕头景点数组。A 的应用入口接收事件，向行程模块传入数据。

公共客户端对模块提供 `requestJson<T>(path: string, init?: RequestInit): Promise<T>`：`path` 使用 `/api` 开头的相对路径；响应非 2xx 时拒绝 Promise，错误消息取后端的可读 `message`，无法解析时使用通用提示。调用方为 JSON 请求自行设置 `Content-Type` 和序列化请求体。该签名用于成员间的内部模块交接，不改变 HTTP 契约。

行程模块提供 `TripWorkspace.vue`，A 维护。props 为 `draft: PlanView | null`、`attractions: Attraction[]`；内部完成编辑、校验和保存请求、历史列表与删除。父页面收到新草案时，若有未保存编辑，提示用户确认替换，避免覆盖。

同一新草案对象以新的引用传入。行程模块复制为本地编辑状态，不直接修改 props；调用 `PlanInput` 接口时从每日 `attractions` 提取 ID。编辑响应只应用于对应草案版本，过期响应丢弃或取消请求。

规划页面使用中文“AI 推荐”“规则推荐”和费用范围说明，普通界面无需展示框架名或内部日志。

## 5. 本地存储和服务边界

样例与行程路径由 `config.py` 解析，环境变量优先于 `backend/.env`；相对路径基于 `backend/`，不随启动目录变化。前端 Vite 代理 `/api`，前端密钥始终为空。

后端仅绑定 `127.0.0.1`，一个工作进程。JSON 存储适用于本地单用户；A 使用单进程锁包围读改写与临时文件原子替换。损坏文件返回存储错误而不是重置；无文件返回空历史。生成与校验函数无保存副作用。

## 6. Agent 的最小实现

B 通过 LangChain 创建一个 Agent，只提供 `search_attractions(city)` 工具，工具必须验证参数为汕头，然后调用同一个景点服务，返回景点、区域、参考时长和已知票价。偏好在生成时处理，避免多次查询与复杂工具选择。

工具返回可用 ID 集合；模型最终消息输出普通 JSON，结构为 `AgentCandidate`。以 JSON 解析和 Pydantic 校验最终文本，不用模型反复修复结果。避免采用额外的“结构化输出工具”而意外增加工具种类及调用次数；若采用模型原生结构化输出，也需验证不增加额外调用。

通过实际支持的 middleware 或等价应用控制，每个请求最多 2 次模型调用、1 次工具执行，关闭 SDK 隐式自动重试。并发工具批次也计入限制，不允许一批偷偷执行多个；未发生实际工具查询的结果不标为 Agent 成功。总超时由 `AGENT_TIMEOUT_SECONDS` 决定（模板默认 30 秒），包括两次调用；超时后终止，不继续后台生成。

Agent 输出除常规业务规则外，还需检查 ID 均在本次工具返回集合中。没有凭据或调用失败时返回 API 指定错误；规则模式不实例化模型。只记录供开发检查的工具名、调用数和脱敏结果，不返回或记录密钥、请求头及私有用户信息。
