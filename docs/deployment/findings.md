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

## 7. 旧内容备份默认遗漏项目空间（本仓库已修复；本机待更新）

旧脚本默认只遍历用户memories，迁移至peers/*/memories的项目事件不会备份；按文件名是否含点猜目录、固定深度与未消费分页，也可能静默遗漏。原文读取默认清理部分记忆字段，不适合原样导出。

本轮默认发现用户及所有peer的memories；使用isDir与has_more/offset分页，读取raw原文，保存URI/hash/完成状态。新增恢复工具默认离线校验，显式apply后只create并读回。模拟API回归通过，真实恢复仍待验收。导出不含索引/ACL等，范围见脚本README。

## 8. 隔离脚本依赖缺失统计而误报（本仓库已修复；原5/5需重跑）

已在隔离夹具复现：返回project-c的内容且不提供other_peer统计，原脚本仍5/5 PASS。新脚本逐条校验URI，拒绝actor请求里任何其他peer/其他用户/未知来源；统计声称0也不能绕过。个人命中使用用户级URI，不再只信self计数。无session_id，避免测试影响会话召回ledger。

## 9. 单次context超时被写成整轮8秒上限（文档已修正；上游行为未改）

8000ms只传给primary context请求。失败时可执行legacy recall、raw检索，初始化及legacy peer查询另计。本轮未更改官方runtime，不能声明增加了总deadline或取消传播。挂起工具修正说明、释放已取消连接并支持有限测试时长；整轮表现必须按HANDOFF在用户Mac验证。

## 当前边界

上述配置绕过与最初安装结果属于本机报告，非本轮重新验证。本轮维护工具已变更，因此旧脚本成绩不自动转成新工具实机成绩。源码时间戳只是安装者的审计依据，不能单独证明与发布包逐字节一致；如需更强证据应比较发布包内容/哈希。
