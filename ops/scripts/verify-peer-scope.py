#!/usr/bin/env python3
"""Read-only scope checks using result URIs, not optional origin statistics.

Requires known project and personal test facts. Use --project-uri/--personal-uri
for stronger evidence that the specific sentinels were recalled. No capture or
commit is performed. No session_id is sent, avoiding recall-ledger side effects.
"""
import argparse
import sys

from ov_api import ApiError, Client, canonical_uri, uri_parts

QUOTAS = {"events": 3, "entities": 3, "preferences": 3, "experiences": 3, "resources": 2, "skills": 2}


def classify(uri, user):
    parts = uri_parts(uri)
    if parts[0] == "resources" or (parts[0] == "agent" and parts[1] in ("skills", "memories")):
        return "global", None
    if parts[:2] != ["user", user]:
        raise ValueError("Result belongs to another/unknown user namespace")
    if len(parts) >= 4 and parts[2] in ("memories", "skills", "resources"):
        return "self", None
    if len(parts) >= 6 and parts[2] == "peers" and parts[4] in ("memories", "skills", "resources"):
        return "peer", parts[3]
    raise ValueError("Result has unknown memory origin")


def validate_result(result, *, user, peer, scope, actor, expect_peer=None, expect_self=False,
                    required_uri=None):
    if not isinstance(result, dict) or not isinstance(result.get("entries"), list):
        raise ValueError("Search response lacks an entries array")
    entries = result["entries"]
    found_peer = found_self = False
    uris = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Malformed search entry")
        uri = canonical_uri(entry.get("uri"))
        kind, origin = classify(uri, user)
        uris.add(uri)
        if scope == "actor" and kind == "peer" and origin != actor:
            raise ValueError(f"Cross-project result: {uri}")
        found_peer |= kind == "peer" and origin == peer
        found_self |= kind == "self"
    origins = (result.get("stats") or {}).get("origins")
    # Stats are diagnostic only. An absent field must never waive URI checks;
    # explicit nonzero cross-peer stats are still grounds to fail.
    if scope == "actor" and isinstance(origins, dict) and origins.get("other_peer", 0) != 0:
        raise ValueError("Server stats report other-peer content")
    if expect_peer is not None and found_peer != expect_peer:
        raise ValueError("Expected project hit/miss was not observed")
    if expect_self and not found_self:
        raise ValueError("No user-level personal result was observed")
    if required_uri and canonical_uri(required_uri) not in uris:
        raise ValueError("Known sentinel URI was not recalled; result is inconclusive")
    return len(entries)


def run_checks(client, args):
    matrix = [
        ("all/no actor: project hit", args.query_project, "all", None, True, False, args.project_uri),
        ("actor/current: project hit", args.query_project, "actor", args.peer, True, False, args.project_uri),
        ("actor/other: project excluded", args.query_project, "actor", args.other, False, False, None),
        ("actor/other: personal shared", args.query_personal, "actor", args.other, None, True, args.personal_uri),
        ("actor/current: personal shared", args.query_personal, "actor", args.peer, None, True, args.personal_uri),
    ]
    failed = 0
    for label, query, scope, actor, want_peer, want_self, sentinel in matrix:
        try:
            response = client.request("/api/v1/search/search", body={
                "query": query, "mode": "context", "max_tokens": 3000,
                "peer_scope": scope, "quotas": QUOTAS,
            }, actor=actor)
            count = validate_result(response["result"], user=args.user, peer=args.peer, scope=scope,
                                    actor=actor, expect_peer=want_peer, expect_self=want_self, required_uri=sentinel)
            print(f"[PASS] {label}: {count} result URIs checked")
        except (ApiError, ValueError, TypeError) as error:
            failed += 1
            print(f"[FAIL] {label}: {error}")
    print(f"Result: {5 - failed}/5 passed. Automatic recall API only; MCP/GUI require separate acceptance.")
    if not args.project_uri or not args.personal_uri:
        print("Note: sentinel URIs not both supplied; positive hits prove scope only, not exact fact recall.")
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://127.0.0.1:1933")
    ap.add_argument("--user", default="default")
    ap.add_argument("--peer", default="deepseek-harness")
    ap.add_argument("--other", default="other-project")
    ap.add_argument("--query-project", default="TTS 语音合成故障")
    ap.add_argument("--query-personal", default="用户用什么操作系统")
    ap.add_argument("--project-uri")
    ap.add_argument("--personal-uri")
    ap.add_argument("--timeout", type=float, default=30)
    args = ap.parse_args()
    try:
        for value in (args.user, args.peer, args.other):
            if len(uri_parts("viking://user/" + value)) != 2:
                raise ValueError("User/peer IDs must be single URI components")
        if args.peer == args.other:
            raise ValueError("The test peers must differ")
        return run_checks(Client(args.base, args.timeout), args)
    except (ApiError, ValueError) as error:
        print(f"Verification FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
