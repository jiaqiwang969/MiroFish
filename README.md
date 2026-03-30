# MiroFish

MiroFish 是一个把“现实材料 -> 图谱 -> 多智能体仿真 -> 报告/互动”串起来的开发仓库。
当前仓库的主开发路径已经切到本地优先模式：`Graphiti sidecar + Kuzu + bge-m3 + Flask backend + Vue frontend`。

这份 README 面向刚接手项目、需要尽快本地跑起来并继续开发的内部同学。读完后你应该能回答 4 个问题：

- 这个仓库当前默认跑法是什么
- 前后端和本地图谱服务怎么一起启动
- 从上传材料到报告生成的链路经过哪些模块
- 如果要继续开发，第一站应该看哪些文件

## 一句话理解当前版本

- 默认图谱后端：`graphiti`
- 默认启动命令：`npm run dev:graphiti`
- 前端端口：`3000`
- 后端端口：`5001`
- Graphiti sidecar 端口：`8011`
- LLM 接口：统一走 OpenAI-compatible
- `Zep Cloud` 仍保留兼容路径，但已经不是本地开发主路径

## 当前能力边界

当前仓库已经打通这些能力：

- 上传 `PDF / MD / TXT / Markdown`，抽取文本并生成 ontology
- 构建图谱并把图谱写入本地 Graphiti sidecar
- 从图谱中过滤实体，生成 OASIS 所需 profile 和 simulation config
- 启动 Twitter/Reddit 风格的 OASIS 仿真
- 生成报告，并在报告阶段继续做图谱检索与访谈
- 直接从微信数据库研究产物创建项目，跳过通用 ontology 生成

需要明确的边界：

- 图谱和 embedding 可以本地运行，但如果 `LLM_BASE_URL` 指向远端，大模型推理仍然依赖外网
- `Zep` 相关代码仍然保留，主要用于兼容旧路径和少量工具封装，不应再作为默认开发入口
- 首次启动 Graphiti sidecar 会下载 `BAAI/bge-m3`，会慢，而且要占用几 GB 磁盘

## 10 分钟本地启动

### 1. 环境要求

建议使用以下环境：

- `Node.js >= 18`
- `Python 3.11` 或 `Python 3.12`
- `uv` 最新版

虽然部分依赖声明是 `>=3.11`，但从本仓库这套 AI 依赖组合看，日常开发仍建议优先使用 `3.11/3.12`。

检查命令：

```bash
node -v
npm -v
python3.11 --version
uv --version
```

### 2. 配置环境变量

根目录：

```bash
cp .env.example .env
```

Graphiti sidecar：

```bash
cp graphiti_service/.env.example graphiti_service/.env
```

根目录 `.env` 最少需要这些变量：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_MODEL_NAME=gpt-5.4-mini

GRAPH_BACKEND=graphiti
GRAPHITI_SERVICE_URL=http://127.0.0.1:8011
GRAPHITI_REQUEST_TIMEOUT_SECONDS=300
GRAPHITI_BUILD_BATCH_SIZE=2
```

`graphiti_service/.env` 最少需要这些变量：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_MODEL_NAME=gpt-5.4-mini

GRAPHITI_DB_PATH=./data/graphiti.kuzu
GRAPHITI_EMBEDDING_MODEL=BAAI/bge-m3
GRAPHITI_HOST=127.0.0.1
GRAPHITI_PORT=8011
GRAPHITI_PREWARM=true
GRAPHITI_CHECKPOINT_AFTER_WRITE=true
GRAPHITI_RECOVER_STALE_WAL=true
```

说明：

- 根目录 `.env` 给 `backend/` 用
- `graphiti_service/.env` 优先级高于根目录 `.env`
- 这两个文件都已经被 `.gitignore` 忽略，不会被提交

### 3. 安装依赖

一条命令安装全部依赖：

```bash
npm run setup:all
```

它会做三件事：

- 安装根目录 Node 依赖
- 安装 `frontend/` 依赖
- 用 `uv` 安装 `backend/` 和 `graphiti_service/` 依赖

如果要分开装：

```bash
npm run setup
npm run setup:backend
npm run setup:graphiti
```

### 4. 启动服务

推荐启动方式：

```bash
npm run dev:graphiti
```

