"""
SCRIPT 2 — LEMA 7.1: COMPLETITUD CROMATICA  — V20
==================================================
CAMBIOS V20: Version estandarizada. Sin cambios funcionales respecto a V17.
CAMBIOS V17: fix bug closure en get_multiple_optimal_colorings,
             contadores de pares ahora se acumulan correctamente.
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
        chromatic_exact, get_all_graphs,
        print_header, print_footer, UnifiedLogger,
        EXACT_THRESHOLD, TQDM_AVAILABLE
    )
    if TQDM_AVAILABLE:
        from tqdm import tqdm
except ImportError:
    print("ERROR: No se encontro core_utils.py")
    sys.exit(1)


def _bt(i, order, col, adj, chi):
    """Backtracking 100% explicito — sin closures, sin bugs."""
    if i == len(order):
        return True
    v = order[i]
    used = {col[u] for u in adj[v] if u in col}
    for c in range(1, chi + 1):
        if c not in used:
            col[v] = c
            if _bt(i + 1, order, col, adj, chi):
                return True
            del col[v]
    return False


def get_multiple_optimal_colorings_fixed(G, chi, num_colorings=10, seed=42):
    """Version corregida — parametros explicitos, sin closure bug."""
    import random
    nodes = list(G.nodes())
    adj = {v: set(G.neighbors(v)) for v in nodes}
    rng = random.Random(seed)
    colorings = []
    seen = set()

    orders = [nodes[:]]
    for _ in range(num_colorings * 20):
        o = nodes[:]
        rng.shuffle(o)
        orders.append(o)

    for order in orders:
        if len(colorings) >= num_colorings:
            break
        col = {}
        if _bt(0, order, col, adj, chi):
            key = tuple(sorted(col.items()))
            if key not in seen:
                seen.add(key)
                colorings.append(dict(col))

    return colorings

SCRIPT_NAME = "SCRIPT 2 — LEMA 7.1"
DESCRIPTION = "Verifica: todo par (C_i, C_j) tiene >=1 arista en coloraciones optimas"
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "log_script2_lema71.txt"
NUM_RANDOM_GRAPHS = 500
NUM_COLORINGS_PER_GRAPH = 10


def verify_lemma_71(G, coloring):
    classes = {}
    for v, c in coloring.items():
        classes.setdefault(c, set()).add(v)
    colors = sorted(classes.keys())
    failures = []
    total_pairs = 0
    for ci, cj in itertools.combinations(colors, 2):
        total_pairs += 1
        has_edge = any(G.has_edge(u, v) for u in classes[ci] for v in classes[cj])
        if not has_edge:
            failures.append((ci, cj))
    return len(failures) == 0, failures, total_pairs


def main():
    print_header(SCRIPT_NAME, DESCRIPTION)
    print("Generando grafos de prueba (ordenados por n)...")
    graphs = get_all_graphs(num_random=NUM_RANDOM_GRAPHS, random_seed=99)
    print(f"  Total de grafos: {len(graphs)}  |  Coloraciones por grafo: {NUM_COLORINGS_PER_GRAPH}\n")

    logger = UnifiedLogger(SCRIPT_NAME, LOG_FILE)
    print(f"  Log iniciado: {LOG_FILE}\n")

    graphs_ok = 0
    graphs_fail = 0
    total_colorings = 0
    total_pairs_checked = 0
    total_pairs_ok = 0
    t0 = time.time()

    iterator = tqdm(graphs, desc="Verificando", ncols=90,
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') \
               if TQDM_AVAILABLE else graphs

    try:
        for G, name, familia in iterator:
            if not nx.is_connected(G):
                continue
            n = G.number_of_nodes()
            chi = chromatic_exact(G, max_k=15 if n <= 20 else 10)
            if chi is None or chi < 2:
                continue
            colorings = get_multiple_optimal_colorings_fixed(G, chi, num_colorings=NUM_COLORINGS_PER_GRAPH)
            if not colorings:
                continue
            total_colorings += len(colorings)
            graph_ok = True
            for coloring in colorings:
                lema_ok, failures, pairs = verify_lemma_71(G, coloring)
                total_pairs_checked += pairs
                total_pairs_ok += (pairs - len(failures))
                if not lema_ok:
                    graph_ok = False
            method = "EXACTO" if n <= EXACT_THRESHOLD else f"PROB({len(colorings)} cols)"
            if graph_ok:
                graphs_ok += 1
            else:
                graphs_fail += 1
            logger.add_entry(
                graph_name=f"[{familia}] {name}",
                chi=chi, p=chi - 1, formula_ok=graph_ok, method=method,
                extra={"cols": len(colorings)}
            )
            if not TQDM_AVAILABLE or not graph_ok:
                print(f"  [{'OK' if graph_ok else 'FALLO'}] {name:<35} chi={chi} cols={len(colorings)} [{method}]")
    except KeyboardInterrupt:
        print("\n\n  !! Interrumpido — guardando log parcial...")
    finally:
        elapsed = (time.time() - t0) / 60
        logger.set_summary(
            Coloraciones_verificadas=total_colorings,
            Pares_totales=total_pairs_checked,
            Pares_OK=total_pairs_ok
        )
        logger.write_log()
        print_footer(graphs_ok, graphs_fail, elapsed)
        print(f"\n  Coloraciones verificadas : {total_colorings}")
        print(f"  Pares de clases totales  : {total_pairs_checked}")
        print(f"  Pares con arista (OK)    : {total_pairs_ok}")
        print(f"  Log: {LOG_FILE}")

    return graphs_fail == 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    success = main()
    sys.exit(0 if success else 1)
