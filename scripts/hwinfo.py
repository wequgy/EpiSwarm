#!/usr/bin/env python3
"""Hardware probe CLI tool for EpiSwarm Studio (Stage R3.2).

Reports logical/physical cores, RAM, free memory, GPU model and memory (via nvidia-smi / torch),
Python and NumPy build info, recommended worker counts, and agent capacity limits.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from episwarm.system.hardware import probe_hardware, estimate_resources


def main() -> None:
    parser = argparse.ArgumentParser(description="EpiSwarm Hardware & Resource Probe")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    parser.add_argument("--estimate", nargs=3, type=int, metavar=("AGENTS", "DAYS", "REPLICATES"),
                        help="Estimate memory and time requirements for a run configuration")
    args = parser.parse_args()

    info = probe_hardware()

    if args.estimate:
        agents, days, reps = args.estimate
        info["estimate"] = estimate_resources(agents, days, reps)

    if args.json:
        print(json.dumps(info, indent=2))
        return

    print("==================================================")
    print("        EpiSwarm System Hardware Probe            ")
    print("==================================================")
    cpu = info["cpu"]
    print(f"CPU Physical Cores : {cpu['physical_cores']}")
    print(f"CPU Logical Cores  : {cpu['logical_cores']}")
    print(f"Architecture       : {cpu['architecture']}")

    mem = info["memory"]
    print(f"Total RAM          : {mem['total_gb']} GB")
    print(f"Available RAM      : {mem['available_gb']} GB")
    print(f"Peak Memory Budget : {mem['budget_limit_gb']} GB (target cap: 11 GB)")

    gpu = info["gpu"]
    if gpu["available"]:
        print(f"GPU Model          : {gpu['name']}")
        print(f"GPU VRAM Total     : {gpu['total_memory_mb']} MB (Free: {gpu['free_memory_mb']} MB)")
        print(f"GPU Driver Version : {gpu.get('driver_version', 'N/A')}")
    else:
        print(f"GPU Status         : Not detected / unavailable ({gpu.get('note', '')})")

    rt = info["runtime"]
    py_ver = rt["python_version"].split()[0]
    print(f"Python Runtime     : {py_ver} ({rt['python_implementation']})")
    print(f"NumPy Version      : {rt['numpy']['version']}")

    rec = info["recommendations"]
    print("--------------------------------------------------")
    print("Engine Recommendations:")
    print(f"  Recommended Workers : {rec['recommended_workers']} (physical cores - 1)")
    print(f"  Max Concurrent      : {rec['max_workers']}")
    print(f"  Default Resolution  : {rec['default_scale_agents']} agents")
    print(f"  Estimated Max Agent : ~{rec['max_agents']:,} agents within memory budget")
    print("==================================================")

    if "estimate" in info:
        est = info["estimate"]
        print("\n--- Resource Estimate ---")
        inp = est["inputs"]
        print(f"Configuration : {inp['agents']:,} agents, {inp['days']} days, {inp['replicates']} replicates")
        print(f"Estimated RAM : {est['estimated_memory_mb']} MB ({est['estimated_memory_gb']} GB) [Budget: {est['memory_budget_gb']} GB - Fits: {est['fits_memory_budget']}]")
        print(f"Estimated Time: ~{est['estimated_wall_time_human']} ({est['estimated_wall_time_seconds']}s)")


if __name__ == "__main__":
    main()
