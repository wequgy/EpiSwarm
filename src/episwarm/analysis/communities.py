"""Spatial community detection and bootstrapping on commuting flux graphs (Libin et al. 2020, Spec 11.6).

Detects communities in the commuting mobility flux graph to cluster administrative
areas into coordinated policy groups (scaling deep RL/joint optimization to ~10 controlled clusters).
"""

from typing import Dict, List, Set, Tuple, Optional, Any
import numpy as np
import networkx as nx
from sklearn.metrics import adjusted_rand_score


def detect_mobility_communities(
    area_ids: List[str],
    mobility_matrix: np.ndarray,
    resolution: float = 1.0,
    seed: int = 42
) -> Dict[str, Any]:
    """Detect communities from mobility flux graph.

    Tries Leiden if available via leidenalg/backend; otherwise uses Louvain/modularity
    maximization with documented fallback.
    """
    n = len(area_ids)
    mob = np.asarray(mobility_matrix, dtype=np.float64)
    assert mob.shape == (n, n), f"Matrix shape {mob.shape} != ({n}, {n})"

    # Build weighted graph (symmetrized for modularity clustering)
    G = nx.Graph()
    for aid in area_ids:
        G.add_node(aid)

    for i in range(n):
        for j in range(i + 1, n):
            weight = float(mob[i, j] + mob[j, i])
            if weight > 1e-6:
                G.add_edge(area_ids[i], area_ids[j], weight=weight)

    algorithm_used = "louvain_modularity_fallback"
    communities: List[Set[str]] = []

    # Attempt Leiden if library exists
    try:
        import leidenalg
        import igraph as ig
        # Construct igraph
        g_ig = ig.Graph()
        g_ig.add_vertices(area_ids)
        edges = []
        weights = []
        for u, v, d in G.edges(data=True):
            edges.append((u, v))
            weights.append(d["weight"])
        if edges:
            g_ig.add_edges(edges)
            g_ig.es["weight"] = weights
            part = leidenalg.find_partition(
                g_ig,
                leidenalg.ModularityVertexPartition,
                weights=g_ig.es["weight"],
                seed=seed
            )
            communities = [set(area_ids[idx] for idx in p) for p in part]
            algorithm_used = "leidenalg"
    except ImportError:
        # Documented fallback using NetworkX Louvain modularity
        from networkx.algorithms.community import louvain_communities
        try:
            comms = louvain_communities(G, weight="weight", resolution=resolution, seed=seed)
            communities = [set(c) for c in comms]
            algorithm_used = "networkx_louvain"
        except Exception:
            from networkx.algorithms.community import greedy_modularity_communities
            comms = greedy_modularity_communities(G, weight="weight")
            communities = [set(c) for c in comms]
            algorithm_used = "networkx_greedy_modularity"

    if not communities:
        # Fallback: each area in its own community
        communities = [{aid} for aid in area_ids]

    # Map area to community id
    area_to_comm: Dict[str, int] = {}
    for cid, comm in enumerate(communities):
        for aid in comm:
            area_to_comm[aid] = cid

    # Calculate graph modularity
    modularity = 0.0
    try:
        from networkx.algorithms.community import modularity as calc_modularity
        if G.number_of_edges() > 0:
            modularity = float(calc_modularity(G, communities, weight="weight"))
    except Exception:
        modularity = 0.0

    return {
        "algorithm": algorithm_used,
        "n_communities": len(communities),
        "communities": [sorted(list(c)) for c in communities],
        "area_to_community": area_to_comm,
        "modularity": round(modularity, 4),
        "n_nodes": n,
        "n_edges": G.number_of_edges()
    }


def bootstrap_community_robustness(
    area_ids: List[str],
    mobility_matrix: np.ndarray,
    n_bootstraps: int = 15,
    noise_std: float = 0.15,
    seed: int = 42
) -> Dict[str, Any]:
    """Assess community stability by bootstrapping with perturbed mobility flows (Spec 11.6)."""
    rng = np.random.default_rng(seed)
    n = len(area_ids)

    # Base partition
    base_res = detect_mobility_communities(area_ids, mobility_matrix, seed=seed)
    base_labels = [base_res["area_to_community"][aid] for aid in area_ids]

    ari_scores: List[float] = []

    for b in range(n_bootstraps):
        b_seed = seed + b + 1
        # Multiplicative positive Gaussian perturbation
        noise = rng.normal(1.0, noise_std, size=(n, n))
        noise = np.clip(noise, 0.1, 3.0)
        perturbed_mob = mobility_matrix * noise
        # Symmetrize
        perturbed_mob = 0.5 * (perturbed_mob + perturbed_mob.T)

        boot_res = detect_mobility_communities(area_ids, perturbed_mob, seed=b_seed)
        boot_labels = [boot_res["area_to_community"][aid] for aid in area_ids]

        ari = float(adjusted_rand_score(base_labels, boot_labels))
        ari_scores.append(ari)

    mean_ari = float(np.mean(ari_scores)) if ari_scores else 1.0
    return {
        "mean_adjusted_rand_index": round(mean_ari, 4),
        "min_ari": round(float(np.min(ari_scores)), 4) if ari_scores else 1.0,
        "max_ari": round(float(np.max(ari_scores)), 4) if ari_scores else 1.0,
        "std_ari": round(float(np.std(ari_scores)), 4) if ari_scores else 0.0,
        "n_bootstraps": n_bootstraps,
        "is_stable": bool(mean_ari >= 0.70)
    }


def group_areas_for_policy_control(
    area_ids: List[str],
    mobility_matrix: np.ndarray,
    max_controlled_groups: int = 10,
    seed: int = 42
) -> Dict[int, List[str]]:
    """Group administrative areas into <= max_controlled_groups for tractable joint control (Spec 11.6)."""
    detection = detect_mobility_communities(area_ids, mobility_matrix, seed=seed)
    comms = detection["communities"]

    # If count <= max_controlled_groups, return directly
    if len(comms) <= max_controlled_groups:
        return {i: c for i, c in enumerate(comms)}

    # If more than max_controlled_groups, merge smallest clusters until count <= max_controlled_groups
    merged = [list(c) for c in comms]
    while len(merged) > max_controlled_groups:
        merged.sort(key=len)
        smallest = merged.pop(0)
        merged[0].extend(smallest)

    return {i: sorted(c) for i, c in enumerate(merged)}
