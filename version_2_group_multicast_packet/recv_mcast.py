#!/usr/bin/env python3.10
import socket
import struct
import sys
import time
import platform

GROUP = "239.1.1.1"
PORT = 5000
LISTEN_TIME = 5  # seconds

def main():
    hostname = platform.node()
    print(f"[{hostname}] Listening for multicast on {GROUP}:{PORT} for {LISTEN_TIME}s...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", PORT))

    mreq = struct.pack("4sl", socket.inet_aton(GROUP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(LISTEN_TIME)

    try:
        data, addr = sock.recvfrom(1024)
        msg = data.decode().strip()
        print(f"[{hostname}] ✅ Received multicast from {addr[0]}: '{msg}'")
    except socket.timeout:
        print(f"[{hostname}] ❌ No multicast received.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
