#!/usr/bin/env python3
"""peer_scope=actor 隔离四象限验证（针对 OpenViking 服务端 gather_flat 泄漏，
见 docs/deployment/findings.md #3）。

前提：某个 peer（默认 deepseek-harness）下已有项目事件记忆，用户级空间有个人偏好。

验证矩阵（携带 quotas，走 gather_bucket 路径）:
    1. scope=all, 无 peer       查项目事件 -> 应命中 peer 条目
    2. scope=actor, 本 peer     查项目事件 -> 应命中 peer 条目
    3. scope=actor, 其他 peer   查项目事件 -> 应【不】命中 peer 条目（隔离）
    4. scope=actor, 其他 peer   查个人偏好 -> 应命中用户级条目（共享）
    5. scope=actor, 本 peer     查个人偏好 -> 应命中用户级条目

用法:
    python3 verify-peer-scope.py [--base http://127.0.0.1:1933]
        [--peer deepseek-harness] [--other other-project]
        [--query-project "TTS 语音合成故障"] [--query-personal "用户用什么操作系统"]
退出码: 0 = 全部符合预期；1 = 存在不符合项。
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

QUOTAS = {"events": 3, "entities": 3, "preferences": 3, "experiences": 3, "resources": 2, "skills": 2}


def search(base, query, peer_scope, actor=None):
    body = {"query": query, "mode": "context", "max_tokens": 3000,
            "peer_scope": peer_scope, "session_id": "verify-peer-scope", "quotas": QUOTAS}
    req = urllib.request.Request(
        base + "/api/v1/search/search", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    if actor:
        req.add_header("X-OpenViking-Actor-Peer", actor)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:150]}")
        return None, None
    res = d.get("result") or {}
    entries = res.get("entries") or []
    origins = (res.get("stats") or {}).get("origins", {})
    return entries, origins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:1933")
    ap.add_argument("--peer", default="deepseek-harness")
    ap.add_argument("--other", default="other-project")
    ap.add_argument("--query-project", default="TTS 语音合成故障")
    ap.add_argument("--query-personal", default="用户用什么操作系统")
    args = ap.parse_args()

    failures = 0

    def check(label, query, scope, actor, expect_peer_hit=None, expect_self_hit=None):
        """统一断言：actor 模式下 other_peer 必须恒为 0（无跨项目泄漏）；
        expect_peer_hit=True 要求命中本 peer 条目；expect_self_hit=True 要求命中用户级。"""
        nonlocal failures
        entries, origins = search(args.base, query, scope, actor)
        if entries is None:
            failures += 1
            return
        origins = origins or {}
        peer_hits = [e for e in entries if f"/peers/{args.peer}/" in str(e.get("uri", ""))]
        ok = True
        if scope == "actor" and origins.get("other_peer", 0) != 0:
            ok = False  # 隔离红线：任何情况下 actor 模式都不应出现其他 peer
        if expect_peer_hit is True and not peer_hits:
            ok = False
        if expect_peer_hit is False and peer_hits:
            ok = False
        if expect_self_hit is True and origins.get("self", 0) == 0:
            ok = False
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"[{mark}] {label}: peer条目={len(peer_hits)} origins={origins}")

    check("1) all/无peer 查项目事件（应命中）", args.query_project, "all", None, expect_peer_hit=True)
    check("2) actor/本peer 查项目事件（应命中）", args.query_project, "actor", args.peer, expect_peer_hit=True)
    check("3) actor/其他peer 查项目事件（应隔离）", args.query_project, "actor", args.other, expect_peer_hit=False)
    check("4) actor/其他peer 查个人偏好（应命中用户级）", args.query_personal, "actor", args.other, expect_self_hit=True)
    check("5) actor/本peer 查个人偏好（应命中用户级）", args.query_personal, "actor", args.peer, expect_self_hit=True)

    print("结论:", "全部符合预期" if failures == 0 else f"{failures} 项不符合——见 docs/deployment/findings.md #3")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