这会同时拉起：

- `graphiti_service/app.py`
- `backend/run.py`
- `frontend` Vite dev server

启动后访问：

- 前端：`http://127.0.0.1:3000`
- 后端健康检查：`http://127.0.0.1:5001/health`
- Graphiti sidecar 健康检查：`http://127.0.0.1:8011/health`

如果你要分终端启动：

```bash
npm run graphiti
npm run backend
npm run frontend
```

### 5. 快速自检

后端：

```bash
curl http://127.0.0.1:5001/health
```

Graphiti sidecar：

```bash
curl http://127.0.0.1:8011/health
```

如果两个都返回 `status: ok`，前端页面也能打开，就说明开发环境基本正常。

## 当前推荐开发模式

### 主路径：Graphiti 本地模式

当前默认模式是：

- 后端在 [backend/app/config.py](backend/app/config.py) 里读取 `GRAPH_BACKEND=graphiti`
- 图谱抽象层走 [backend/app/services/graph_backend.py](backend/app/services/graph_backend.py)
- HTTP 客户端走 [backend/app/services/graphiti_sidecar_client.py](backend/app/services/graphiti_sidecar_client.py)
- Graphiti 本体服务在 [graphiti_service/app.py](graphiti_service/app.py) 和 [graphiti_service/service.py](graphiti_service/service.py)
- 本地图谱数据默认落到 `graphiti_service/data/graphiti.kuzu`

这套模式的目标是把“图谱写入、图谱查询、embedding、持久化”尽量收回本地控制。

### 兼容路径：Zep 模式

如果必须回退到旧路径，可以在根目录 `.env` 里改成：

```env
GRAPH_BACKEND=zep
ZEP_API_KEY=your_zep_api_key
```

但当前不建议把新开发继续堆在这条路径上。

## 项目结构总览

```text
MiroFish/
├── backend/                 Flask 后端，处理图谱、仿真、报告 API
├── frontend/                Vue 3 + Vite 前端
├── graphiti_service/        本地图谱 sidecar，Graphiti + Kuzu
├── scripts/                 仓库级辅助脚本
├── docs/                    研究文档、计划文档
├── static/                  README/官网使用的静态资源
└── .env.example             根目录环境变量模板
```

重点看这几个目录：

### `frontend/`

- `src/views/Home.vue`
  首页上传入口，收集文件和 `simulationRequirement`
- `src/views/MainView.vue`
  主流程页面，负责从图谱构建进入环境准备
- `src/views/SimulationView.vue`
  仿真概览页
- `src/views/SimulationRunView.vue`
  仿真运行页
- `src/views/ReportView.vue`
  报告查看页
- `src/views/InteractionView.vue`
  深度互动页
- `src/api/*.js`
  对后端 API 的封装

### `backend/`

- `app/api/graph.py`
  项目创建、ontology 生成、图谱构建、图谱读取
- `app/api/simulation.py`
  仿真创建、准备、启动、停止、状态和访谈
- `app/api/report.py`
  报告生成、报告查询、日志流和工具接口
- `app/services/graph_backend.py`
  图谱后端抽象层，当前默认走 Graphiti
- `app/services/graph_builder.py`
  文本切块后写入图谱的核心逻辑
- `app/services/zep_entity_reader.py`
  从图谱后端读取并过滤实体
- `app/services/oasis_profile_generator.py`
  把实体转成 OASIS 需要的人设 profile
- `app/services/simulation_config_generator.py`
  生成仿真配置
- `app/services/simulation_runner.py`
  启动和管理仿真进程
- `app/services/report_agent.py`
  报告 Agent 主逻辑
- `app/services/zep_tools.py`
  报告阶段的检索和统计工具

### `graphiti_service/`

- `app.py`
  sidecar Flask 入口
- `service.py`
  Graphiti/Kuzu 的核心封装
- `config.py`
  sidecar 配置加载和校验
- `tests/test_service.py`
  sidecar 逻辑测试
- `tests/test_app.py`
  sidecar 路由测试

### `docs/`

- `docs/lectures/wechat-db-to-social-simulation-first-principles.tex`
  微信数据库到社交仿真的第一性原理讲义
- `docs/plans/`
  计划文档和实施记录

## 从页面到后端的核心调用链

