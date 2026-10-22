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

## 当前部署的运维产物（ops/）

本仓库同时维护当前实机运行的记忆部署（OpenViking 服务端 + DSH 记忆插件）的
运维产物——这些是**配置模板、文档与维护脚本，不含上游源码改动**
（截至 2026-10-22 对上游包零修改，见 [ops/patches/README.md](ops/patches/README.md)）：

- [VERSIONS.md](VERSIONS.md) — 全部组件版本与升级命令
- [docs/deployment/install.md](docs/deployment/install.md) — 安装说明
- [docs/deployment/acceptance.md](docs/deployment/acceptance.md) — 实机验收结论与证据
- [docs/deployment/findings.md](docs/deployment/findings.md) — 问题与缺陷记录（含绕过方案）
- [ops/config/](ops/config/) — 脱敏配置模板（密钥一律 `sk-xxx` 占位）
- [ops/scripts/](ops/scripts/) — 维护脚本：记忆备份、隔离验证、挂起模拟
- [ops/patches/](ops/patches/) — 上游源码补丁（当前为空，含未来补丁流程）
