# 成员一：行程生成基础框架

## 本次范围与现有代码

按本地《智能旅游行程规划与管理系统_项目方案.md》第七节，成员一主要承担需求、AI 规划助手及行程生成。本次只接通“需求 → 候选 → 校验 → 草案”，不实现完整网站或保存管理。

仓库 A/B 是代码模块分工，不能直接与原方案成员一/二等同。本次复用队友 `feat/b-planning` 的后端、景点、Agent 与规划组件；保留其原提交作者，新增成员一所需的规则与统一校验服务。公共模型沿用队友最新版的未知票价、每日说明与区域字段，不重写第二套 Agent 或资料服务。

当前可运行：健康检查、景点查询、规则生成、Agent 生成入口、草案校验。真实模型调用仍需本地配置并验证。前端只有队友的规划组件，没有整站工程；保存、历史、删除尚未实现，对应接口返回 404。实验一报告保留为当时的文档初稿，不据此补写原型实操结果。

## 最小结构

```text
backend/app/
  main.py                  FastAPI 入口、错误处理与路由注册（复用）
  contracts.py             公共需求、候选与草案模型（复用）
  config.py                本地配置（复用）
  catalog/                 只读景点服务（复用）
  planning/agent.py        一个 Agent、一个只读工具（复用）
  planning/service.py      选择规则或 Agent，然后统一校验（复用）
  itineraries/rules.py     新增：确定性规则候选
  itineraries/service.py   新增：编号、天数、重复、区域校验与费用重算
  itineraries/router.py    新增：草案校验接口，不保存
```

## 生成流程

```mermaid
flowchart TD
    A[填写汕头旅游需求] --> B[校验天数、偏好和预算]
    B --> C{生成方式}
    C -->|规则| D[按偏好和区域挑选本地景点]
    C -->|AI| E[模型发起一次只读景点查询]
    E --> F[模型返回分日编号和建议]
    D --> G[统一检查日期、编号、重复与每日限制]
    F --> G
    G --> H[按本地资料重算已知门票和预算提示]
    H --> I[返回草案，供用户检查]
    I --> J[用户调整后重新校验]
    J --> G
    E -->|未配置、超时或失败| K[明确报错，由用户主动选择规则]
```

Agent 最多两次模型调用、一次工具执行；不自动重试或静默回退，不写文件。只有真实观察到模型调用工具才可描述为真实 Agent 演示；离线替身测试不作该声明。方案接口依据 [LangChain 官方文档](https://docs.langchain.com/oss/python/langchain/agents)，接口测试采用 [FastAPI TestClient](https://fastapi.tiangolo.com/tutorial/testing/)。

## 启动与尝试

安装 Python 3.13 和 uv 后，在仓库根目录执行：

```powershell
cd backend
uv sync --locked
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/docs`，在 `POST /api/plans/generate` 点击 Try it out，输入：

```json
{"city":"汕头","day_count":2,"preferences":["自然"],"budget_cny":100,"mode":"rules"}
```

规则模式无需配置模型。返回 `status="draft"` 的分日草案，不保存数据。未知票价以 `has_unknown_prices=true` 提醒；已知费用未超预算但含未知价格时，`over_budget=null`，不能当成免费或预算满足。`POST /api/plans/validate` 可按 [接口契约](api.md) 提交调整后的分日 ID，费用由服务端重新计算。

如需真实 AI，在本地将 `backend/.env.example` 复制为 `.env`，自行填写 `LLM_MODEL`、`LLM_API_KEY`，服务需要时填写 `LLM_BASE_URL`；重启后把请求的 `mode` 改为 `agent`。本次不读取或提交真实凭据，未执行真实模型联调。服务不支持工具调用或配置缺失时会明确失败，用户可另发规则请求。

## 检查与后续

在 `backend` 目录执行 `uv run --locked pytest -q` 和 `uv run --locked ruff check app tests`。关键检查覆盖规则确定性、未知价格、非法编号/日期/重复/区域、Agent 候选共用校验及已有 Agent 调用限制。测试使用独立资料、临时目录和替身模型，不消耗模型配额。

2026-11-06 实测：使用 `uv sync --locked` 安装现有锁文件，Python 3.13.18；后端 `pytest -q` 共 43 项通过，`ruff check app tests` 与 `ruff format --check app tests` 通过。启动临时本机 Uvicorn 服务，通过真实 HTTP 检查健康接口、规则生成、草案重新校验及 Swagger 页面；未配置模型时 Agent 明确返回 503 `AGENT_UNAVAILABLE`。这次未执行真实模型调用或完整前端构建。

后续按需要接入 Vue 主工程、草案编辑与确认保存；本次不展开数据库、账户、地图、更多工具、RAG 或多 Agent。真实 Agent 的工具调用记录留待具备可用模型服务时验证。
