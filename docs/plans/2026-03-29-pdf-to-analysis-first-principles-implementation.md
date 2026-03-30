# PDF 到分析结论第一性原理讲义 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 产出一份基于真实武汉大学案例数据的中文 `XeLaTeX` 教学讲义，并编译生成 PDF。

**Architecture:** 讲义本体使用 `ctexbook` 组织章节、表格和附录，插图使用 `TikZ/PGFPlots` 内嵌生成，案例数据直接引用当前工作树中的真实运行结果与配置参数。实现过程中只新增 `docs/` 下的文档与讲义文件，不修改业务代码。

**Tech Stack:** XeLaTeX, ctexbook, TikZ, PGFPlots, booktabs, longtable, tcolorbox

---

### Task 1: 固化设计与计划文档

**Files:**
- Create: `docs/plans/2026-03-29-pdf-to-analysis-first-principles-design.md`
- Create: `docs/plans/2026-03-29-pdf-to-analysis-first-principles-implementation.md`

**Step 1: 写入设计文档**

记录目标受众、章节结构、插图策略、案例数据边界和成功标准。

**Step 2: 写入实施计划**

明确讲义文件路径、所需包、插图来源、验证命令与交付物。

**Step 3: 验证文件已落盘**

Run: `ls docs/plans | rg 'pdf-to-analysis-first-principles'`

Expected: 能看到 design 和 implementation 两个文件名。

### Task 2: 创建讲义主文件骨架

**Files:**
- Create: `docs/lectures/pdf-to-analysis-first-principles-case.tex`

**Step 1: 写 LaTeX 文档前导**

包含类、页面设置、中文字体、颜色、定理框、目录和超链接配置。

**Step 2: 写标题页与目录**

标题要明确这是“第一性原理讲义”，副标题写明武汉大学案例与 Graphiti 本地部署背景。

**Step 3: 写统一样式环境**

创建 `definitionbox`、`casebox`、`takeawaybox` 等环境，供全书复用。

### Task 3: 编写原理章节

**Files:**
- Modify: `docs/lectures/pdf-to-analysis-first-principles-case.tex`

**Step 1: 写“问题定义”和“第一性原理”章节**

解释为什么 PDF 不是知识本身，只是原始载体。

**Step 2: 写“中间世界模型”章节**

解释为什么需要 chunk、ontology、graph 和 agent profile 这些中间表示。

**Step 3: 写“系统总览”章节**

给出完整链路，并定义每一层的输入、输出、约束。

### Task 4: 编写案例推导章节

**Files:**
- Modify: `docs/lectures/pdf-to-analysis-first-principles-case.tex`

**Step 1: 写 PDF 抽取与预处理章节**

结合 `FileParser`、`TextProcessor` 说明文本提取和规范化。

**Step 2: 写本体生成与图谱构建章节**

结合 `OntologyGenerator`、`GraphBuilderService`、`GraphitiMemoryService` 说明结构化过程。

**Step 3: 写 Agent 配置与仿真章节**

结合 `SimulationConfigGenerator` 和实际日志，说明 59 个 Agent 如何从实体世界中派生。

**Step 4: 写报告生成章节**

结合 `ReportAgent`、`zep_tools`、采访与检索，说明“分析报告”并非直接总结。

### Task 5: 写真实实验结果与调优章节

**Files:**
- Modify: `docs/lectures/pdf-to-analysis-first-principles-case.tex`

**Step 1: 写真实配置表**

列出模型、图谱后端、embedding、chunk、batch size、端口等信息。

**Step 2: 写真实运行结果表**

列出建图、准备、仿真、报告耗时和规模指标。

**Step 3: 写瓶颈分析**

解释为什么本次速度慢在远端 LLM 链路与检索策略，而不是本机纯算力。

**Step 4: 写参数权衡**

解释 `6500/650` 为什么更快但不一定更优，并给出下一步实验建议。

### Task 6: 添加教学插图

**Files:**
- Modify: `docs/lectures/pdf-to-analysis-first-principles-case.tex`

**Step 1: 添加全链路流程图**

用 TikZ 画出 `PDF -> Text -> Chunk -> Ontology -> Graph -> Agents -> Simulation -> Report`。

**Step 2: 添加时间分布图**

用 PGFPlots 画本次运行各阶段耗时。

**Step 3: 添加权衡示意图**

画出 chunk 粒度、速度和检索命中之间的关系。

### Task 7: 编译与修正

**Files:**
- Modify: `docs/lectures/pdf-to-analysis-first-principles-case.tex`
- Output: `docs/lectures/pdf-to-analysis-first-principles-case.pdf`

**Step 1: 首次编译**

Run: `cd docs/lectures && xelatex -interaction=nonstopmode pdf-to-analysis-first-principles-case.tex`

Expected: 成功生成 PDF，若有交叉引用警告可继续第二遍。

**Step 2: 第二次编译**

Run: `cd docs/lectures && xelatex -interaction=nonstopmode pdf-to-analysis-first-principles-case.tex`

Expected: 目录、页码、引用稳定。

**Step 3: 检查输出文件**

Run: `ls -lh docs/lectures/pdf-to-analysis-first-principles-case.pdf`

Expected: PDF 文件存在且大小正常。

### Task 8: 最终核验

**Files:**
- Verify: `docs/lectures/pdf-to-analysis-first-principles-case.tex`
- Verify: `docs/lectures/pdf-to-analysis-first-principles-case.pdf`

**Step 1: 检查关键内容是否覆盖**

确认正文含有：
- 第一性原理解释
- 真实案例参数
- 真实运行数据
- 速度与质量瓶颈
- 插图与附录

**Step 2: 记录验证命令**

Run:
- `xelatex --version | head -n 1`
- `pdfinfo docs/lectures/pdf-to-analysis-first-principles-case.pdf | head`

Expected: 能确认编译器和 PDF 基本元信息。

**Step 3: 汇报交付**

说明生成的 `.tex` 和 `.pdf` 路径，并简述讲义覆盖范围与验证结果。
