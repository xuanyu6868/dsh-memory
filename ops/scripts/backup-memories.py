#!/usr/bin/env python3
"""备份 OpenViking 记忆库到本地目录（纯文本 Markdown，保留目录结构）。

用法:
    python3 backup-memories.py [--base http://127.0.0.1:1933]
                               [--root viking://user/default/memories]
                               [--out ~/backups/openviking-memories-YYYYMMDD]

说明:
    - 通过 HTTP API 读取（/api/v1/fs/ls + /api/v1/content/read），不复制向量索引。
    - events 的日期桶目录（2026/10/22 等）在递归 ls 中只返回桶本身，
      需要先展开到具体日期目录再列文件——本脚本已处理。
    - 仅标准库。备份产物不含密钥，但包含记忆内容，注意存放位置。
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


def api(base, path, **params):
    q = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{base}{path}?{q}", timeout=30) as r:
        return json.load(r)


def list_markdown(base, uri, depth=0):
    """递归列出 .md 文件 URI；日期桶目录（无扩展名且非叶）向下展开。"""
    if depth > 8:
        return []
    d = api(base, "/api/v1/fs/ls", uri=uri, recursive="false", limit=500)
    items = d.get("result") or []
    files = []
    for i in items:
        u = i.get("uri", "")
        if not u:
            continue
        if u.endswith(".md"):
            files.append(u)
        elif "." not in u.rsplit("/", 1)[-1]:  # 目录（无扩展名）
            files.extend(list_markdown(base, u, depth + 1))
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:1933")
    ap.add_argument("--root", default="viking://user/default/memories")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    files = list_markdown(api_base := args.base, args.root)
    print(f"发现 {len(files)} 个记忆文件")
    ok = fail = 0
    for uri in files:
        rel = uri.replace(args.root.rstrip("/") + "/", "")
        dst = os.path.join(os.path.expanduser(args.out), rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            c = api(api_base, "/api/v1/content/read", uri=uri)
            r2 = c.get("result")
            text = r2.get("content") if isinstance(r2, dict) else (r2 or "")
            with open(dst, "w", encoding="utf-8") as f:
                f.write(text if isinstance(text, str) else json.dumps(text, ensure_ascii=False))
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {uri}: {e}", file=sys.stderr)
            fail += 1
    print(f"完成：成功 {ok}，失败 {fail}，输出目录 {args.out}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
