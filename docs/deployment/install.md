# 安装说明（OpenViking 服务端 + DSH 记忆插件）

适用：首次安装/复现基线。已有工作安装先按HANDOFF核对差异，不覆盖配置或重复安装。

目标：macOS 本地跑通 OpenViking 记忆服务，DSH desktop profile 全量启用记忆插件
（自动召回、自动捕获提交、MCP 工具、技能目录）。VLM 用 Kimi Coding，embedding 用
本地 GGUF 模型（无需第二个 key）。

## 1. 服务端

```bash
# 需要 uv（Python 3.10+ 由 uv 托管）
uv tool install "openviking[local-embed]==0.5.1.1" --upgrade
# 若直连 PyPI TLS 失败：
# uv tool install "openviking[local-embed]==0.5.1.1" --upgrade --default-index https://pypi.tuna.tsinghua.edu.cn/simple

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
python3 - <<'PYTHON'
from pathlib import Path
import plistlib
home = Path.home()
p = home / "Library/LaunchAgents/ai.openviking.server.plist"
if p.exists():
    raise SystemExit("目标已存在：请先备份并比较差异，不覆盖")
def render(value):
    if isinstance(value, str): return value.replace("__HOME__", str(home))
    if isinstance(value, list): return [render(item) for item in value]
    if isinstance(value, dict): return {key: render(item) for key, item in value.items()}
    return value
config = plistlib.loads(Path("ops/config/ai.openviking.server.plist.template").read_bytes())
p.parent.mkdir(parents=True, exist_ok=True)
(home / ".openviking/logs").mkdir(parents=True, exist_ok=True)
p.write_bytes(plistlib.dumps(render(config)))
PYTHON
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.openviking.server.plist
ov status   # 检查真实服务状态
```

## 3. DSH 插件

在 DSH 会话里用 plugin_manager 安装（或 CLI `dsh plugin --profile desktop add @openviking/dsh-memory-plugin@0.5.26`）：

```
@openviking/dsh-memory-plugin@0.5.26
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

## 6. 初步验证（不能代替Harness自动链路验收）

```bash
openviking-server doctor
ov status
```

自动链路必须从Harness正常输入开始验证，不能用CLI手工写入/搜索代替。完整状态见[acceptance.md](acceptance.md)，接手操作见[HANDOFF.md](HANDOFF.md)。
