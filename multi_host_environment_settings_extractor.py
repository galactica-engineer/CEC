import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ---------------- Parsing ----------------
def parse_ifconfig(output):
    """Parse ifconfig output into a structured dictionary."""
    interfaces = {}
    blocks = re.split(r'\n(?=\S)', output.strip())  # split on new interface blocks

    for block in blocks:
        lines = block.splitlines()
        if not lines:
            continue

        iface_line = lines[0]
        iface_name = iface_line.split(":")[0].strip()

        iface_data = {
            "flags": None,
            "inet": None,
            "inet6": None,
            "mac": None,
        }

        # Extract flags
        flags_match = re.search(r"<([^>]+)>", iface_line)
        if flags_match:
            iface_data["flags"] = flags_match.group(1).split(",")

        # Extract inet, inet6, mac
        for line in lines[1:]:
            if "inet " in line:
                match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
                if match:
                    iface_data["inet"] = match.group(1)
            elif "inet6 " in line:
                match = re.search(r"inet6 ([0-9a-f:]+)", line)
                if match:
                    iface_data["inet6"] = match.group(1)
            elif "ether " in line:
                match = re.search(r"ether ([0-9a-f:]+)", line)
                if match:
                    iface_data["mac"] = match.group(1)

        interfaces[iface_name] = iface_data

    return interfaces


def parse_route(output):
    """Parse 'route -n' output into a list of dictionaries."""
    routes = []
    lines = output.strip().splitlines()

    # Skip header lines until we find the actual routing table
    for i, line in enumerate(lines):
        if line.startswith("Destination"):
            header_index = i
            break
    else:
        return routes  # no valid table found

    # Process the table lines after header
    for line in lines[header_index + 1:]:
        parts = line.split()
        if len(parts) >= 8:
            route_entry = {
                "destination": parts[0],
                "gateway": parts[1],
                "genmask": parts[2],
                "flags": parts[3],
                "metric": int(parts[4]),
                "ref": int(parts[5]),
                "use": int(parts[6]),
                "iface": parts[7],
            }
            routes.append(route_entry)

    return routes


# ---------------- File Handling ----------------
def load_hosts(json_file):
    """Load list of hosts from a JSON file."""
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
        return data.get("hosts", [])
    except Exception as e:
        print(f"[ERROR] Reading {json_file}: {e}")
        return []


def prepare_output_directory(directory_name="current_extraction_jsons"):
    """
    Create/refresh an output directory relative to script location.
    Example: ./current_extraction_jsons/
    """
    output_dir = Path(__file__).parent / directory_name

    if output_dir.exists():
        shutil.rmtree(output_dir)

    output_dir.mkdir()
    return output_dir


def save_to_json(data, hostname, output_dir):
    """Save parsed data to JSON with a timestamp in the filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"{hostname}_{timestamp}.json"
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print(f"[OK] Saved parsed data from {hostname} to {filename}")
    except Exception as e:
        print(f"[ERROR] Saving {hostname} data: {e}")


# ---------------- Remote Execution ----------------
def ssh_command(host, command):
    """Run a command over SSH and return its output, or None on failure."""
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-i", os.path.expanduser("~/.ssh/id_rsa"),
        host,
        command,
    ]
    try:
        return subprocess.check_output(ssh_cmd, text=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] SSH to {host}: {e}")
        return None


def get_ifconfig(host):
    """Get and parse ifconfig output from a remote host."""
    raw_output = ssh_command(host, "/usr/sbin/ifconfig")
    if raw_output:
        return parse_ifconfig(raw_output)
    return None


def get_routes(host):
    """Get and parse route -n output from a remote host."""
    raw_output = ssh_command(host, "/sbin/route -n")
    if raw_output:
        return parse_route(raw_output)
    return None


# ---------------- Comparison ----------------
def strip_timestamp(filename):
    """
    Strip timestamp from a filename like 'host_ifconfig_YYYYMMDD_HHMMSS.json'.
    Returns 'host_ifconfig'.
    """
    return re.sub(r"_\d{8}_\d{6}\.json$", "", filename)


def compare_json_files(base_file, new_file):
    """Compare two JSON files and return True if identical, else False."""
    try:
        with open(base_file, "r") as f1, open(new_file, "r") as f2:
            base_data = json.load(f1)
            new_data = json.load(f2)
        return base_data == new_data
    except Exception as e:
        print(f"[ERROR] Comparing {base_file} and {new_file}: {e}")
        return False

def find_base_file(base_dir, key):
    """Find base file ignoring timestamp, prefer latest if multiple exist."""
    pattern = f"{key}*.json"
    matches = sorted(Path(base_dir).glob(pattern))
    if matches:
        return matches[-1]  # latest (by sort order)
    return None

def compare_extractions(base_dir, new_dir, output_dir):
    """
    Compare new extraction JSON files against base values.
    Print pass/fail per host and save results into a JSON summary.
    """
    results = {}

    new_files = list(Path(new_dir).glob("*.json"))
    for new_file in new_files:
        key = strip_timestamp(new_file.name)

	base_file = find_base_file(base_dir, key)
	if not base_file:
    	    results[key] = "MISSING_BASE"
#    	    print(f"[WARN] No base file for {key}")
    	    continue

        match = compare_json_files(base_file, new_file)
        results[key] = "PASS" if match else "FAIL"
#        print(f"[{results[key]}] {key}")

    # Save results summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = Path(output_dir) / f"comparison_summary_{timestamp}.json"
    try:
        with open(summary_file, "w") as f:
            json.dump(results, f, indent=4)
        print(f"[OK] Comparison results saved to {summary_file}")
    except Exception as e:
        print(f"[ERROR] Saving comparison summary: {e}")

    return results

# ---------------- Main ----------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python launcher.py <hosts.json>")
        sys.exit(1)

    hosts_file = Path(sys.argv[1])

    if not hosts_file.exists():
        print(f"[ERROR] File not found: {hosts_file}")
        sys.exit(1)

    hosts = load_hosts(hosts_file)
    if not hosts:
        print("[ERROR] No hosts found in file.")
        sys.exit(1)

    output_dir = prepare_output_directory("current_extraction_jsons")

    for host in hosts:
        print(f"[*] Connecting to {host}...")

	# --- ifconfig ---
        parsed_ifconfig = get_ifconfig(host)
        if parsed_ifconfig:
            save_to_json(parsed_ifconfig, f"{host}_ifconfig", output_dir)

	# --- route -n ---
        parsed_routes = get_routes(host)
        if parsed_routes:
            save_to_json(parsed_routes, f"{host}_routes", output_dir)

    # Run comparison against base values if directory exists
    base_dir = Path(__file__).parent / "base_value_jsons"
    if base_dir.exists():
	print("\n=== Camparison Summary ===")
        results = compare_extractions(base_dir, output_dir, output_dir)

        # Print all host results at once
        for key, status in results.items():
            print(f"[{status}] {key}")
    else:
        print("[WARN] No base_value_jsons directory found. Skipping comparison.")


if __name__ == "__main__":
    main()
