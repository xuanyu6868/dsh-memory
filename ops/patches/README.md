# 上游补丁策略

## 当前状态

安装者报告：OpenViking0.5.1.1和官方DSH插件0.5.26均通过发布包安装，无手工源码改动。本轮Codex也未修改用户已安装的node_modules/site-packages。

本仓库自行实现的ops脚本不属于“上游源码补丁”。目前没有上游补丁；8秒整轮deadline也未实现。不能仅凭文件时间戳声称与发布包逐字节一致，必要时比较发布包哈希/内容。

## 将来确需修改上游时

1. 先确认问题不能通过已验证配置或已发布修复解决。
2. 首选fork，在可追溯提交中修复和测试，记录上游基准版本/commit与自有commit。Python安装形式示例：`uv tool install "openviking[local-embed] @ git+https://github.com/<you>/OpenViking.git@<commit>"`。占位符必须替换，不把branch HEAD称为固定版本。
3. 若选择补丁，使用带正确相对路径的Git diff（例如a/path.py、b/path.py），记录生成根目录和strip参数；应用前执行`git apply --check`，应用后做实际回归。不要用两个任意文件名的diff配合未经核对的patch -p1。
4. npm改动优先用pnpm patch/patch-commit等可随清单重放的机制；升级后先检查是否仍需补丁，再验证适用性，不能盲目重放。
5. VERSIONS.md记录版本、补丁/fork提交、适用性、重放与验证结果。配置、模板、服务端实际运行版本和客户端实际加载状态分开记录。
