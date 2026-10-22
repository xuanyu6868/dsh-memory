# 版本记录

本部署各组件的已验证版本（2026-10-22 实机验收通过时的快照）。

## 服务端（上游包，未修改）

| 组件 | 版本 | 来源 / 安装命令 |
|---|---|---|
| openviking（服务端 + `ov` CLI） | **0.5.1.1** | PyPI；`uv tool install "openviking[local-embed]" --upgrade` |
| llama-cpp-python（local-embed 依赖） | 0.3.36 | 随 extra 安装（本地源码编译，macOS arm64） |
| Embedding 模型 | bge-small-zh-v1.5-f16.gguf（46 MB，512 维） | 首次启动自动下载到 `~/.cache/openviking/models` |
| VLM | kimi-for-coding-highspeed（Kimi Coding 订阅） | **必须 `temperature: 1`**，否则全部 400 |

升级历史：0.5.1 →（发现向量入队 bug，见 docs/deployment/findings.md #2）→ 0.5.1.1。
升级命令备注：本机 uv 直连 PyPI TLS 失败时换清华镜像
`uv tool install "openviking[local-embed]" --upgrade --default-index https://pypi.tuna.tsinghua.edu.cn/simple`。

## DSH 侧

| 组件 | 版本 | 来源 |
|---|---|---|
| @openviking/dsh-memory-plugin | **0.5.26** | npm；DSH plugin_manager 装入 desktop profile |
| 宿主 DSH | desktop profile（未钉版本） | /Applications/DeepSeek Harness.app |

## 运行时环境

| 组件 | 版本 |
|---|---|
| uv | 0.12.1 |
| Python（uv 托管，服务端用） | 3.12.13 |
| Node.js | v24.13.1 |
| 操作系统 | macOS（Apple Silicon） |

## 复验命令

```bash
ov --version                 # 应输出 0.5.1.1
ov status                    # VLM = kimi-for-coding-highspeed，Embedding = bge-small-zh-v1.5-f16
openviking-server doctor     # 全部 PASS
```
