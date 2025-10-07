#!/usr/bin/env python3
"""
mcast_manager.py

Requirements:
- python3 on local and remote hosts
- ssh and scp available locally
- ssh access to target hosts (key-based recommended)

What it does:
- Copies send_mcast.py and recv_mcast.py to /tmp on each host
- For each host in HOSTS, treats it as the sender:
    - starts recv_mcast.py on all other hosts (background, saves PID to /tmp/recv_mcast.pid)
    - runs send_mcast.py on the sender host (foreground, captures output)
    - collects /tmp/recv_mcast.log from all receivers
    - kills remote receivers and cleans up /tmp files
- Stores per-round logs locally under ./results/<sender-host>/
"""
import subprocess
import os
import time
import sys
from pathlib import Path

# ========== CONFIGURE ==========
SSH_USER = "youruser"   # replace with your ssh username
HOSTS = [
    "host1.example.com",
    "host2.example.com",
    "host3.example.com",
    "host4.example.com",
    "host5.example.com",
    "host6.example.com",
    "host7.example.com",
    "host8.example.com",
]
REMOTE_DIR = "/tmp"
SEND_SCRIPT = "send_mcast.py"
RECV_SCRIPT = "recv_mcast.py"
GROUP = "239.1.1.1"
PORT = 5000
# ===============================

def run(cmd, capture=False):
    if capture:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
    else:
        return subprocess.call(cmd, shell=True)

def scp_to(host, local_path, remote_path):
    cmd = f"scp {local_path} {SSH_USER}@{host}:{remote_path}"
    print("SCP ->", cmd)
    return run(cmd)

def ssh(host, remote_cmd, capture=False):
    ssh_cmd = f"ssh {SSH_USER}@{host} \"{remote_cmd}\""
    print("SSH ->", ssh_cmd)
    return run(ssh_cmd, capture=capture)

def start_receivers(sender):
    print(f"Starting receivers (excluding sender: {sender})")
    for h in HOSTS:
        if h == sender:
            continue
        # remote logfile and pidfile
        remote_log = f"{REMOTE_DIR}/recv_mcast.log"
        remote_pid = f"{REMOTE_DIR}/recv_mcast.pid"
        # start in background with nohup and save PID
        cmd = (
            f"nohup python3 {REMOTE_DIR}/{RECV_SCRIPT} --group {GROUP} --port {PORT} --log {remote_log} "
            f"> /dev/null 2>&1 & echo $! > {remote_pid}"
        )
        ssh(h, cmd)
        time.sleep(0.05)

def stop_receivers_and_collect(sender, results_dir):
    print("Collecting logs and stopping receivers")
    Path(results_dir).mkdir(parents=True, exist_ok=True)
    for h in HOSTS:
        if h == sender:
            continue
        remote_log = f"{REMOTE_DIR}/recv_mcast.log"
        remote_pid = f"{REMOTE_DIR}/recv_mcast.pid"
        local_log = os.path.join(results_dir, f"{h}_recv.log")
        # scp the log if exists (ignore errors)
        try:
            scp_to(h, remote_log, local_log)  # scp local_path remote: but here we call reversed, fix:
        except Exception:
            pass
        # because scp_to above expects local->remote, do a direct scp pull here:
        try:
            cmd = f"scp {SSH_USER}@{h}:{remote_log} {local_log}"
            run(cmd)
        except Exception:
            pass
        # kill the receiver process if pid file exists
        try:
            out = ssh(h, f"if [ -f {remote_pid} ]; then kill \"$(cat {remote_pid})\" 2>/dev/null || true; fi; rm -f {remote_pid} {remote_log}")
        except Exception:
            pass

def run_sender(sender):
    print("Running sender on", sender)
    cmd = f"python3 {REMOTE_DIR}/{SEND_SCRIPT} --group {GROUP} --port {PORT}"
    # run and capture output
    out = ssh(sender, cmd, capture=True)
    return out

def deploy_scripts():
    print("Copying scripts to all hosts")
    for h in HOSTS:
        scp_to(h, SEND_SCRIPT, f"{REMOTE_DIR}/{SEND_SCRIPT}")
        scp_to(h, RECV_SCRIPT, f"{REMOTE_DIR}/{RECV_SCRIPT}")

def main():
    # simple pre-check
    if SSH_USER == "youruser":
        print("Edit SSH_USER in the script before running.")
        sys.exit(1)
    deploy_scripts()
    base_results = Path("results")
    base_results.mkdir(exist_ok=True)
    for sender in HOSTS:
        print("="*60)
        print("Sender round:", sender)
        results_dir = base_results / sender
        results_dir.mkdir(exist_ok=True)
        start_receivers(sender)
        # give receivers a bit to join group
        time.sleep(2)
        sender_out = run_sender(sender)
        # write sender output
        with open(results_dir / "sender_output.txt", "w") as f:
            f.write(sender_out or "")
        # wait a moment for receivers to log
        time.sleep(1)
        stop_receivers_and_collect(sender, str(results_dir))
        print(f"Round for sender {sender} complete. Logs in {results_dir}")
        time.sleep(1)

if __name__ == "__main__":
    main()