新同学接手时，先把这条链看明白。

### 1. 上传现实材料

前端入口在：

- `frontend/src/views/Home.vue`
- `frontend/src/store/pendingUpload.js`

用户上传文件并输入 `simulationRequirement` 后，前端把待上传状态暂存，然后跳到流程页。

### 2. 创建项目并生成 ontology

流程页在：

- `frontend/src/views/MainView.vue`
- `frontend/src/components/Step1GraphBuild.vue`

这里会调用：

- `POST /api/graph/ontology/generate`

后端入口在：

- `backend/app/api/graph.py`

这一步主要做：

- 解析上传文件
- 抽取文本
- 调用 LLM 生成 ontology
- 创建 project

### 3. 构建图谱

继续在 `Step1GraphBuild` 里调用：

- `POST /api/graph/build`

后端会进入：

- `backend/app/services/graph_builder.py`
- `backend/app/services/graph_backend.py`
- `backend/app/services/graphiti_sidecar_client.py`

如果当前是 `graphiti` 模式，后端会通过 HTTP 把图谱写到本地 sidecar：

- `POST /graphs`
- `POST /graphs/<graph_id>/ontology`
- `POST /graphs/<graph_id>/episodes`

sidecar 则在：

- `graphiti_service/app.py`
- `graphiti_service/service.py`

负责：

- 初始化 Graphiti
- 绑定 Kuzu
- 生成 embedding
- 写入 episodes
- 建立节点和边

### 4. 环境准备

前端进入：

- `frontend/src/components/Step2EnvSetup.vue`

主要接口：

- `POST /api/simulation/create`
- `POST /api/simulation/prepare`

后端主要模块：

- `backend/app/api/simulation.py`
- `backend/app/services/simulation_manager.py`
- `backend/app/services/simulation_config_generator.py`
- `backend/app/services/zep_entity_reader.py`
- `backend/app/services/oasis_profile_generator.py`

这里会做：

- 从图谱里读实体
- 过滤出适合仿真的实体
- 生成 Twitter/Reddit 两套 profile
- 生成 simulation config

### 5. 启动仿真

主要接口：

- `POST /api/simulation/start`

主要模块：

- `backend/app/services/simulation_runner.py`
- `backend/scripts/run_parallel_simulation.py`
- `backend/scripts/run_twitter_simulation.py`
- `backend/scripts/run_reddit_simulation.py`

这一步会把模拟目录、配置文件、日志文件、平台 DB 一起准备好，并启动 OASIS 环境。

### 6. 生成报告和深度互动

报告接口：

- `POST /api/report/generate`
- `GET /api/report/<report_id>`
- `POST /api/report/chat`

对应模块：

- `backend/app/api/report.py`
- `backend/app/services/report_agent.py`
- `backend/app/services/zep_tools.py`

这里的职责是：

- 汇总仿真结果
- 做图谱检索和统计
- 生成最终 markdown 报告
- 支持继续提问、查看日志、访谈 agent

## 微信数据库本地链路

这一版已经额外接入了微信数据库研究产物的快速建项路径。

入口在：

- `POST /api/graph/ontology/wechat`

关键文件：

- `backend/app/api/graph.py`
- `backend/app/services/wechat_ontology.py`
- `backend/app/services/wechat_db_ingester.py`
- `backend/app/services/oasis_profile_generator.py`

这条链路的思路是：

- 不再让 LLM 从零生成 ontology
- 直接使用预定义的微信 ontology
- 把微信数据库研究产物转换成 graph-ready episodes
- 再进入 MiroFish 原有的图谱构建、环境准备、仿真、报告链路

适合处理“你已经有一份微信 DB 逆向研究产物目录，希望直接建项”的场景。

## 常用开发入口

### 想改页面流程

先看：

- `frontend/src/router/index.js`
- `frontend/src/views/Home.vue`
- `frontend/src/views/MainView.vue`
- `frontend/src/components/Step1GraphBuild.vue`
- `frontend/src/components/Step2EnvSetup.vue`
- `frontend/src/components/Step3Simulation.vue`
- `frontend/src/components/Step4Report.vue`
- `frontend/src/components/Step5Interaction.vue`

### 想改接口协议

先看：

