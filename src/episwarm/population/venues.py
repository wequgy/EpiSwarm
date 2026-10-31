"""Venue instantiation, commute assignment, and persistent social space routines (Spec 9 & 2)."""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd


class VenueRegistry:
    """Registry of instantiated physical venues across administrative areas."""

    def __init__(self):
        self.venue_ids: np.ndarray = np.empty(0, dtype=np.int32)
        self.area_ids: np.ndarray = np.empty(0, dtype=np.int16)
        self.venue_types: np.ndarray = np.empty(0, dtype=object)  # 'school', 'workplace', 'market', 'leisure', 'worship'
        self.capacities: np.ndarray = np.empty(0, dtype=np.int32)


def instantiate_venues(
    venues_df: pd.DataFrame,
    area_id_to_int: Dict[str, int],
    rng: np.random.Generator
) -> Tuple[VenueRegistry, Dict[int, List[int]], Dict[int, List[int]], Dict[str, Dict[int, List[int]]]]:
    """Generate discrete venue instances from venues.csv specification.

    Returns:
        registry: VenueRegistry containing all venue instances
        schools_by_area: Dict[area_int, List[venue_id]]
        workplaces_by_area: Dict[area_int, List[venue_id]]
        all_venues_by_type: Dict[venue_type, Dict[area_int, List[venue_id]]]
    """
    registry = VenueRegistry()
    v_ids = []
    v_areas = []
    v_types = []
    v_caps = []

    all_venues_by_type: Dict[str, Dict[int, List[int]]] = {}

    current_vid = 0
    if not venues_df.empty:
        for _, row in venues_df.iterrows():
            aid_str = str(row["area_id"])
            if aid_str not in area_id_to_int:
                continue
            aid = area_id_to_int[aid_str]
            v_type = str(row["venue_type"]).strip().lower()
            count = int(row.get("count", 10))
            mean_sz = float(row.get("mean_size", 50.0))
            sd_sz = float(row.get("size_sd", max(1.0, mean_sz * 0.2)))

            sizes = np.clip(rng.normal(mean_sz, sd_sz, size=count), 5, None).astype(np.int32)

            for s in sizes:
                vid = current_vid
                current_vid += 1
                v_ids.append(vid)
                v_areas.append(aid)
                v_types.append(v_type)
                v_caps.append(s)

                all_venues_by_type.setdefault(v_type, {}).setdefault(aid, []).append(vid)
    else:
        # Fallback default venues per area
        for aid in range(len(area_id_to_int)):
            for v_type, cnt in [("school", 5), ("workplace", 20), ("market", 5), ("leisure", 10)]:
                for _ in range(cnt):
                    vid = current_vid
                    current_vid += 1
                    v_ids.append(vid)
                    v_areas.append(aid)
                    v_types.append(v_type)
                    v_caps.append(50)
                    all_venues_by_type.setdefault(v_type, {}).setdefault(aid, []).append(vid)

    # Ensure every area has social venues (market, leisure) even if venues.csv only specified school/workplace
    for aid in range(len(area_id_to_int)):
        for social_type in ["market", "leisure"]:
            if aid not in all_venues_by_type.get(social_type, {}):
                for _ in range(5):
                    vid = current_vid
                    current_vid += 1
                    v_ids.append(vid)
                    v_areas.append(aid)
                    v_types.append(social_type)
                    v_caps.append(50)
                    all_venues_by_type.setdefault(social_type, {}).setdefault(aid, []).append(vid)

    registry.venue_ids = np.array(v_ids, dtype=np.int32)
    registry.area_ids = np.array(v_areas, dtype=np.int16)
    registry.venue_types = np.array(v_types, dtype=object)
    registry.capacities = np.array(v_caps, dtype=np.int32)

    schools_by_area = all_venues_by_type.get("school", {})
    workplaces_by_area = all_venues_by_type.get("workplace", {})

    return registry, schools_by_area, workplaces_by_area, all_venues_by_type


