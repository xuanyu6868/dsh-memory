#!/usr/bin/env python3
"""Validate a memory content export. No network or writes unless --apply is set.

Use --target-root to restore into a disposable test subtree first. Content writes
use mode=create and vectors_only, never replace or delete existing memory. This
rebuilds file vectors through the server API; ACL, tags, profiles and sessions
are outside this export's scope. Live-server recovery remains a local acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from ov_api import ApiError, Client, canonical_uri, uri_parts, within


def load_export(directory):
    directory = Path(directory).expanduser().resolve(strict=True)
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("format") != "dsh-memory-content-v1" or manifest.get("complete") is not True:
        raise ValueError("Unsupported or incomplete export")
    roots, entries = manifest.get("roots"), manifest.get("files")
    if not isinstance(roots, list) or not roots or not isinstance(entries, list) or not entries or manifest.get("expected_files") != len(entries):
        raise ValueError("Export count/roots are incomplete")
    roots = [canonical_uri(r) for r in roots]
    if any(uri_parts(r)[0] != "user" or "memories" not in uri_parts(r)[2:] for r in roots):
        raise ValueError("Export roots must be user/peer memory trees")
    seen_uris, seen_paths, verified = set(), set(), []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Malformed manifest entry")
        uri = canonical_uri(entry.get("uri"))
        path = entry.get("path")
        if not isinstance(path, str) or Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("Unsafe export file path")
        source = (directory / path).resolve(strict=True)
        if not source.is_relative_to(directory) or not source.is_file():
            raise ValueError("Export path escapes its directory")
        if uri in seen_uris or source in seen_paths or not any(within(uri, r) and uri != r for r in roots):
            raise ValueError("Duplicate/out-of-scope export entry")
        data = source.read_bytes()
        if entry.get("bytes") != len(data) or entry.get("sha256") != hashlib.sha256(data).hexdigest():
            raise ValueError("Export checksum mismatch")
        verified.append((uri, data.decode("utf-8")))
        seen_uris.add(uri); seen_paths.add(source)
    return roots, verified


def plan_restore(directory, target_root=None):
    roots, entries = load_export(directory)
    if target_root:
        target_root = canonical_uri(target_root)
        p = uri_parts(target_root)
        if p[0] != "user" or "memories" not in p[2:] or p.index("memories", 2) == len(p) - 1:
            raise ValueError("--target-root must be a subtree INSIDE a memory root, e.g. .../memories/restore-test")
    plan = []
    for uri, text in entries:
        # Root index prevents identical relative filenames in two projects colliding.
        root = next(r for r in sorted(roots, key=len, reverse=True) if within(uri, r))
        relative = "/".join(uri_parts(uri)[len(uri_parts(root)):])
        target = f"{target_root}/root-{roots.index(root)}/{relative}" if target_root else uri
        plan.append((canonical_uri(target), text))
    return plan


def apply_restore(client, plan):
    # Callers must explicitly pass --apply. Refuse all conflicting content before
    # writing any file; create mode also protects against a later racing writer.
    pending, skipped = [], 0
    for uri, text in plan:
        try:
            current = client.read(uri)
        except ApiError as error:
            if error.status != 404:
                raise
            pending.append((uri, text))
        else:
            if current != text:
                raise ValueError(f"Target already contains different content: {uri}")
            skipped += 1
    for uri, text in pending:
        client.request("/api/v1/content/write", body={"uri": uri, "content": text, "mode": "create", "wait": True, "processing_mode": "vectors_only"})
        if client.read(uri) != text:
            raise ApiError("Restored content differs from export; stop and inspect server")
    return len(pending), skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="directory", required=True)
    ap.add_argument("--base", default="http://127.0.0.1:1933")
    ap.add_argument("--target-root", help="Optional disposable memory subtree for a restore rehearsal")
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--apply", action="store_true", help="Explicitly create server files after all checks pass")
    args = ap.parse_args()
    try:
        plan = plan_restore(args.directory, args.target_root)
        print(f"Integrity OK: {len(plan)} files. Mode: {'APPLY (create only)' if args.apply else 'DRY RUN (no network/writes)'}")
        if args.apply:
            created, skipped = apply_restore(Client(args.base, args.timeout), plan)
            print(f"Restored/read-back verified: {created}; identical targets skipped: {skipped}")
        else:
            for uri, _ in plan:
                print(uri)
        return 0
    except (ApiError, ValueError, OSError, KeyError, TypeError) as error:
        print(f"Restore FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