- `frontend/src/api/graph.js`
- `frontend/src/api/simulation.js`
- `frontend/src/api/report.js`
- `backend/app/api/graph.py`
- `backend/app/api/simulation.py`
- `backend/app/api/report.py`

### 想改图谱后端

先看：

- `backend/app/config.py`
- `backend/app/services/graph_backend.py`
- `backend/app/services/graphiti_sidecar_client.py`
- `backend/app/services/graph_builder.py`
- `graphiti_service/config.py`
- `graphiti_service/service.py`

### 想改仿真准备和 profile 生成

先看：

- `backend/app/services/zep_entity_reader.py`
- `backend/app/services/oasis_profile_generator.py`
- `backend/app/services/simulation_config_generator.py`
- `backend/app/services/simulation_manager.py`

### 想改报告 Agent

先看：

- `backend/app/services/report_agent.py`
- `backend/app/services/zep_tools.py`
- `backend/app/api/report.py`

## 测试与验证命令

仓库里目前最关键的几组验证命令：

```bash
node scripts/test_graphiti_dev_scripts.mjs
cd backend && uv run pytest tests -q
cd graphiti_service && uv run pytest tests/test_service.py tests/test_app.py -q
```

说明：

- 第一条检查根目录 `package.json` 里和 Graphiti 本地模式相关的脚本是否还在
- 第二条跑 backend 的图谱后端、API、报告工具兼容测试
- 第三条跑 Graphiti sidecar 的服务层和路由层测试

如果你只改前端页面，未必需要每次都跑满所有测试；但如果你改了图谱后端、配置项、接口契约，建议三条都跑。

## 常见问题

### 1. 后端启动报配置错误

优先检查：

- 根目录 `.env` 是否存在
- `LLM_API_KEY` 是否配置
- `GRAPH_BACKEND=graphiti` 时是否配置了 `GRAPHITI_SERVICE_URL`

### 2. Graphiti sidecar 首次启动很慢

这是正常现象。首次会下载并缓存 `BAAI/bge-m3`，缓存体积大约几 GB。下载完成后，后续重启会快很多。

### 3. Kuzu WAL 导致启动失败

默认已经打开：

- `GRAPHITI_CHECKPOINT_AFTER_WRITE=true`
- `GRAPHITI_RECOVER_STALE_WAL=true`

含义：

- 每次成功写入后主动做 `CHECKPOINT`
- 遇到旧 WAL 时自动备份成 `*.stale-时间戳`

排查时优先看：

- `graphiti_service/data/`

### 4. 端口冲突

默认端口：

- `3000` 前端
- `5001` 后端
- `8011` Graphiti sidecar

可用下面命令检查：

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:5001 -sTCP:LISTEN
lsof -nP -iTCP:8011 -sTCP:LISTEN
```

### 5. 想做真正纯离线

当前图谱和 embedding 已经可以本地化，但 LLM 是否纯离线取决于 `LLM_BASE_URL` 指向哪里。
如果你要完全离线，需要再接一个本地 OpenAI-compatible 推理服务。

## 建议阅读顺序

如果你是第一次接手，建议按这个顺序看：

1. 先读这份 `README.md`
2. 看 `.env.example`
3. 看 `graphiti_service/.env.example`
4. 看 `frontend/src/router/index.js`
5. 看 `frontend/src/views/Home.vue` 和 `frontend/src/views/MainView.vue`
6. 看 `backend/app/api/graph.py`
7. 看 `backend/app/api/simulation.py`
8. 看 `backend/app/api/report.py`
9. 看 `backend/app/services/graph_backend.py` 和 `graphiti_service/service.py`
10. 最后再看 `docs/lectures/wechat-db-to-social-simulation-first-principles.tex`

## 附：仍然保留的旧信息

如果你只是想快速看效果，可以继续访问历史演示资源：

- 在线 Demo：<https://666ghj.github.io/mirofish-demo/>
- 武大舆情演示视频：<https://www.bilibili.com/video/BV1VYBsBHEMY/>
- 红楼梦结局推演视频：<https://www.bilibili.com/video/BV1cPk3BBExq>

但对于继续开发的人来说，优先级应该始终是：

- 先把本地 `dev:graphiti` 跑起来
- 再顺着 `frontend -> backend/api -> backend/services -> graphiti_service` 看调用链