def assign_venues_and_commute(
    agent_ages: np.ndarray,
    agent_areas: np.ndarray,
    agent_occupations: np.ndarray,
    commute_od_df: Optional[pd.DataFrame],
    area_id_to_int: Dict[str, int],
    schools_by_area: Dict[int, List[int]],
    workplaces_by_area: Dict[int, List[int]],
    rng: np.random.Generator
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Assign workplace, school, and commute area for each synthetic agent.

    Returns:
        workplace_ids: int32 array (-1 if not employed)
        school_ids: int32 array (-1 if not attending school)
        commute_areas: int16 array (destination area of daily travel)
    """
    n_agents = len(agent_ages)
    workplace_ids = np.full(n_agents, -1, dtype=np.int32)
    school_ids = np.full(n_agents, -1, dtype=np.int32)
    commute_areas = np.copy(agent_areas)

    # 1. School assignment: children aged 5-18
    school_mask = (agent_ages >= 5) & (agent_ages <= 18)
    for aid in np.unique(agent_areas):
        local_kids = np.where(school_mask & (agent_areas == aid))[0]
        if len(local_kids) == 0:
            continue
        local_schools = schools_by_area.get(aid, [])
        if not local_schools:
            all_schools = [s for slist in schools_by_area.values() for s in slist]
            if all_schools:
                chosen = rng.choice(all_schools, size=len(local_kids))
                school_ids[local_kids] = chosen
        else:
            chosen = rng.choice(local_schools, size=len(local_kids))
            school_ids[local_kids] = chosen

    # 2. Workplace assignment: workers (occupation > 0, age 18-64)
    worker_mask = (agent_ages >= 18) & (agent_ages < 65) & (agent_occupations > 0)

    commute_probs: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
    if commute_od_df is not None and not commute_od_df.empty:
        for from_str, group in commute_od_df.groupby("from_area"):
            if str(from_str) not in area_id_to_int:
                continue
            from_aid = area_id_to_int[str(from_str)]
            dest_aids = []
            shares = []
            for _, r in group.iterrows():
                to_str = str(r["to_area"])
                if to_str in area_id_to_int:
                    dest_aids.append(area_id_to_int[to_str])
                    shares.append(float(r["share"]))
            if dest_aids and sum(shares) > 0:
                shares_arr = np.array(shares, dtype=np.float64)
                shares_arr /= shares_arr.sum()
                commute_probs[from_aid] = (np.array(dest_aids, dtype=np.int16), shares_arr)

    # Assign workers
    for origin_aid in np.unique(agent_areas):
        local_workers = np.where(worker_mask & (agent_areas == origin_aid))[0]
        if len(local_workers) == 0:
            continue

        if origin_aid in commute_probs:
            dests, probs = commute_probs[origin_aid]
            dest_choices = rng.choice(dests, size=len(local_workers), p=probs)
        else:
            dest_choices = np.full(len(local_workers), origin_aid, dtype=np.int16)

        commute_areas[local_workers] = dest_choices

        for dest_aid in np.unique(dest_choices):
            dest_worker_idx = local_workers[dest_choices == dest_aid]
            dest_workplaces = workplaces_by_area.get(dest_aid, [])
            if not dest_workplaces:
                all_wps = [w for wlist in workplaces_by_area.values() for w in wlist]
                if all_wps:
                    workplace_ids[dest_worker_idx] = rng.choice(all_wps, size=len(dest_worker_idx))
            else:
                workplace_ids[dest_worker_idx] = rng.choice(dest_workplaces, size=len(dest_worker_idx))

    return workplace_ids, school_ids, commute_areas


def assign_social_venues(
    agent_areas: np.ndarray,
    all_venues_by_type: Dict[str, Dict[int, List[int]]],
    rng: np.random.Generator
) -> Tuple[np.ndarray, np.ndarray]:
    """Assign persistent preferred market and leisure venues per agent (Spec 9).

    Returns:
        pref_market_ids: int32 array
        pref_leisure_ids: int32 array
    """
    n_agents = len(agent_areas)
    pref_market = np.full(n_agents, -1, dtype=np.int32)
    pref_leisure = np.full(n_agents, -1, dtype=np.int32)

    markets_by_area = all_venues_by_type.get("market", {})
    leisure_by_area = all_venues_by_type.get("leisure", {})

    all_markets = [m for mlist in markets_by_area.values() for m in mlist]
    all_leisure = [l for llist in leisure_by_area.values() for l in llist]

    for aid in np.unique(agent_areas):
        mask = (agent_areas == aid)
        count = int(np.sum(mask))
        if count == 0:
            continue

        # Preferred market
        local_mkts = markets_by_area.get(aid, [])
        if local_mkts:
            pref_market[mask] = rng.choice(local_mkts, size=count)
        elif all_markets:
            pref_market[mask] = rng.choice(all_markets, size=count)

        # Preferred leisure / social venue
        local_leis = leisure_by_area.get(aid, [])
        if local_leis:
            pref_leisure[mask] = rng.choice(local_leis, size=count)
        elif all_leisure:
            pref_leisure[mask] = rng.choice(all_leisure, size=count)

    return pref_market, pref_leisure
