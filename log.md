# 开发日志

---

## 2026-05-08

### 已完成：Phase 1–4 基础实现

**初始项目骨架（Phase 1–3）**

- FastAPI 后端 + uvicorn，`/health` 健康检查
- WebSocket 对话端点 `/ws/chat`，支持流式 token 输出
- DeepSeekClient：OpenAI 兼容 streaming + tool calling，无 API Key 时本地降级响应
- 文件存储层：FileStore / ConversationStore / EntityStore / TaskStore / CalendarStore / DocumentStore / MemoryStore
- 技能层：TaskSkill（Markdown 任务）/ CalendarSkill（iCal）/ DocSkill（文档检索）/ EntitySkill / EmailSkill（IMAP 骨架）
- Orchestrator：意图分类 → 本地规则工具触发 → DeepSeek tool calling 兜底 → 流式 LLM 回复
- Token 认证中间件
- REST API：tasks / calendar / entities / files / memory

**Phase 4 升级（本轮）**

改动文件：
- `requirements.txt`：新增 pdfplumber、python-docx、sentence-transformers、faiss-cpu
- `server/config.py`：新增 `EmbeddingSettings` 类，加入 `Settings`
- `server/models.py`：`MemorySummary` 新增 `narrative: str = ""` 字段
- `server/rag/embedder.py`（新建）：`Embedder` 类，封装 sentence-transformers + FAISS，依赖缺失时 `available=False` 自动降级
- `server/rag/indexer.py`：
  - 新增 PDF 解析（pdfplumber）、Word 解析（python-docx），import 失败优雅跳过
  - `write_chunks()` 后自动调用 `_rebuild_faiss()` 重建向量索引
- `server/rag/retriever.py`：FAISS 向量搜索优先，index 缺失时自动重建，异常时降级关键词 cosine 搜索
- `server/agent/entity_modeler.py`：
  - 新增 `ENTITY_EXTRACT_PROMPT`（设计文档指定的提取提示词）
  - 新增 `async upsert_entities_async(text, llm)`：有 API Key 时调用 LLM JSON 提取，失败时回退 regex
  - 保留同步 `upsert_extracted_entities()` 向后兼容
- `server/storage/memory_store.py`：
  - 新增 `async update_daily_summary_with_llm(day, llm)`：生成统计摘要 + LLM 叙述性 narrative
  - 新增 `async _generate_narrative(records, llm)`：调用 DeepSeek 生成每日摘要文字
  - `update_daily_summary()` 同步包装修复：无事件循环时用 `asyncio.run()`，有运行循环时用 `ensure_future()`
  - `build_context()` 优先展示 narrative
- `server/agent/orchestrator.py`：
  - `stream()` 重构：先 yield 全部内容，再 `await _post_process()`
  - `_post_process()`：LLM 实体提取 → 写入 assistant 对话记录（含实体 ID）→ 刷新记忆
  - 实体提取和记忆更新不再阻塞前端流式体验
- `server/main.py`：`DocumentIndexer` 传入 `settings.embedding`

**Bug 修复**

- `MemoryStore.update_daily_summary()` 在 pytest 同步上下文中 `RuntimeError: no current event loop` → 改用 `asyncio.get_running_loop()` 判断

**测试**

- `python -m pytest tests/` 全部通过（13 passed）

---

### 待实现（Phase 5，下一批）

- Planner 升级（关键词规则细化 + LLM 意图分类）
- 周记忆摘要生成
- Memory API 异步化（POST /daily 返回含 narrative 的摘要）
- 实体 FAISS 模糊匹配
