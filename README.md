# 智能旅游行程规划与管理系统

用户根据天数、兴趣和预算生成汕头行程草案，调整后确认保存。使用人工整理的真实汕头景点参考资料，提供规则推荐和一个带只读查询工具的单 Agent 推荐。

**当前状态：B 的后端基础、景点查询和单 Agent 模块已开发；完整应用仍待 A 的行程服务和前端工程接入。** Agent 已做离线替身测试，真实模型联调尚未完成。详见 [开发进度](docs/development.md)。

## 项目目标

优先完成软件工程实验一至七的需求分析、UML 建模和报告；开发按模块推进一个本地可运行原型。只覆盖汕头，使用人工整理的参考门票；资料并非实时，不提供预订、支付或导航。

| 部分 | 本版选型 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Element Plus |
| 后端 | Python、FastAPI、Pydantic 2 |
| Agent | LangChain `create_agent`、一个支持工具调用的模型、一个只读查询工具 |
| 数据 | 本地 JSON 景点参考资料及本地行程文件 |
| 建模与协作 | StarUML、Git、GitHub |

保留原方案的语言和主要框架，Agent 接口作有限简化。本版固定使用 JSON；PostgreSQL、SQLAlchemy 等原方案组件列为后续扩展，不在开发途中临时接入。

## A 与 B 的分工

**A 和 B 各自完整负责自己的业务模块，包括前后端、测试和相应说明。** 不将同一功能的每个小步骤分给两人轮流完成。

| 成员 | 模块及完整交付 | 主要文件范围 |
| --- | --- | --- |
| **A** | **行程编辑与管理**：草案展示与调整、统一校验和费用计算、规则推荐、确认保存、查看和删除；维护前端入口与公共前端类型 | `frontend/src/modules/trips/`、`backend/app/itineraries/`，前端入口及 `types/`、`api/client.ts` |
| **B** | **景点与智能规划**：需求输入、汕头景点参考资料、生成接口、单 Agent 工具调用及错误处理；维护后端入口与公共请求模型 | `frontend/src/modules/planning/`、`backend/app/catalog/`、`backend/app/planning/`、`backend/data/attractions.json`，后端入口及 `contracts.py`、`errors.py` |

A 负责前端工程初始化，B 负责后端工程初始化。两人各自维护工程入口、依赖与锁文件；需要对方新增入口注册时提交具体模块接口，由入口负责人一次接入。公共接口和数据契约已写在文档中，模块内部实现不必逐项请求对方确认。

报告分工：A 主责实验一、三、五与综合报告文件整理；B 主责实验二、四、六与综合演示检查。实验七各自整合自己模块的内容，由 A 汇总、B 检查一致性。详见 [实验交付](docs/experiments/README.md)。每次实验一人主整理，另一人检查。

## 开发前阅读

| 文档 | 唯一负责说明的内容 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | 编程 Agent 工作边界、阅读顺序和交付要求 |
| [需求与业务规则](docs/requirements.md) | 功能范围、参与者、输入约束和业务行为 |
| [架构与模块约定](docs/architecture.md) | 技术、目录、模块依赖及内部交接接口 |
| [接口和数据契约](docs/api.md) | 字段、示例、错误码及持久化格式 |
| [开发顺序和启动任务](docs/development.md) | 开工条件、阶段验收及 A/B 可直接交给 Agent 的任务 |
| [B 模块对接说明](docs/b-handoff.md) | 已实现内容、A 需要提供的服务与组件入口 |
| [协作方式](CONTRIBUTING.md) | 分支、提交、互审和契约变更方式 |
| [验收清单](docs/acceptance.md) | 需要验证的行为和证据 |

先阅读根规则，再读所负责目录的 `AGENTS.md`。文档中的候选目录和目标行为不表示已经实现。

## 开始开发

1. 各自获取仓库并检查实际分支、现有文件和本地改动。
2. 按 [开发顺序](docs/development.md) 完成最小工程与公共模型，再按模块并行开发。
3. 将对应 A/B 启动任务交给各自的编程 Agent；提交时说明检查结果和未完成项。

前端初始化时使用 `pnpm`，后端使用 `uv`，依赖和锁文件分别由 A、B 负责。Python 沿用 3.13；前端 Node 版本需满足所选 Vite 的要求。先验证并记录实际环境，再锁定依赖。

后端使用 Python 3.13 和已安装的 `uv`，在仓库根目录执行：

```powershell
cd backend
uv sync --locked
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开终端在 `backend` 目录执行 `uv run --locked pytest -q`。健康检查为 `http://127.0.0.1:8000/api/health`，景点资料为 `/api/attractions`。A 的行程服务合入前，生成接口返回 503 `SERVICE_NOT_READY`。前端主工程尚待 A 初始化；B 的规划组件已在隔离工程验证，不代表整个前端已经构建。

## 本地配置

后端读取 `backend/.env`，参考 [配置模板](backend/.env.example)；环境变量优先于文件。实现配置读取属于 B 的后端初始化任务。前端通过 Vite 代理访问 `/api`，不接触模型密钥。

完整行程服务接入后，无模型凭据时可使用规则推荐及行程管理。当前 Agent 适配 OpenAI 兼容的工具调用接口；服务地址、模型名称和密钥由使用者提供，具体兼容性需真实联调验证。真实密钥、运行记录、个人行程和本地配置均不提交。默认服务仅绑定本机，适用于单进程本地演示。
