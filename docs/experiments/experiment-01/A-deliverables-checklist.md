# 成员 A 实验一交付清单

核验日期：2026-11-05。当前交付为成员 A 初稿，未获成员 B 复核，不是完整小组终稿。

## A 任务与实际输出

本表路径相对本目录。

| 任务 | 状态 | 真实文件 | 核对结果 |
| --- | --- | --- | --- |
| 资料审查 | 已完成 | [A-source-review.md](A-source-review.md) | 逐份记录相关章节、未通读部分、规则、远程读取与新旧冲突 |
| A-01 详细目标 | 已完成 | [project-goals.md](project-goals.md) | 正文 598 个汉字（不计标题、数字和标点）；汕头单城、六功能闭环、原型边界；已纳入报告 4.2 |
| A-02 功能简述 | 已完成 | [function-specifications-A.md](function-specifications-A.md) | F02/F03 各一张正式纵向四字段表；已纳入报告 4.4 |
| A-03 Agent 需求设计 | 已完成 | [agent-flow-notes.md](agent-flow-notes.md) | 明确三种方式、只读工具、程序校验与计算、用户确认；不声称实现 |
| A-04 五章 Word 初稿 | 已完成初稿 | [软件工程实验一_汕头旅游系统_成员A初稿.docx](report/软件工程实验一_汕头旅游系统_成员A初稿.docx) | 可由 python-docx 解析及本机 Word 打开；实际导出 4 页，逐页检查无裁切、表格拆行或文字重叠；B 内容仍待补 |
| 方案对齐 | 已完成本次文档修改，待 B 复核 | [repository-alignment-notes.md](repository-alignment-notes.md) | 按用户最新指示同步 7 份现行规划文档，保留接口字段与代码主责 |
| 交付验收 | 已完成 | [A-deliverables-checklist.md](A-deliverables-checklist.md) | 本文件汇总实际检查和交接位置 |

## B 待交材料及报告位置

| 待交内容 | 插入位置 | 真实性与复核要求 |
| --- | --- | --- |
| UML 学习记录、StarUML 实际版本与操作截图 | 4.1 | 提供启动、新建项目、添加模型与图、保存及重新打开的真实记录；双方各自核实环境 |
| 功能结构图源文件及清晰导出图片 | 4.3，图 1 | 核对三组功能、六项编号与名称，保留可编辑源文件 |
| F01/F04/F05/F06 正式四字段表 | 4.4 对应占位表 | B 独立文件交付，由 A 合并；当前未找到其已完成文件 |
| 报告交叉复核 | 全文及抬头 | 11/07 整理可提交版，11/08 双方核对；个人信息由本人如实填写 |

## 实际检查与边界

- 五章顺序与教师实验一原文核对，六张表均为四行两列，其中两张 A 正式表、四张 B 占位表。
- 目标、功能表、报告与现行契约采用汕头单城；8–10 条为未来建议，不是已录入数据。
- 检查 Markdown 本地链接、API 示例 JSON 语法、差异空白；逐页查看 Word 导出图。标准渲染脚本因未安装 LibreOffice 不能运行，已使用本机 Word 导出 PDF 替代；核验文件位于仓库外 `.work/`。
- 没有初始化应用、修改 B 代码或安装 StarUML；没有应用测试、真实 Agent 调用或实操成功声明；没有插入教师或往届截图；身份字段留空。
- 仅列明暂存本次 14 个文件：本目录 7 个交付文件，加 README、requirements、api、acceptance、architecture、development、experiments/README。附件、提取文本、渲染结果、辅助脚本不入库。

## Git 交接

origin：`https://github.com/wjsm666/smart-travel-agent.git`。实际 clone 和 `ls-remote` 成功；未验证远程写权限。任务分支为 `docs/exp01-member-a`，本阶段作本地文档提交，提交号以 `git log -1` 为准。没有 push、PR 或 merge。B 尚未审核单城契约与本次报告，不能将用户的最新方案指示写成 B 已同意。
