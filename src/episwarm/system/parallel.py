"""Windows-safe process-parallel execution engine with zero-copy shared memory.

Stage R3.2: Replaces GIL-bound ThreadPoolExecutor with ProcessPoolExecutor,
using multiprocessing.shared_memory for zero-copy immutable population sharing,
hardware probe worker auto-tuning, and strict memory budgeting.
"""

from __future__ import annotations

import os
import math
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from multiprocessing import shared_memory
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import psutil

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.system.hardware import probe_hardware, MAX_MEMORY_BUDGET_BYTES


ARRAY_FIELDS = [
    "age",
    "area_id",
    "household_id",
    "workplace_id",
    "school_id",
    "commute_area",
    "wfh_possible",
    "compliance",
    "vulnerability",
    "comorbidity",
]


class SharedPopulationContext:
    """Manages shared memory segments for immutable PopulationSoA arrays."""

    def __init__(self, pop: PopulationSoA):
        self.pop = pop
        self.shm_blocks: Dict[str, shared_memory.SharedMemory] = {}
        self.meta: Dict[str, Any] = {
            "n_agents": pop.n_agents,
            "int_to_area_id": pop.int_to_area_id,
            "area_id_to_int": pop.area_id_to_int,
            "arrays": {},
        }
        self._allocate()

    def _allocate(self) -> None:
        prefix = f"epipop_{uuid.uuid4().hex[:8]}"
        for name in ARRAY_FIELDS:
            arr = getattr(self.pop, name, None)
            if arr is not None and isinstance(arr, np.ndarray):
                shm_name = f"{prefix}_{name}"
                shm = shared_memory.SharedMemory(create=True, size=arr.nbytes, name=shm_name)
                dest = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)
                dest[:] = arr[:]
                self.shm_blocks[name] = shm
                self.meta["arrays"][name] = {
                    "shm_name": shm_name,
                    "shape": arr.shape,
                    "dtype": str(arr.dtype),
                }

    def close(self) -> None:
        """Close and unlink all shared memory blocks."""
        for shm in self.shm_blocks.values():
            try:
                shm.close()
                shm.unlink()
            except Exception:
                pass
        self.shm_blocks.clear()

    def __enter__(self) -> SharedPopulationContext:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def reconstruct_shared_population(meta: Dict[str, Any]) -> Tuple[PopulationSoA, List[shared_memory.SharedMemory]]:
    """Reconstruct a PopulationSoA object from shared memory views in a child process."""
    opened_shms: List[shared_memory.SharedMemory] = []
    arrays: Dict[str, np.ndarray] = {}

    for name, arr_info in meta["arrays"].items():
        shm = shared_memory.SharedMemory(name=arr_info["shm_name"])
        opened_shms.append(shm)
        arr = np.ndarray(arr_info["shape"], dtype=np.dtype(arr_info["dtype"]), buffer=shm.buf)
        arrays[name] = arr

    pop = PopulationSoA(
        n_agents=meta["n_agents"],
        age=arrays.get("age", np.empty(0, dtype=np.int8)),
        area_id=arrays.get("area_id", np.empty(0, dtype=np.int16)),
        household_id=arrays.get("household_id", np.empty(0, dtype=np.int32)),
        workplace_id=arrays.get("workplace_id", np.empty(0, dtype=np.int32)),
        school_id=arrays.get("school_id", np.empty(0, dtype=np.int32)),
        commute_area=arrays.get("commute_area", np.empty(0, dtype=np.int16)),
        wfh_possible=arrays.get("wfh_possible", np.empty(0, dtype=bool)),
        compliance=arrays.get("compliance", np.empty(0, dtype=np.float32)),
        vulnerability=arrays.get("vulnerability", np.empty(0, dtype=np.float32)),
        comorbidity=arrays.get("comorbidity", np.empty(0, dtype=np.float32)),
        int_to_area_id=meta["int_to_area_id"],
        area_id_to_int=meta["area_id_to_int"],
    )
    return pop, opened_shms


def worker_simulate_replicate_shm(
    meta: Dict[str, Any],
    disease_dict: Dict[str, Any],
    scenario_dict: Dict[str, Any],
    seed: int,
    behavior_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Top-level picklable child worker for process execution."""
    from episwarm.engine.sim import run_simulation

    pop, opened_shms = reconstruct_shared_population(meta)
    try:
        disease_pack = DiseasePack(**disease_dict)
        scenario_pack = ScenarioPack(**scenario_dict)
        scenario_pack.random_seed = seed
        if behavior_mode:
            scenario_pack.behavior_mode = behavior_mode

        res = run_simulation(pop, disease_pack, scenario_pack, behavior_mode=behavior_mode)

        inf_indices = [i for i, s in enumerate(disease_pack.states) if s.infectious]
        inf_c = res.daily_state_counts[:, inf_indices].sum(axis=1) if inf_indices else np.zeros(scenario_pack.horizon_days)
        peak_d = int(np.argmax(inf_c))
        peak_inf = int(inf_c[peak_d])

        return {
            "seed": seed,
            "attack_rate": float(res.attack_rate),
            "peak_day": peak_d,
            "peak_infections": peak_inf,
            "total_deaths": int(res.total_deaths),
            "overflow_deaths": int(res.overflow_deaths),
            "peak_hospital_demand": int(np.max(res.daily_hospital_demand)),
            "peak_icu_demand": int(np.max(res.daily_icu_demand)),
            "runtime_sec": float(res.manifest.get("runtime_sec", 0.0)),
        }
    finally:
        for shm in opened_shms:
            try:
                shm.close()
            except Exception:
                pass


def compute_safe_worker_count(n_tasks: int, scale_agents: int) -> int:
    """Determine the optimal worker count constrained by physical cores and memory budget."""
    hw = probe_hardware()
    rec_workers = hw["recommendations"]["recommended_workers"]
    vm = psutil.virtual_memory()

    # Budget guard: estimate per-worker overhead (~60 MB + 10 KB per agent)
    per_worker_mb = 60.0 + (scale_agents * 10.0) / (1024.0)
    avail_budget_mb = min(MAX_MEMORY_BUDGET_BYTES, vm.available) / (1024.0 * 1024.0)

    max_by_ram = max(1, int(avail_budget_mb * 0.80 / per_worker_mb))
    workers = min(n_tasks, rec_workers, max_by_ram)
    return max(1, workers)
