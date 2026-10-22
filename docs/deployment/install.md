# 安装说明（OpenViking 服务端 + DSH 记忆插件）

目标：macOS 本地跑通 OpenViking 记忆服务，DSH desktop profile 全量启用记忆插件
（自动召回、自动捕获提交、MCP 工具、技能目录）。VLM 用 Kimi Coding，embedding 用
本地 GGUF 模型（无需第二个 key）。

## 1. 服务端

```bash
# 需要 uv（Python 3.10+ 由 uv 托管）
uv tool install "openviking[local-embed]" --upgrade
# 若直连 PyPI TLS 失败：
# uv tool install "openviking[local-embed]" --upgrade --default-index https://pypi.tuna.tsinghua.edu.cn/simple

mkdir -p ~/.openviking
```

把 [ops/config/ov.conf.template.json](../../ops/config/ov.conf.template.json) 复制为
`~/.openviking/ov.conf`，填入自己的 Kimi key（`vlm.api_key`），按需修改
`storage.workspace` 绝对路径。注意 **`temperature: 1` 必须保留**——
kimi-for-coding-highspeed 只接受 temperature=1，否则所有 VLM 调用 400。

把 [ops/config/ovcli.conf.json](../../ops/config/ovcli.conf.json) 复制为
`~/.openviking/ovcli.conf`（本机 dev 模式无需 key）。

```bash
openviking-server doctor   # 全部 PASS 再继续
openviking-server          # 前台验证一次，Ctrl-C 停掉
```

## 2. launchd 常驻

```bash
sed -i '' "s|__HOME__|$HOME|g" ops/config/ai.openviking.server.plist.template
mkdir -p ~/.openviking/logs
cp ops/config/ai.openviking.server.plist.template ~/Library/LaunchAgents/ai.openviking.server.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.openviking.server.plist
ov health   # 已连接（健康）
```

## 3. DSH 插件

在 DSH 会话里用 plugin_manager 安装（或 CLI `dsh plugin --profile desktop add`）：

```
@openviking/dsh-memory-plugin
```

插件凭证链自动读 `~/.openviking/ovcli.conf` → `~/.openviking/ov.conf`，无需额外配置。

## 4. profile 配置（可选但推荐）

把 [ops/config/cordis.patch.openviking-snippet.yml](../../ops/config/cordis.patch.openviking-snippet.yml)
的 `openviking-memory-runtime` 块合并进 `~/.dsh/profiles/desktop/cordis.patch.yml`，
重启 App 生效。片段里每个键的作用与坑都有注释。

## 5. 项目隔离（可选）

在需要独立记忆空间的工作区根目录放 `.openviking/config.json`
（见 [ops/config/workspace-peer.config.json](../../ops/config/workspace-peer.config.json)），
该工作区的项目记忆即写入 `viking://user/<你>/peers/<peer>/memories`；
配合上面 patch 的 `recallPeerScope: actor`，项目记忆不会进入其他项目的自动检索。
git 工作区无需此文件（自动按 origin URL 派生 peer）。

## 6. 验证

```bash
ov add-memory "测试：我喜欢浅色主题。"
sleep 60
ov find "浅色主题"     # 应命中新提取的记忆
```

DSH 新会话问相关偏好，应看到回答引用记忆。完整验收流程见
[acceptance.md](acceptance.md)。
