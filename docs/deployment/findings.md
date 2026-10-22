# 问题与缺陷记录

安装、验收过程中发现的问题、根因、处置与复验方法。每条都对照过实际安装
源码或日志，附处置状态。

## 1. Kimi VLM 只接受 temperature=1（已修复，配置侧）

- **现象**：所有 VLM 调用 400：`invalid temperature: only 1 is allowed for this model`，
  导致摘要生成与记忆提取全部失败。
- **根因**：OpenViking VLM 配置默认 temperature=0.0；`kimi_vlm.py` 的
  `normalize_kimi_config` 只规整 api_base/model/User-Agent，不处理 temperature。
- **处置**：`ov.conf` 的 `vlm` 段加 `"temperature": 1`（模板已含）。

## 2. v0.5.1 向量入队被拒（已修复，升级上游）

- **现象**：记忆提取写了文件但搜不到；日志每次提取必现
  `Error enqueuing embedding message: Task <uuid> is unavailable; rejected work for Embedding`。
- **根因**：`vikingdb_manager.enqueue_embedding_msg` 把记忆向量挂到已关闭的
  提取任务上，入队被拒且不重试（0.5.1）。
- **处置**：升级 0.5.1 → **0.5.1.1** 后错误归零，语音轮提取无需人工干预即可检索。
  历史受影响记忆用 `ov reindex <URI> --mode vectors_only --wait true` 补救。

## 3. `peer_scope=actor` 在无 quotas 时被静默忽略（服务端 0.5.1.1，绕过）

- **现象**：`peer_scope: "actor"` + `X-OpenViking-Actor-Peer: other-project`，
  context 模式检索仍返回其他 peer 的记忆（四象限测试实锤）。
- **根因**：`retrieve/context_assembler/gather.py` 的 **`gather_flat()`**
  （请求不带 quotas 时走这里）的基础搜索写死 `target_uri=""`（全库扫描），
  且对结果不做 origin 过滤；只有 `gather_bucket()`（带 quotas）正确按
  `memory_target_roots(ctx)` = [用户级, 当前 peer] 限定范围。
- **绕过（已验证）**：请求显式携带 quotas → 走 bucket 路径 → 隔离完全正确。
  插件侧设置 `recallLimit`（任意正整数）即自动携带 quotas
  （`shared/recall-core.mjs`: `if (limitConfigured) body.quotas = codingQuotas(limit)`）。
- **复验**：`python3 ops/scripts/verify-peer-scope.py`。

## 4. dsh 侧死配置（文档修正）

- `commitTurnThreshold`、`commitKeepRecentCount` 在 `@openviking/dsh-memory-plugin`
  0.5.26 的 dsh 运行时中**零引用**：turn/end 唯一触发器是
  `commitTokenThreshold`（runtime.mjs 比对服务器 pending_tokens）；
  提交请求体硬编码 `keep_recent_count: 0`（client.mjs）。
- 真实提交时机：token 阈值 / compaction/start / 会话销毁。

## 5. MCP 工具的进程级 peer 限制（设计限制，已记录取舍）

- MCP 代理每 profile 单进程，无法跟随会话工作区切换 peer。actor 模式下无显式
  peer 时**主动降级为全 peer 广搜**（`shared/mcp-proxy-config.mjs` 的 fallback
  警告原文："actor-scoped recall needs an explicit peer id… Falling back to broad
  recall across every peer under this user"）。
- 选项：`ovcli.conf` 设 `actor_peer_id` 可把 MCP 钉死在单一项目（单项目用户适用；
  多项目会话反而会指错）。
- **当前取舍**：自动检索做隔离（actor），MCP 保持广搜作为跨项目查询的显式工具。

## 6. 环境备注：uv 直连 PyPI TLS 失败

- 本机（Clash 代理环境）uv 装/升级包时报 `tls handshake eof`，curl 正常。
- 处置：`--default-index https://pypi.tuna.tsinghua.edu.cn/simple` 换镜像源成功。
