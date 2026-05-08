# Personal AI Work Assistant

本项目是一个面向个人使用的本地 AI 工作助理骨架，参考 `personal-ai-assistant-prompt_1.md` 设计实现。

当前版本聚焦可运行的本地后端框架：

- FastAPI 后端服务与健康检查
- WebSocket 对话端点
- DeepSeek 兼容 LLM 客户端封装
- 纯文件存储层
- JSONL 对话归档
- Markdown 任务管理
- iCalendar 日程文件管理
- JSON 实体 CRUD
- 文档上传、下载、重建索引与轻量检索
- 邮件读取/起草技能骨架
- 可插拔技能接口
- 对话工具调用闭环：任务/日程/文档检索可由自然语言触发
- 自动实体沉淀与长期记忆摘要

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

默认配置位于 `config.yaml`。生产使用时请通过环境变量设置：

```bash
export DEEPSEEK_API_KEY="..."
export ASSISTANT_AUTH_TOKEN="..."
```

## API

- `GET /health`：健康检查
- `WS /ws/chat`：对话 WebSocket
- `GET /api/tasks/`：查询任务
- `POST /api/tasks/`：创建任务
- `PATCH /api/tasks/{task_id}`：更新任务状态
- `GET /api/calendar/`：查询日程
- `POST /api/calendar/`：创建日程
- `PATCH /api/calendar/{event_id}`：更新日程
- `DELETE /api/calendar/{event_id}`：删除日程
- `GET /api/entities/{entity_type}`：查询实体
- `POST /api/entities/{entity_type}`：创建实体
- `GET /api/entities/{entity_type}/{entity_id}`：读取实体
- `PUT /api/entities/{entity_type}/{entity_id}`：更新实体
- `DELETE /api/entities/{entity_type}/{entity_id}`：删除实体
- `GET /api/files/`：列出本地文档
- `POST /api/files/`：上传文档并自动索引
- `GET /api/files/search?q=...`：检索本地文档片段
- `POST /api/files/reindex`：重建文档索引
- `GET /api/files/{document_id}`：下载文档
- `GET /api/memory/daily`：列出每日记忆摘要
- `POST /api/memory/daily`：重建当天记忆摘要
- `POST /api/memory/daily/{day}`：重建指定日期摘要
- `GET /api/memory/context`：获取最近长期记忆上下文

如果配置了 `ASSISTANT_AUTH_TOKEN`，HTTP API 使用 `Authorization: Bearer <token>`。WebSocket 可使用同样的 Header，或在开发调试时使用 `ws://host:8000/ws/chat?token=<token>`。

## 对话工具调用示例

WebSocket 发送 JSON：

```json
{"message":"帮我创建任务：完成UVC工艺规格书修订 截止 2026-05-20","session_id":"default"}
```

当前本地规则可直接触发：

- `创建任务/新增待办...` → 写入 `data/tasks/work.md`
- `安排会议/创建日程... 2026-05-20 10:30` → 写入 `data/calendar/default.ics`
- `检索文档/搜索知识库...` → 查询本地文档索引

每轮对话会自动归档到 `data/conversations/YYYY-MM-DD.jsonl`，并从用户消息中轻量提取人物、公司、项目、产品实体写入 `data/entities/`。每日摘要写入 `data/memory/YYYY-MM-DD.yaml`，全局摘要写入 `data/memory/summary.yaml`。

配置 `DEEPSEEK_API_KEY` 后，Agent 也会把已注册工具定义交给 DeepSeek 的 OpenAI 兼容 tool calling 接口。

## 目录

```text
server/       Python 后端
data/         本地持久化数据
app/          Flutter 客户端预留目录
tests/        后端基础测试
```

## 当前限制

- Agent 编排目前是轻量工具闭环，尚未接入 LangGraph 状态机。
- 未配置 `DEEPSEEK_API_KEY` 时，LLM 会返回本地降级响应，便于离线开发。
- 文档检索当前是纯本地关键词/余弦相似度索引，后续可替换为 bge-small-zh + FAISS。
- 邮件技能目前支持 IMAP 读取元信息和回复草稿，不会自动发送邮件。
- 实体抽取当前是轻量规则，后续应升级为 LLM JSON 抽取 + 别名/关系合并。
- 实体向量索引和 Flutter UI 仍是后续阶段内容。
