# AGENTS.md — 给编码代理的说明

本仓库是 DeepSeek Harness 的记忆系统。实现时请先阅读 `docs/design.md`，并遵守以下约定：

## 约定

1. **语言与运行时**：默认 TypeScript（Node.js ≥ 20），除非设计文档另有说明。
2. **存储格式**：记忆条目使用 JSONL（一行一条），人类可读的摘要用 Markdown；禁止引入二进制专有格式。
3. **隐私**：绝不把真实的用户密钥、token、个人隐私数据写入仓库或测试夹具；统一用 `example.com` / `sk-xxx` 之类的占位符。
4. **测试**：每个公开 API 都要有单元测试；运行 `npm test` 必须全绿才能提交。
5. **提交信息**：使用 Conventional Commits（`feat:` / `fix:` / `docs:` / `test:` / `chore:`）。

## 工作方式

- 大改动先开 PR，不要直接推 main。
- 不确定的设计决策在 PR 描述里列出选项，由人来定。
