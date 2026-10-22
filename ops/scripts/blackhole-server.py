#!/usr/bin/env python3
"""黑洞服务：接受 TCP 连接但永不返回响应，用于模拟"记忆服务挂起"。

用途：验证 DSH 记忆插件在服务端挂起时的降级行为——pre-step 检索应在
recallContextTimeoutMs（当前配置 8000ms）后放弃，聊天/语音继续，
而不是无限等待（docs/deployment/findings.md 与 acceptance.md 待办项）。

用法:
    1. 停掉真实服务:  launchctl bootout gui/$(id -u)/ai.openviking.server
    2. 起黑洞:        python3 blackhole-server.py --port 1933
    3. 在 DSH 会话发一条消息，观察等待时长与降级行为
    4. Ctrl-C 停黑洞，恢复真实服务:
       launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.openviking.server.plist

可选: --hold N 表示每个连接hold N 秒后主动关闭（默认 0 = 永不返回）。
"""
import argparse
import socket
import threading
import time


def hold_conn(conn, addr, hold):
    try:
        conn.settimeout(None)
        if hold > 0:
            time.sleep(hold)
        else:
            while True:
                time.sleep(3600)
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1933)
    ap.add_argument("--hold", type=float, default=0, help="每连接hold秒数，0=永不返回")
    args = ap.parse_args()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(64)
    print(f"blackhole listening on {args.host}:{args.port} (hold={'forever' if args.hold == 0 else str(args.hold) + 's'})")
    try:
        while True:
            conn, addr = srv.accept()
            print(f"[{time.strftime('%H:%M:%S')}] accepted {addr[0]}:{addr[1]} (holding, no response)")
            threading.Thread(target=hold_conn, args=(conn, addr, args.hold), daemon=True).start()
    except KeyboardInterrupt:
        print("\nblackhole stopped")
    finally:
        srv.close()


if __name__ == "__main__":
    main()
