# dsh-memory

DeepSeek Harness 的 OpenViking 记忆集成与运维工具，后续增加 Harness 内置记忆管理页面。

当前采用：Mac 本地 OpenViking + 本地 GGUF Embedding + Kimi Coding 云端提取 + 官方 DSH 插件。无自研 JSONL/SQLite 引擎，管理页面尚未实现。

## 当前入口

- [设计与边界](docs/design.md)
- [组件版本](VERSIONS.md)
- [首次安装](docs/deployment/install.md)
- [验收记录及未完成项](docs/deployment/acceptance.md)
- [缺陷与取舍](docs/deployment/findings.md)
- **[给 DeepSeek Harness 的下一步操作单](docs/deployment/HANDOFF.md)**
- [运维工具用法](ops/scripts/README.md)
- [脱敏配置模板](ops/config/)
- [上游补丁策略](ops/patches/README.md)

## 本仓库验证

Python ≥3.10、Node ≥20，无需安装第三方包：

```bash
npm run check
npm test
```

测试只使用合成数据与本地模拟 API，不连接真实记忆库、不调用 Kimi、不操作 launchd。模型及宿主安装的兼容版本见 VERSIONS.md。

配置/脚本推送 GitHub 不代表 Mac 已升级或 App 已加载。当前剩余本机验收见操作单；本轮没有替用户完成 App 重启、真实恢复或整轮超时验证。

源码与模板可入库；真实密钥、聊天、记忆、备份、数据库和原始日志不进入本仓库。
