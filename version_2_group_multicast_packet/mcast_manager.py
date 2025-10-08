#!/usr/bin/env python3.10
import subprocess
import time
import sys
import os

# --- Configuration ---
USER = "yourusername"   # <-- change this
HOSTS = ["host1", "host2", "host3", "host4", "host5", "host6", "host7", "host8"]
REMOTE_DIR = "~/mcast_test"
GROUP = "239.1.1.1"
PORT = 5000

SEND_SCRIPT = "send_mcast.py"
RECV_SCRIPT = "recv_mcast.py"

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def scp_to(host, filename):
    cmd = f"scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {filename} {USER}@{host}:{REMOTE_DIR}/"
    return run_cmd(cmd)

def ssh(host, command):
    cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {USER}@{host} '{command}'"
    return run_cmd(cmd)

def ensure_remote_dir(host):
    ssh(host, f"mkdir -p {REMOTE_DIR}")

def main():
    print("=== Multicast Test Orchestrator ===")

    # --- Copy scripts to all hosts ---
    for host in HOSTS:
        print(f"\nCopying scripts to {host}...")
        ensure_remote_dir(host)
        scp_to(host, SEND_SCRIPT)
        scp_to(host, RECV_SCRIPT)

    # --- Main test loop ---
    for sender in HOSTS:
        receivers = [h for h in HOSTS if h != sender]
        print(f"\n=== Round: Sender = {sender} ===")

        # Start receivers
        recv_procs = {}
        for r in receivers:
            cmd = f"cd {REMOTE_DIR} && python3.10 {RECV_SCRIPT}"
            recv_procs[r] = subprocess.Popen(
                f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {USER}@{r} '{cmd}'",
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

        time.sleep(2)  # Give receivers time to start

        # Send from sender
        print(f"Sending multicast from {sender}...")
        send_cmd = f"cd {REMOTE_DIR} && python3.10 {SEND_SCRIPT}"
        ssh(sender, send_cmd)

        time.sleep(6)  # Allow receivers to finish

        # Collect receiver output
        print("\nResults:")
        for r, proc in recv_procs.items():
            try:
                out, err = proc.communicate(timeout=2)
                if "[✅" in out or "✅" in out:
                    print(f"  ✅ {r} received message")
                else:
                    print(f"  ❌ {r} missed message")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"  ⚠️  {r} did not respond in time")

        print("\n----------------------------------------")

if __name__ == "__main__":
    main()
