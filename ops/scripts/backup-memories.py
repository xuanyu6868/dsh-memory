#!/usr/bin/env python3
"""Export user + every project memory tree with raw text and a SHA256 manifest.

Default scope: <user>/memories and <user>/peers/*/memories. This is a memory
content export, not an atomic disaster-recovery snapshot or an index/config backup.
Use repeated --root for explicit scopes. Destination must not already exist.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.parse

from ov_api import ApiError, Client, canonical_uri, uri_parts, within

GENERATED = {".abstract.md", ".overview.md"}


def discover_roots(client, user_root):
    user_root = canonical_uri(user_root)
    if len(uri_parts(user_root)) != 2 or uri_parts(user_root)[0] != "user":
        raise ValueError("--user-root must be viking://user/<user>")
    children = {i["uri"].rsplit("/", 1)[-1]: i for i in client.listing(user_root)}
    roots = []
    if children.get("memories", {}).get("isDir"):
        roots.append(user_root + "/memories")
    if children.get("peers", {}).get("isDir"):
        for peer in client.listing(user_root + "/peers"):
            if not peer["isDir"]:
                continue
            for entry in client.listing(peer["uri"]):
                if entry["isDir"] and entry["uri"].rsplit("/", 1)[-1] == "memories":
                    roots.append(entry["uri"])
    if not roots:
        raise ApiError("No memory roots discovered; refusing a misleading empty backup")
    return sorted(roots)


def walk_files(client, root, depth=0):
    if depth > 64:
        raise ApiError("Memory tree exceeded depth limit; export aborted")
    for item in client.listing(root):
        if item["isDir"]:
            yield from walk_files(client, item["uri"], depth + 1)
        elif item["uri"].rsplit("/", 1)[-1] not in GENERATED:
            yield item["uri"]


def save_manifest(out, manifest):
    pending = out / "manifest.tmp"
    pending.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    pending.chmod(0o600)
    pending.replace(out / "manifest.json")


def export(client, out, roots):
    roots = sorted(set(canonical_uri(r) for r in roots))
    if not roots or any(uri_parts(r)[0] != "user" or "memories" not in uri_parts(r)[2:] for r in roots):
        raise ValueError("Backup roots must be explicit user/peer memory trees")
    files = sorted(set(uri for root in roots for uri in walk_files(client, root)))
    if not files:
        raise ApiError("No memory files found; nothing exported")
    out = Path(out).expanduser()
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    manifest = {"format": "dsh-memory-content-v1", "created_at": datetime.now(timezone.utc).isoformat(),
                "complete": False, "roots": roots, "expected_files": len(files), "files": [],
                "excluded": ["generated directory summaries", "indexes", "ACL/tags", "sessions", "configuration", "profiles outside selected memory roots"]}
    save_manifest(out, manifest)
    try:
        for uri in files:
            data = client.read(uri).encode("utf-8")
            rel = "files/" + "/".join(urllib.parse.quote(p, safe="-_.") for p in uri_parts(uri))
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_bytes(data)
            target.chmod(0o600)
            manifest["files"].append({"uri": uri, "path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
            save_manifest(out, manifest)
        manifest["complete"] = True
        save_manifest(out, manifest)
    except Exception:
        # A partially written directory stays visibly incomplete and cannot restore.
        save_manifest(out, manifest)
        raise
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://127.0.0.1:1933")
    ap.add_argument("--user-root", default="viking://user/default")
    ap.add_argument("--root", action="append", help="Explicit memory subtree; repeat to include multiple roots")
    ap.add_argument("--out", required=True, help="New local directory, outside this repository")
    ap.add_argument("--timeout", type=float, default=30)
    args = ap.parse_args()
    try:
        client = Client(args.base, args.timeout)
        roots = args.root or discover_roots(client, args.user_root)
        result = export(client, args.out, roots)
        print(f"Complete content export: {len(roots)} roots, {len(result['files'])} files. Manifest: {Path(args.out).expanduser() / 'manifest.json'}")
        return 0
    except (ApiError, ValueError, OSError) as error:
        print(f"Backup FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
