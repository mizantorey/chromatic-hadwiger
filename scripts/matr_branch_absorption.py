"""
SCRIPT 5 — LEMA 8.3d: ABSORCION DISTRIBUIDA  — V20
====================================================
CAMBIOS V20: Version estandarizada. Sin cambios funcionales respecto a V16.
CAMBIOS V16: try/finally, auto-save, GPU, grafos ordenados por n.
Investigador : Mizael Antonio Tovar Reyes
Ubicacion    : Ciudad Juarez, Chihuahua, Mexico
"""

import sys
import time
import itertools
from pathlib import Path
import networkx as nx

try:
    from core_utils import (
        chromatic_exact, get_optimal_coloring, compute_p_hybrid,
        get_all_graphs, kneser_graph_manual,
        print_header, print_footer, UnifiedLogger,
        EXACT_THRESHOLD, TQDM_AVAILABLE
    )
    if TQDM_AVAILABLE:
        from tqdm import tqdm
except ImportError:
    print("ERROR: No se encontro core_utils.py")
    sys.exit(1)

SCRIPT_NAME = "SCRIPT 5 — LEMA 8.3d"
DESCRIPTION = "Verifica: absorcion distribuida preserva aristas inter-set"
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "log_script5_lema83d.txt"
NUM_RANDOM_GRAPHS = 500


def build_branch_sets_tracked(G, coloring, chi):
    classes = {}
    for v, c in coloring.items():
        classes.setdefault(c, set()).add(v)
    colors = sorted(classes.keys())
    if len(colors) != chi:
        return None
    branch_sets = {c: set(classes[c]) for c in colors}
    absorption_log = {}

    for c in colors:
        class_nodes = list(classes[c])
        if not class_nodes:
            continue
        center = max(class_nodes, key=lambda v: G.degree(v))
        component = set()
        queue = [center]
        visited = {center}
        while queue:
            v = queue.pop(0)
            component.add(v)
            for u in G.neighbors(v):
                if u not in visited:
                    visited.add(u)
                    if u in classes[c]:
                        queue.append(u)
        isolated = classes[c] - component
        for iso in isolated:
            try:
                path = nx.shortest_path(G, center, iso)
                for pv in path:
                    if pv not in classes[c]:
                        orig_color = coloring.get(pv)
                        if orig_color is None:
                            continue
                        if pv not in absorption_log:
                            absorption_log[pv] = {"orig_color": orig_color, "absorbed_into": set()}
                        absorption_log[pv]["absorbed_into"].add(c)
                    branch_sets[c].add(pv)
            except nx.NetworkXNoPath:
                pass

    return branch_sets, classes, colors, absorption_log


def verify_distributed_absorption(G, branch_sets, classes, colors, absorption_log):
    distributed_pairs = []
    failures = []
    for j in colors:
        absorbed_into = set()
        for v, log in absorption_log.items():
            if log["orig_color"] == j:
                for dest in log["absorbed_into"]:
                    if dest != j:
                        absorbed_into.add(dest)
        if len(absorbed_into) < 2:
            continue
        for l in colors:
            if l == j:
                continue
            ejl = [(u, v) for u in classes[j] for v in classes[l] if G.has_edge(u, v)]
            if not ejl:
                continue
            distributed_pairs.append((j, l, len(absorbed_into), len(ejl)))
            inter_edge_exists = any(
                G.has_edge(u, v) for u in branch_sets[j] for v in branch_sets[l]
            )
            if not inter_edge_exists:
                failures.append({"class_j": j, "class_l": l, "absorbed_into": list(absorbed_into)})
    return len(failures) == 0, distributed_pairs, failures


def main():
    print_header(SCRIPT_NAME, DESCRIPTION)
    print("Generando grafos de prueba (ordenados por n)...")
    graphs = get_all_graphs(num_random=NUM_RANDOM_GRAPHS, random_seed=2024)
    print(f"  Total de grafos: {len(graphs)}\n")

    logger = UnifiedLogger(SCRIPT_NAME, LOG_FILE)
    print(f"  Log iniciado: {LOG_FILE}\n")

    graphs_ok = 0
    graphs_fail = 0
    graphs_with_dist = 0
    total_dist_pairs = 0
    t0 = time.time()

    iterator = tqdm(graphs, desc="Verificando", ncols=90,
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') \
               if TQDM_AVAILABLE else graphs

    try:
        for G, name, familia in iterator:
            if not nx.is_connected(G):
                continue
            n = G.number_of_nodes()
            chi = chromatic_exact(G, max_k=15 if n <= 18 else 10)
            if chi is None or chi < 2:
                continue
            coloring = get_optimal_coloring(G, chi)
            if coloring is None:
                continue
            result = build_branch_sets_tracked(G, coloring, chi)
            if result is None:
                continue
            branch_sets, classes, colors, absorption_log = result
            all_ok, dist_pairs, failures = verify_distributed_absorption(
                G, branch_sets, classes, colors, absorption_log
            )
            if dist_pairs:
                graphs_with_dist += 1
                total_dist_pairs += len(dist_pairs)
            method = "EXACTO" if n <= EXACT_THRESHOLD else "PROB"
            if all_ok:
                graphs_ok += 1
            else:
                graphs_fail += 1
            logger.add_entry(
                graph_name=f"[{familia}] {name}",
                chi=chi, p=chi - 1, formula_ok=all_ok, method=method,
                extra={"dist_pairs": len(dist_pairs), "failures": len(failures)}
            )
            if not TQDM_AVAILABLE and dist_pairs:
                print(f"  [{'OK' if all_ok else 'FALLO'}] {name:<35} chi={chi} dist={len(dist_pairs)} [{method}]")
    except KeyboardInterrupt:
        print("\n\n  !! Interrumpido — guardando log parcial...")
    finally:
        elapsed = (time.time() - t0) / 60
        logger.set_summary(
            Grafos_con_absorcion_distribuida=graphs_with_dist,
            Pares_distribuidos_totales=total_dist_pairs,
            Todos_preservan_aristas="SI" if graphs_fail == 0 else "NO"
        )
        logger.write_log()
        print_footer(graphs_ok, graphs_fail, elapsed)
        print(f"\n  Grafos con casos distribuidos : {graphs_with_dist}")
        print(f"  Pares distribuidos totales    : {total_dist_pairs}")
        print(f"  Todos preservan aristas       : {'SI' if graphs_fail == 0 else 'NO'}")
        print(f"  Log: {LOG_FILE}")

    return graphs_fail == 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    success = main()
    sys.exit(0 if success else 1)
