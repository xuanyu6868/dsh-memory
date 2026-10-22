#!/usr/bin/env python3
"""Accept TCP but return no response; test total Harness waiting, not just HTTP.

Default: loopback port 1933, manual stop. This helper never stops/starts launchd.
8000ms limits only the context request, NOT initialization, fallback, legacy-peer
retrieval or the whole pre-step hook. Test both initialized and brand-new sessions.
See docs/deployment/HANDOFF.md for bounded local operation and recovery steps.
"""
import argparse
import select
import socketserver
import threading
import time


class BlackholeServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False

    def __init__(self, address, *, hold=0, max_connections=64):
        self.hold = hold
        self.stopping = threading.Event()
        self.slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, BlackholeHandler)

    def verify_request(self, request, client_address):
        return self.slots.acquire(blocking=False)


class BlackholeHandler(socketserver.BaseRequestHandler):
    def handle(self):
        started = time.monotonic()
        try:
            while not self.server.stopping.is_set():
                if self.server.hold and time.monotonic() - started >= self.server.hold:
                    return
                readable, _, _ = select.select([self.request], [], [], 0.1)
                if readable and not self.request.recv(65536):
                    return  # Client cancelled/timed out: release socket and slot.
                # Discard request bytes; no HTTP response and no body logging.
        except OSError:
            pass
        finally:
            self.server.slots.release()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1933)
    ap.add_argument("--hold", type=float, default=0, help="Close each connection after N seconds; 0 waits for disconnect")
    ap.add_argument("--duration", type=float, default=0, help="Stop helper after N seconds; 0 means Ctrl-C")
    args = ap.parse_args()
    if args.hold < 0 or args.duration < 0:
        ap.error("hold/duration must be nonnegative")
    srv = BlackholeServer((args.host, args.port), hold=args.hold)
    timer = None
    if args.duration:
        def stop():
            srv.stopping.set()
            srv.shutdown()
        timer = threading.Timer(args.duration, stop)
        timer.daemon = True
        timer.start()
    print(f"Blackhole listening at {args.host}:{srv.server_address[1]}; returns no HTTP response", flush=True)
    try:
        srv.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        if timer:
            timer.cancel()
        srv.stopping.set()
        srv.server_close()
        print("Blackhole stopped. Restore/check the real service before continuing.", flush=True)


if __name__ == "__main__":
    main()
