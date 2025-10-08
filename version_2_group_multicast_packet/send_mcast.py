#!/usr/bin/env python3.10
import socket
import sys
import time
import platform

GROUP = "239.1.1.1"
PORT = 5000
MESSAGE = f"Multicast test from {platform.node()}"

def main():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        ttl = 2
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        sock.sendto(MESSAGE.encode(), (GROUP, PORT))
        print(f"[SENDER] Sent multicast: '{MESSAGE}' to {GROUP}:{PORT}")
    except Exception as e:
        print(f"[SENDER] Error sending multicast: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
