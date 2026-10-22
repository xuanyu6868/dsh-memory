# patches/

## 当前状态：零补丁

截至 2026-10-22，本部署**没有修改任何上游包的源码**——`node_modules`
（@openviking/dsh-memory-plugin 0.5.26）与 uv `site-packages`
（openviking 0.5.1.1）均保持官方发布内容，全部问题均通过配置调整或
上游升级解决（详见 docs/deployment/findings.md）。因此本目录暂无补丁。

## 未来需要改源码时的流程

1. **优先替代品**：能用配置解决就不改源码；上游已修复的就升级（VERSIONS.md 记录当前版本）。
2. **生成补丁**：确需修改时，在改动前后各复制一份，生成统一 diff 放本目录：
   ```bash
   diff -u original.py modified.py > patches/0001-short-description.patch
   ```
3. **补丁头注明**：目标包名@版本、文件相对路径、问题描述、上游 issue（如有）。
4. **升级后重放**：
   - npm/node_modules：升级插件后检查目标文件是否变化，未变则
     `cd <package-dir> && patch -p1 < patches/0001-*.patch`；建议同时用
     pnpm 的 `patchedDependencies` 或 `patch-package` 固化。
   - uv/site-packages：uv 工具环境会被升级整体替换，补丁须重放；
     更稳的做法是 fork 上游仓库改代码，然后
     `uv tool install "git+https://github.com/<you>/OpenViking@<branch>[local-embed]"`。
5. 每个补丁都要在 VERSIONS.md 记录"适用版本"和"重放状态"。
