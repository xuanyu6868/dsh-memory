# 本机验收结果（2026-10-22，HANDOFF 操作单执行记录）

执行方：DeepSeek Harness（用户本机）。基线提交：`ca18c62`。本文只含元数据
（时间、分数、会话 ID）与合成测试数据；不含密钥、聊天、真实记忆全文或原始日志。

## 0. 准备

- `npm run check` PASS；`npm test` 全绿（exit 0，含负向夹具——泄漏场景被正确判负）。
- 本机配置 vs 模板：ov.conf（脱敏后）、ovcli.conf、工作区 peer 配置、launchd plist
  （去注释后）、cordis 插件块 —— **全部一致**，无需合并字段。
- 实际加载确认：MCP 代理进程于 01:50:46（patch 写入后 2 秒）随 App 重启重建，
  进程 env 实测 `OPENVIKING_RECALL_PEER_SCOPE=actor`、`OPENVIKING_PEER_ID=`（空）。
  GitHub 提交 ≠ 本机生效，此条以进程证据为准。
- 版本：openviking 0.5.1.1，插件 0.5.26，与 VERSIONS.md 一致。

## A. 备份 / 恢复演练

- **真实导出**：`complete=true`；roots=2（`user/default/memories` +
  `user/default/peers/deepseek-harness/memories`）；42 文件 = 磁盘 42；
  **42/42 SHA256 匹配**；已迁移的工作日志（peer events 27 个）与日期桶深层文件均在列。
- **范围声明**：仅记忆内容导出；不含向量索引、ACL/tags、会话、凭据、配置；
  不是完整灾备。
- **合成恢复**（唯一前缀 opsacc，个人/项目各 1 条）：分别 `--root` 导出
  （complete=true，2 roots 2 文件）→ 默认预览零网络请求 →
  `--target-root .../ops-restore-0300 --apply` 恢复 → 工具读回校验 2/2 一致 →
  reindex 后恢复副本可检索（0.82）。
- **清理**：恢复副本、源 fixture、临时导出目录均已删除并验证。

## B. 实际隔离

- **脚本**（新版，哨兵 URI，每用例 16 个结果 URI 逐一校验）：**5/5 PASS**。
- **GUI 正向**（本工作区）：直接答出项目口令；该轮注入首条即 peer 实体（0.87），
  且本会话（peer 配置前已存在）注入也已切换到 deepseek-harness peer + 用户级，
  无其他 peer 内容。
- **GUI 反向**（Personal-Website 工作区）：自动注入**只含用户级内容**
  （个人偏好 0.69）——自动检索隔离成立。**但**助手随后主动调用
  `mcp__openviking__search` 两次，MCP 广搜返回 peer 项目事实（84%）并最终答出口令。
  → **MCP 进程级广搜实机复现了跨项目取数**（findings #5 的设计限制）。
  自动检索隔离成立；不声称完整工具隔离。单项目用户可选
  `ovcli.conf` 设 `actor_peer_id` 钉死 MCP。
- **用户级残留检查**：发现本长会话仍向用户级写入 4 条 events（peer 配置前
  检索态已固定所致），已迁移至 peer 空间并重建索引（36 条向量）；基础设施类实体
  （服务端/两个模型/插件/代码仓库，共 5 条）判归属不明 → 保留并列出。

## C. 挂起测试（整轮计时，不只单次 HTTP）

- **基线**：健康服务，全新会话"提交→开始回答" ≈ **5.4s**。
- **黑洞窗口内**（已初始化会话，4 条"你好"）：提交→开始执行
  **155.4s / 91.2s / 50.5s**（第 4 条在恢复后 3.1s，正常）。每条最终都有回答；
  无卡死；用户未逐项评价主观等待感受（中途决定结束测试）。
- **结论：整轮 8 秒目标未达成。**
  机制（源码确认）：`recallContextTimeoutMs: 8000` 只覆盖**单次 context 请求**；
  超时后插件串行回退 legacy `/api/v1/search/recall`（`recallTimeoutMs` 默认 **120s**）
  与 raw find（`timeoutMs` 默认 15s），链式叠加，外加快速连发时的排队效应。
- **取舍方案（待用户决策）**：patch 增加 `recallTimeoutMs: 8000`（legacy 级同预算，
  最坏链 ≈24s）；**真正严格的整轮 deadline 需要上游补丁**（回退链取消传播/
  总预算），可作为独立补丁项立项（ops/patches/ 流程已备）。
- **未执行用例**：挂起中的语音、挂起中的全新会话文字（用户决定终止，如实记录）。
- **恢复（两轮均验证）**：launchd 重新托管约 6 秒恢复健康；`ov status` 队列 0；
  挂起期间失败的捕获写入在恢复后 30 秒内自动重放（服务端会话档案 mod_time 证据）；
  普通聊天恢复（3.1s）。

## D. 剩余问题（合并评估参考）

1. 整轮检索预算未达标 —— 待决策：调 `recallTimeoutMs`（小改）或上游总 deadline 补丁（根治）。
2. MCP 广搜突破项目隔离 —— 设计限制；可选 `actor_peer_id` 钉死或保持现状（跨项目工具）。
3. 服务端 `gather_flat`（无 quotas）忽略 `peer_scope` —— 已由 `recallLimit` 绕过；
   建议报上游修复。
4. 挂起中语音 / 全新会话两例未测（用户终止）。
5. 本长会话的检索态已切换正常；历史残留已清。
