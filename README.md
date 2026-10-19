# dsh-memory

DeepSeek Harness（DSH）记忆系统 —— 为 DSH 会话提供持久化、可检索的长期记忆。

## 目标

- 跨会话记忆：把会话中的重要事实、偏好、决定沉淀为结构化记忆。
- 可检索：支持按关键词 / 语义检索，按需注入上下文。
- 可审计：记忆以纯文本（Markdown / JSONL）形式存储，版本可控、可人工编辑。

## 仓库结构（规划）

```
dsh-memory/
├── README.md            # 本文件
├── AGENTS.md            # 给编码代理（GPT/Codex 等）的说明
├── docs/
│   └── design.md        # 设计文档（数据结构、检索、写入策略）
├── src/                 # 实现代码（待建）
└── tests/               # 测试（待建）
```

## 状态

🚧 脚手架阶段，设计稿见 [docs/design.md](docs/design.md)。
