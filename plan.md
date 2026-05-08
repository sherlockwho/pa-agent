# 项目开发计划

> 对应设计文档：`personal-ai-assistant-prompt.md`

---

## 总体进度

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1 | FastAPI 骨架、WebSocket、DeepSeek 客户端、文件存储、对话归档 | ✅ 完成 |
| Phase 2 | 实体建模 CRUD + 轻量提取 | ✅ 完成（基础）|
| Phase 3 | 技能接入（任务/日程/文档/邮件）、Function Calling 工具闭环 | ✅ 完成 |
| Phase 4 | RAG（PDF/Word 解析 + FAISS 向量索引）、LLM 实体提取、LLM 记忆摘要 | ✅ 完成 |
| Phase 5 | 记忆系统完善（周摘要、LLM Planner）、实体 FAISS 模糊匹配 | 🚧 进行中 |
| Phase 6 | Docker 容器化、Tailscale 远程访问、日志监控 | ⏳ 待开始 |
| Flutter | 移动客户端（对话 / 任务 / 日程 / 实体浏览器） | ⏳ 待开始 |

---

## Phase 5 任务清单（当前阶段）

### 下一批实现目标

- [ ] **Planner 升级**：关键词规则更精准（区分 create/query），有 API Key 时调用 LLM 分类意图
- [ ] **周记忆摘要**：在 `MemoryStore` 中实现 `generate_weekly_summary()`，config 已有 `weekly_summary_day`
- [ ] **Memory API 异步化**：`POST /api/memory/daily` 端点改为 async，返回含 LLM narrative 的摘要
- [ ] **实体 FAISS 模糊匹配**：用向量索引辅助 `find_by_name()` 的别名匹配，减少重复实体

### 后续排队

- [ ] 测试覆盖补全（Planner、MemoryStore weekly、entity fuzzy match）
- [ ] `daily_summary_trigger` 计数逻辑（每 N 条消息触发一次，而非每条都生成）
- [ ] `POST /api/memory/weekly` 端点
- [ ] 邮件技能完善（body 解析、搜索过滤）

---

## Phase 6 任务清单（待开始）

- [ ] Dockerfile + docker-compose（挂载 data/ 目录）
- [ ] uvicorn 生产配置（workers、log level）
- [ ] Tailscale/WireGuard 远程访问文档
- [ ] 错误处理与结构化日志（structlog 或标准 logging）

---

## Flutter 客户端（待开始）

- [ ] 项目初始化（`flutter create app`）
- [ ] ChatScreen：WebSocket 流式对话界面
- [ ] TasksScreen：任务列表
- [ ] CalendarScreen：日程视图
- [ ] EntityBrowser：实体浏览器
- [ ] api_service.dart：HTTP + WebSocket 封装
