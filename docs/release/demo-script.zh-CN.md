# Mini ChatChat 演示脚本

这份脚本适合 5 到 8 分钟的作品集、GitHub 或面试演示。

演示过程中不要展示 `.env`、API key、cookie、JSON Web Token (JWT)、refresh token、OAuth secret、私人邮箱收件箱或真实用户数据。

## 录屏素材

当前已有实际录屏文件：

```text
docs/release/media/github-readme/mini-chatchat-demo.mov
```

录屏摘要：

- 时长：约 103 秒
- 格式：QuickTime MOV
- 视频/音频：H.264 视频 + AAC 音频
- 分辨率：4096 x 2164
- 文件大小：约 50 MB

当前录屏适合作为 GitHub README 的短展示素材，但没有完整覆盖下面 5 到 8 分钟脚本的全部流程。缺失或只部分覆盖的内容包括：完整 KB 上传与索引、临时文件问答、Agent 工具执行、Tool Center 讲解、Docker 终端证明和备份/恢复说明。

## 准备

操作：

```bash
cp .env.production.example .env.production
mkdir -p runtime/prod
docker compose -f docker-compose.prod.yml up --build -d
curl http://127.0.0.1/api/health
```

讲解：

Mini ChatChat 可以通过 Docker Compose 运行。React 前端由 nginx 提供静态资源，FastAPI 后端通过 `/api` 暴露。

预期结果：

- 前端可通过 `http://127.0.0.1/` 打开
- `/api/health` 返回 `ok`
- backend 和 frontend 容器都是 healthy

面试讲解点：

这说明项目不是只能在本地 dev server 运行，而是具备可复现的私有演示运行形态。

失败备用方案：

如果 Docker 不可用，可以本地启动后端和前端：

```bash
cd backend
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend-react
npm run dev -- --host 127.0.0.1 --port 5173
```

## 1. 项目定位

操作：

打开 Chat 工作区。

讲解：

Mini ChatChat 是一个受 LangChain-Chatchat 核心体验启发的全栈 AI 知识工作台，支持本地知识库 RAG、联网搜索、临时文件问答、带来源的回答、Agent 工具调用、MCP 集成、用户认证、用户数据隔离和 Docker 部署。

预期结果：

- Chat 工作区可见
- 产品 Shell 中能看到版本和当前运行状态

面试讲解点：

强调检索链路是可检查的，不是全部隐藏在 LangChain 后面。

失败备用方案：

如果产品 Shell 加载较慢，可以先展示 `curl http://127.0.0.1/api/health`，再刷新浏览器。

## 2. Guest 模式

操作：

不登录直接使用应用。

讲解：

游客可以使用基础聊天、联网搜索和临时文件问答。Knowledge 管理、Agent 工具、MCP、filesystem tool、SQLite tool 和 Developer Mode 等敏感能力由权限控制。

预期结果：

- Chat 可访问
- Search 模式可见
- 受限能力会提示需要登录

面试讲解点：

这体现了渐进式权限控制，而不是简单隐藏未完成能力。

失败备用方案：

如果游客权限不明显，打开 Knowledge 或 Agent，展示登录提示。

## 3. 注册与登录

操作：

打开 `/register` 或 `/login`，使用准备好的 demo 账户。

讲解：

应用支持邮箱注册、登录、HttpOnly refresh cookie、refresh rotation、Session 管理和用户数据隔离。

预期结果：

- 账户菜单显示已登录用户
- Account 页面显示个人资料和 Session
- 浏览器 JavaScript 不能直接读取 refresh token

面试讲解点：

说明认证已经接入用户隔离的会话、知识库、文件和 Session。

失败备用方案：

如果 demo 账户已存在，直接登录，不要重复创建无用账户。

## 4. Onboarding

操作：

展示首次引导，或从当前状态说明它的作用。

讲解：

Onboarding 用普通用户能理解的方式介绍本地 KB、临时文件、搜索和 Agent 模式，不强迫用户进入开发者设置。

预期结果：

- 用户能理解不同模式的用途
- Onboarding 可以完成或跳过

面试讲解点：

这属于产品体验，不只是后端功能。

失败备用方案：

如果 Onboarding 已完成，说明它由用户偏好控制。

## 5. 创建知识库

操作：

打开 Knowledge，选择或创建 demo KB，并查看文档区域。

讲解：

Knowledge 工作区管理本地 RAG 的文档生命周期，包括上传、索引、查看、重建、删除、导入和导出。

预期结果：

- 当前 KB 可见
- 文档列表或空上传状态可见

面试讲解点：

说明 KB metadata 存在 SQLite，向量存储在用户 scope 下的 FAISS 文件中。

失败备用方案：

如果不需要创建 KB，直接使用 default KB 继续上传。

## 6. 上传文档

操作：

上传一个不包含私人数据的小 `.txt` 或 `.md` 文件。

讲解：

后端会解析文档、切分 chunk、保存 metadata，并更新 FAISS index。

预期结果：

- 上传状态成功
- 文档行显示状态和 chunk metadata

面试讲解点：

说明支持 `.txt`、`.pdf`、`.docx`、`.md` 和 `.csv`。

失败备用方案：

如果因为未登录导致上传失败，先登录再重试。如果解析失败，换一个简单文本文件。

## 7. 本地知识库问答

操作：

切换到本地知识库模式，询问上传文档相关问题。

讲解：

