# 维护脚本

仅 Python ≥3.10 标准库。默认服务 `http://127.0.0.1:1933`；显式启用鉴权的服务可通过本机环境变量 `OPENVIKING_API_KEY` 提供凭据，脚本不读取聊天、不打印 key。不要在命令行参数填写 key。

## 备份：默认包含用户与所有项目的记忆

```bash
python3 -B ops/scripts/backup-memories.py \
  --user-root viking://user/default \
  --out "$HOME/backups/openviking-content-$(date +%Y%m%d-%H%M%S)"
```

输出目录必须是新的。默认发现 `user/<user>/memories` 和 `user/<user>/peers/*/memories`，逐层分页，不按文件名是否含点猜目录，不遗漏日期桶或深层文件。无记忆、API 错误、分页不完整都返回失败。

需要自定义范围时用重复的 `--root <memory-subtree>`；此时不会自动补入其他空间。必须查看 manifest 的 `roots`，不可把一小段导出称为全库备份。

每次导出包含 raw 原文（保留记忆文件内字段）、URI、SHA256、字节数、预期文件数以及 `complete`。部分失败保留 `complete:false`，恢复工具拒绝使用。默认跳过可重建的 `.abstract.md`/`.overview.md`。

**范围限制**：这是记忆内容导出，不是原子灾备快照。不含向量索引、ACL/tags、会话、凭据、配置或记忆根之外的 identity/soul/skills/resources。备份时避免并发写入/迁移；完整灾备需另备这些内容和上游支持的导出格式。备份目录只放在本机仓库之外。

## 完整性校验与恢复

首先只校验：此命令不发网络请求、不写服务端。

```bash
python3 -B ops/scripts/restore-memories.py --from "$HOME/backups/<export-directory>"
```

先在一次性测试子树预览，再显式应用：

```bash
python3 -B ops/scripts/restore-memories.py \
  --from "$HOME/backups/<export-directory>" \
  --target-root viking://user/default/memories/restore-check
# 检查上面的目标 URI 后，才使用同参数追加 --apply。
```

`--apply` 会发生真实写入，使用 mode=create 和 vectors_only，并逐文件读回比较；已存在且相同的文件跳过，异文目标在写入前统一检查并拒绝。多个源根以 root-N 区分，避免文件名相同相互覆盖。不提供强制覆盖/删除。部分网络失败可能留下部分新文件，重跑时相同文件可跳过。

模拟 API 的导出/恢复测试已做；**用户实际 OpenViking 的恢复演练、索引及检索复验仍待本机操作**。无需现在恢复真实数据；先对少量合成数据单独导出，再在测试子树演练。不要把重算索引描述为已还原 ACL 或全部元数据。

## 隔离验证

```bash
python3 -B ops/scripts/verify-peer-scope.py \
  --peer deepseek-harness --other other-project \
  --query-project '<已存的合成项目事实关键词>' \
  --query-personal '<已存的合成个人偏好关键词>' \
  --project-uri 'viking://user/default/peers/deepseek-harness/memories/<fixture>.md' \
  --personal-uri 'viking://user/default/memories/<fixture>.md'
```

脚本只检索、不捕获、不提交、不传 session_id。检查每条 URI：用户级和共享内容允许；actor 请求中的任意其他 peer、其他用户或未知来源都失败。缺失统计不能掩盖 URI 泄漏；显式矛盾统计仍判失败。未指定 sentinel URI 时，正向命中只证明范围，不证明具体事实被召回。

**5/5 只证明当前检索 API 在这些用例下的结果**，不能证明 App 已加载新配置或 MCP 工具也隔离。修复版脚本在用户服务上的结果仍须重跑，不能沿用旧脚本的 5/5。

## 慢响应模拟

```bash
python3 -B ops/scripts/blackhole-server.py --port 1933 --hold 90 --duration 180
```

脚本默认只监听 loopback，不停止真实服务、不改 App 配置、不调用 launchd。端口被占用会失败，不能同时与真实服务占用1933。完整操作与必须执行的恢复步骤见 [HANDOFF](../../docs/deployment/HANDOFF.md)。连接取消后释放线程，最多64个并发连接，不记录请求正文。

**8秒只控制一次 context 请求**。该工具用于测量真实总等待，包括初始化、备用检索和 legacy peer 请求；它不证明插件存在整轮8秒截止时间。
