#!/usr/bin/env python3
"""
recv_mcast.py
Usage: python3 recv_mcast.py [--group GROUP] [--port PORT] [--log LOGFILE]
This will block and print received messages; intended to be run in background (nohup).
"""
import socket
import struct
import argparse
import time

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--group", default="239.1.1.1")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--log", default=None)
    args = p.parse_args()

    mcast_grp = args.group
    mcast_port = args.port

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # allow reuse
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # bind to the multicast group address and port
    try:
        sock.bind((mcast_grp, mcast_port))
    except Exception:
        # Some kernels require binding to '' instead
        sock.bind(('', mcast_port))

    mreq = struct.pack("4sl", socket.inet_aton(mcast_grp), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    prefix = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
    out = []
    while True:
        data, addr = sock.recvfrom(4096)
        line = f"{prefix}RECV from {addr}: {data.decode(errors='replace')}"
        if args.log:
            with open(args.log, "a") as f:
                f.write(line + "\n")
        else:
            print(line)

if __name__ == "__main__":
    main()