本地 KB 问答通过 FAISS + BM25 Hybrid Search 检索上下文，可选 rerank，去重 chunk，限制 prompt context，然后流式生成回答。

预期结果：

- 用户消息出现
- assistant 流式回答
- 回答结束后可以查看来源

面试讲解点：

这是主 RAG 链路：

```text
Question -> Retrieve -> Context -> Prompt -> LLM -> Answer
```

失败备用方案：

如果模型 provider 没配置，可以展示 return-direct 检索或来源/debug 结果。

## 8. Sources

操作：

从 assistant 回答中打开 Sources 面板。

讲解：

Sources 不只是临时 UI 状态。assistant message 的来源 metadata 会持久化，历史会话恢复时也能展示对应来源。

预期结果：

- Source card 显示文件名、chunk preview 和可用的检索分数

面试讲解点：

这有助于审计回答来源，也能降低幻觉排查成本。

失败备用方案：

如果历史消息没有保存来源，展示明确的 empty state，而不是假装有来源。

## 9. 联网搜索

操作：

切换到 Search 模式，询问一个公开信息问题。

讲解：

Search 模式发送 `mode: "search_engine"`，不会传 KB name。它适合公开信息问题；精确当前时间更适合通过 Agent 的 current_time 工具演示。

预期结果：

- assistant 使用搜索模式
- 如果搜索后端返回 URL，Sources 中显示网页来源

面试讲解点：

说明当前时间类问题可以路由到更可靠的 time tool，而不是依赖网页搜索。

失败备用方案：

如果外部搜索不可用，展示 UI 的 error state，而不是静默 fallback 到本地 KB。

## 10. 临时文件问答

操作：

切换到 temp file 模式，上传一个小文件并提问。

讲解：

临时文件问答允许用户对一次性文件提问，而不把文件导入持久知识库。

预期结果：

- 临时文件上传成功
- 请求使用 `mode: "temp_kb"`
- Sources 指向临时文件

面试讲解点：

这说明本地 KB 和临时 KB 的 scope 是分开的。

失败备用方案：

如果还没上传临时文件，展示“请先上传文件”的明确错误状态。

## 11. Agent

操作：

切换到 Agent 模式，输入：

```text
What is 25 * 8 and what is the current UTC time?
```

讲解：

Agent 模式会让模型从安全 Tool Registry 中选择工具。根据配置和权限，它可以使用 calculator、current_time、KB search、browser tools、filesystem readonly、SQLite readonly 和 MCP adapter tools。

预期结果：

- Timeline 展示选择的工具
- 可以看到工具 observation
- 最终回答出现

面试讲解点：

项目把 tool decision、execution、observation 和 final answer generation 分开处理。

失败备用方案：

如果模型选择工具不稳定，换成更简单的 `Calculate 25 * 8`。

## 12. Tool Center

操作：

打开 System 或 Tool Center 区域，展示工具分类。

讲解：

工具以产品能力形式展示，而不是直接暴露内部 ID。Developer Mode 可以在需要时显示 schema 和 ID。

预期结果：

- 工具分类清晰
- 可以看到 calculator、knowledge search、browser search、filesystem readonly、SQLite readonly 等常见工具

面试讲解点：

这说明产品体验和工具安全边界是一起设计的。

失败备用方案：

如果 Developer Mode 关闭，说明技术细节默认对普通用户隐藏。

## 13. Account 与 Sessions

操作：

打开 Account，展示 profile 和 sessions。

讲解：

应用支持账户资料编辑、当前 Session 标识、撤销其他 Session、退出其他设备和退出全部设备。

预期结果：

- 当前 Session 被标记
- Session 操作带确认

面试讲解点：

这不只是一个基础登录 Demo，而是包含真实 Session 管理和用户隔离。

失败备用方案：

如果只有一个 Session，可以说明多设备路径，必要时展示 session API 行为。

## 14. System

操作：

打开 System。

讲解：

System 展示 provider/model 状态、依赖检查、Tool Registry、MCP 状态、运行版本和 health。

预期结果：

- Health 可读
- Runtime version 与 release candidate 一致

面试讲解点：

这支持运维排查，同时不暴露 secret。

失败备用方案：

使用：

```bash
curl http://127.0.0.1/api/health
curl http://127.0.0.1/api/health/deps
```

## 15. Docker 与架构

操作：

展示 README 中的架构图，必要时运行：

```bash
docker compose -f docker-compose.prod.yml ps
```

讲解：

可部署形态是 Browser -> nginx -> React/FastAPI -> Auth/Chat/RAG/Agent -> SQLite/FAISS/uploads/model provider。

预期结果：

- 容器 healthy
- README 架构图可以清楚说明数据流

面试讲解点：

补充说明 backup/restore、health checks、nginx proxy 和 30/30 smoke tests。

失败备用方案：

如果 Docker 没运行，展示 `docs/release/v1.0-release-candidate-readiness.md`。

## 结束总结

讲解：

Mini ChatChat 已达到作品集展示标准，适合本地运行和基于 Docker 的私有演示。目前暂未提供公开在线 Demo。Google/GitHub OAuth 主链路已经实现，但真实 Provider 端到端验证仍需要生产凭据和回调配置。

已知演示限制：

- 暂无公开在线 Demo
- 单节点 SQLite 架构
- Backend 镜像约 2 GB
- 暂无邮箱验证和密码重置
- 备份仍是本地归档
- 公开生产部署仍需要 HTTPS、监控和共享基础设施
