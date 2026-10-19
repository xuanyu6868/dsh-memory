# dsh-memory 设计文档（草案）

> 状态：Draft v0.1 —— 待 GPT/Codex 补全细节后评审。

## 1. 问题定义

DeepSeek Harness 的会话是临时的：每次新会话都从零开始。需要一个记忆系统，
让重要信息（用户偏好、项目决定、常用命令、已解决的问题）能跨会话保留并被检索。

## 2. 核心概念

### 2.1 记忆条目（Memory Entry）

```json
{
  "id": "mem_01J...",
  "created_at": "2026-10-19T10:00:00-07:00",
  "updated_at": "2026-10-19T10:00:00-07:00",
  "kind": "preference | fact | decision | procedure",
  "summary": "一句话摘要，用于列表展示与粗筛",
  "content": "完整内容（Markdown）",
  "tags": ["dsh", "plugin"],
  "source": { "session": "...", "ref": "可选：文件/消息引用" },
  "ttl_days": null
}
```

### 2.2 存储

- 主存储：`store/memories.jsonl`（append-only，更新采用 tombstone + 新条目）。
- 索引：本地 SQLite（FTS5）做关键词检索；可选 embedding 索引做语义检索。

### 2.3 API（草案）

| 方法 | 说明 |
|---|---|
| `remember(entry)` | 写入一条记忆 |
| `recall(query, limit)` | 检索相关记忆 |
| `forget(id)` | 删除（tombstone） |
| `list(filter)` | 列出记忆 |
| `compact()` | 合并 / 清理过期与重复条目 |

## 3. 写入策略

- 显式写入优先：由用户或代理明确调用 `remember`。
- 自动提取（可选第二阶段）：会话结束时由模型提取候选记忆，人工确认后入库。

## 4. 检索与注入

- 会话开始：注入 `kind=preference` 与最近 N 条高频命中的记忆摘要。
- 任务进行中：按当前任务关键词 `recall`，只注入 top-k，避免上下文膨胀。

## 5. 非目标（v1 不做）

- 多人协作 / 云端同步。
- 自动无确认的记忆写入。

## 6. 开放问题

1. embedding 用本地模型还是远程 API？
2. 与 DSH 的集成形态：插件、MCP server，还是独立 CLI？
3. 记忆冲突（同一事实新旧两版）的裁决策略？
