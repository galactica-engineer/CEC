#!/usr/bin/env python3
"""
send_mcast.py
Usage: python3 send_mcast.py [--iface IFACE_IP] [--group GROUP] [--port PORT] [--msg MESSAGE]
"""
import socket
import argparse

def get_primary_ip():
    # Attempt to find primary interface by connecting to a public IP (no traffic sent).
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--iface", help="Interface IP to send from")
    p.add_argument("--group", default="239.1.1.1")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--msg", default="hello multicast")
    args = p.parse_args()

    iface_ip = args.iface or get_primary_ip()
    mcast_grp = args.group
    mcast_port = args.port
    message = args.msg.encode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # TTL 1 keeps it local to the subnet
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(iface_ip))
    except Exception:
        # fallback: don't set IF if it fails
        pass

    sock.sendto(message, (mcast_grp, mcast_port))
    print(f"SENT: {message.decode()} -> {mcast_grp}:{mcast_port} from {iface_ip}")

if __name__ == "__main__":
    main()
