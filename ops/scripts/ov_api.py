"""Small, strict standard-library client for the OpenViking 0.5.1.1 HTTP API."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request


class ApiError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ApiError("API redirect refused; check --base", code)


def uri_parts(uri):
    if not isinstance(uri, str) or not uri.startswith("viking://"):
        raise ValueError("Expected a canonical viking:// URI")
    parts = uri.removeprefix("viking://").rstrip("/").split("/")
    if any(not p or urllib.parse.unquote(p) in (".", "..")
           or any(c in urllib.parse.unquote(p) for c in ("/", "\\", "\x00"))
           or any(ord(c) < 32 for c in p) for p in parts):
        raise ValueError("Unsafe URI component")
    if len(parts) < 2:
        raise ValueError("URI must identify a namespace and path")
    return parts


def canonical_uri(uri):
    return "viking://" + "/".join(uri_parts(uri))


def within(uri, root):
    p, r = uri_parts(uri), uri_parts(root)
    return p[:len(r)] == r


class Client:
    def __init__(self, base="http://127.0.0.1:1933", timeout=30):
        parsed = urllib.parse.urlsplit(base)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("--base must be an HTTP(S) API URL without credentials/query")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.base, self.timeout = base.rstrip("/"), timeout
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, path, *, params=None, body=None, actor=None):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"Content-Type": "application/json"}
        key = os.environ.get("OPENVIKING_API_KEY")
        if key:
            headers["Authorization"] = "Bearer " + key
        if actor:
            headers["X-OpenViking-Actor-Peer"] = actor
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        request = urllib.request.Request(url, data=data, headers=headers, method="GET" if body is None else "POST")
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            raise ApiError(f"API HTTP {error.code} at {path}", error.code) from None
        except (OSError, ValueError) as error:
            raise ApiError(f"API request failed at {path}: {type(error).__name__}") from None
        if not isinstance(result, dict) or result.get("status") != "ok" or "result" not in result:
            raise ApiError(f"Invalid/error API response at {path}")
        return result

    def listing(self, uri):
        """Consume every page. Never treat absent pagination/type fields as empty."""
        uri = canonical_uri(uri)
        seen, offset = set(), 0
        for _ in range(10000):
            page = self.request("/api/v1/fs/ls", params={
                "uri": uri, "recursive": "false", "output": "original",
                "show_all_hidden": "true", "include_abstract": "false",
                "node_limit": 500, "offset": offset, "sort_by": "name", "sort_order": "asc",
            })
            items = page["result"]
            if not isinstance(items, list) or type(page.get("has_more")) is not bool:
                raise ApiError("Listing lacks entries or has_more; export completeness is unknown")
            for item in items:
                if not isinstance(item, dict) or type(item.get("isDir")) is not bool:
                    raise ApiError("Listing lacks isDir; refusing to guess from filename")
                child = canonical_uri(item.get("uri"))
                if not within(child, uri) or len(uri_parts(child)) != len(uri_parts(uri)) + 1 or child in seen:
                    raise ApiError("Invalid, repeated or out-of-directory listing entry")
                seen.add(child)
                yield {**item, "uri": child}
            if not page["has_more"]:
                return
            if not items:
                raise ApiError("Empty listing page still has_more")
            offset += len(items)
        raise ApiError("Listing exceeded page limit; export aborted")

    def read(self, uri):
        result = self.request("/api/v1/content/read", params={"uri": canonical_uri(uri), "raw": "true"})["result"]
        if not isinstance(result, str):
            raise ApiError("Raw content response is not text")
        return result
