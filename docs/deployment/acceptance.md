# 验收说明（2026-10-22 实机验收）

环境：macOS（Apple Silicon），OpenViking 0.5.1.1（验收中由 0.5.1 升级），
@openviking/dsh-memory-plugin 0.5.26，VLM = kimi-for-coding-highspeed，
Embedding = 本地 bge-small-zh-v1.5-f16。

## 结论总览

| # | 验收项 | 判定 |
|---|---|---|
| 1 | 实际生效配置核对 | ✅ 通过 |
| 2 | 完整自动链路（文字） | ✅ 通过（向量化环节曾缺陷，升级后复验通过） |
| 3 | 语音接入 | ✅ 通过 |
| 4 | 共享与隔离 | ⚠️ 默认不满足；actor+quotas 方案 API 级验证通过，MCP 有限制（见 findings #5） |
| 5 | 性能与故障恢复 | ✅ 通过 |
| 6 | 测试数据清理 | ✅ 通过 |

## 关键证据

**自动链路（文字）**：会话 A（`session-0e4617af`）发送标记为测试用途的事实
（虚构车架号 ZL-2026-8842）→ 服务端生成 `dsh-session-0e4617af…` 档案（捕获）→
第 2 条消息后 ~20s 触发提交（00:46:36→00:46:58）→ 提取出含车架号并自动标注
"测试用途"的实体记忆 → 会话 B（`session-9e2ae790`）提问（问题不含答案），
其会话文件中 `[plugin:openviking-memory]` 注入块在回答前已含该车架号，助手
4 秒正确作答（页面截图确认无记忆内容气泡）。

**语音链路**：语音会话 A（`session-58e8d9e8`）口述虚构门禁卡号 → 提取为实体记忆
（可检索 0.85）；新语音会话 B（`session-61ec14f4`）提问，voice-flow.log 记录
TTS 合成文本为正确答案本身；注入文本在 TTS 日志中 0 次出现（未被朗读）；
会话文件中注入标记为 `plugin:openviking-memory`，与用户发言严格分离。

**性能**：空闲 CPU 0.7% / RSS ~435MB；检索 API 36–86ms（即每次提问的额外等待）；
提取峰值 CPU 49–55% 持续 3–6s；冷启动 7s 就绪。

**故障恢复**：停服 115s 期间聊天正常（连接立即失败 0.24ms，不阻塞）；
恢复后 30s 内待处理队列自动重放成功（服务端会话档案时间戳证实）。

**隔离（API 四象限）**：actor=other-project 查项目事件 → 0 命中；
actor=本 peer 查项目事件 → 命中；两种身份查个人偏好 → 均命中。
**注意**：仅当请求携带 quotas（插件设 `recallLimit` 后满足）时成立，见 findings #3。

## 配置现状（验收后）

- `commitTokenThreshold: 1000`（默认 20000，调小让短对话自动提交）
- `recallPeerScope: "actor"` + `recallLimit: 10`（隔离生效的必要组合）
- `recallContextTimeoutMs: 8000`（检索等待预算）
- 工作区 peer：`.openviking/config.json` → `peer.id=deepseek-harness`
- 26 条本工作区 events 记忆已迁入 `peers/deepseek-harness/memories/events`
  （迁移前全量备份在本地 `~/backups/openviking-memories-20261022/`，未入库）

## 清理记录

测试事实实体（虚构自行车/门禁卡）、5 个测试会话服务端档案、上一轮演示资源
已全部删除并验证无残留；真实记忆（偏好、智能家居、基础设施实体、events 工作日志）
完整保留。

## 验收时尚未完成（待办）

- [ ] 新 patch（actor/quotas/8s 预算）需重启 App 生效，重启后需在真实会话复验隔离
- [ ] 慢响应测试（挂起服务验证 8s 预算降级行为，脚本见 ops/scripts/blackhole-server.py）
- [ ] 其他工作区的 GUI 隔离反向验证
