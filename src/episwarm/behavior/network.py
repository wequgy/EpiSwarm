"""Sparse social network graph construction for rumor and influence propagation (Spec 7.1)."""

from typing import Dict, List, Optional, Tuple
import numpy as np
import scipy.sparse as sp

from episwarm.population.build import PopulationSoA


def build_social_network(
    pop: PopulationSoA,
    k_venue_ties: int = 3,
    k_neighborhood_ties: int = 4,
    n_influencers: int = 5,
    rng: Optional[np.random.Generator] = None
) -> sp.csr_matrix:
    """Construct sparse CSR adjacency matrix A from multi-layered physical and social ties.

    Layers:
    1. Household ties: complete subgraph within each household
    2. Venue ties: sample k ties from same workplace or school
    3. Neighborhood ties: local peer ties within same administrative area
    4. Influencers: power-law broadcast ties to broader population
    """
    if rng is None:
        rng = np.random.default_rng(42)

    n = pop.n_agents
    rows: List[np.ndarray] = []
    cols: List[np.ndarray] = []

    # 1. Household ties (complete within household)
    # Sort agent indices by household_id
    hh_order = np.argsort(pop.household_id)
    sorted_hh = pop.household_id[hh_order]
    unique_hhs, split_idx = np.unique(sorted_hh, return_index=True)
    hh_groups = np.split(hh_order, split_idx[1:])

    hh_rows = []
    hh_cols = []
    for grp in hh_groups:
        sz = len(grp)
        if 1 < sz <= 15:  # avoid explosive combinatorial expansion
            for i in range(sz):
                for j in range(sz):
                    if i != j:
                        hh_rows.append(grp[i])
                        hh_cols.append(grp[j])

    if hh_rows:
        rows.append(np.array(hh_rows, dtype=np.int32))
        cols.append(np.array(hh_cols, dtype=np.int32))

    # 2. Venue ties (schools & workplaces)
    for venue_arr in (pop.school_id, pop.workplace_id):
        valid = np.where(venue_arr >= 0)[0]
        if len(valid) > 0:
            v_order = np.argsort(venue_arr[valid])
            sorted_v_agents = valid[v_order]
            sorted_vids = venue_arr[sorted_v_agents]
            _, v_split = np.unique(sorted_vids, return_index=True)
            v_groups = np.split(sorted_v_agents, v_split[1:])

            v_r = []
            v_c = []
            for grp in v_groups:
                sz = len(grp)
                if sz > 1:
                    k = min(k_venue_ties, sz - 1)
                    for member in grp:
                        # Pick k random peers from venue
                        peers = rng.choice(grp, size=min(k + 1, sz), replace=False)
                        for p in peers:
                            if p != member:
                                v_r.append(member)
                                v_c.append(p)
            if v_r:
                rows.append(np.array(v_r, dtype=np.int32))
                cols.append(np.array(v_c, dtype=np.int32))

    # 3. Neighborhood ties (within same area)
    area_r = []
    area_c = []
    for aid in np.unique(pop.area_id):
        local_agents = np.where(pop.area_id == aid)[0]
        sz = len(local_agents)
        if sz > 1:
            k = min(k_neighborhood_ties, sz - 1)
            # Sample k neighbors per agent
            sampled_peers = rng.choice(local_agents, size=(sz, k))
            rep_agents = np.repeat(local_agents, k)
            area_r.append(rep_agents)
            area_c.append(sampled_peers.flatten())

    if area_r:
        rows.append(np.concatenate(area_r).astype(np.int32))
        cols.append(np.concatenate(area_c).astype(np.int32))

    # 4. Influencer broadcasting accounts
    if n_influencers > 0 and n > 20:
        influencer_ids = rng.choice(n, size=min(n_influencers, n), replace=False)
        inf_r = []
        inf_c = []
        for inf in influencer_ids:
            # Power law reach: 5% to 20% of population
            reach_size = int(np.clip(rng.pareto(a=1.5) * 0.05 * n, 10, int(0.25 * n)))
            followers = rng.choice(n, size=min(reach_size, n), replace=False)
            inf_r.append(followers)  # followers receive exposure from influencer
            inf_c.append(np.full(len(followers), inf, dtype=np.int32))
        if inf_r:
            rows.append(np.concatenate(inf_r).astype(np.int32))
            cols.append(np.concatenate(inf_c).astype(np.int32))

    # Assemble sparse CSR matrix
    all_rows = np.concatenate(rows)
    all_cols = np.concatenate(cols)

    # Filter self-loops
    valid_ties = (all_rows != all_cols)
    all_rows = all_rows[valid_ties]
    all_cols = all_cols[valid_ties]

    data = np.ones(len(all_rows), dtype=np.float32)
    adj = sp.csr_matrix((data, (all_rows, all_cols)), shape=(n, n))

    # Row normalize so each agent's exposure is normalized average
    row_sums = np.array(adj.sum(axis=1)).flatten()
    row_sums[row_sums == 0] = 1.0
    inv_diag = sp.diags(1.0 / row_sums)
    adj_norm = inv_diag.dot(adj)

    return adj_norm.tocsr()

