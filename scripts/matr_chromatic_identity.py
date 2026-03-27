"""
SCRIPT 1 — TEOREMA 4.1: chi(G) = 1 + p(G)  — V20
==================================================
CAMBIOS V20: Version estandarizada. Sin cambios funcionales respecto a V16.
CAMBIOS V16: try/finally, auto-save, GPU, grafos ordenados por n.
Investigador : Mizael Antonio Tovar Reyes
Ubicacion    : Ciudad Juarez, Chihuahua, Mexico
"""

import sys
import time
from pathlib import Path
import networkx as nx

try:
    from core_utils import (
        chromatic_exact, compute_p_hybrid, get_all_graphs,
        print_header, print_footer, UnifiedLogger,
        EXACT_THRESHOLD, TQDM_AVAILABLE
    )
    if TQDM_AVAILABLE:
        from tqdm import tqdm
except ImportError:
    print("ERROR: No se encontro core_utils.py")
    sys.exit(1)

SCRIPT_NAME = "SCRIPT 1 — TEOREMA 4.1"
DESCRIPTION = "Verifica: chi(G) = 1 + p(G) para todo grafo simple conexo"
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "log_script1_teorema41.txt"
NUM_RANDOM_GRAPHS = 500


def main():
    print_header(SCRIPT_NAME, DESCRIPTION)
    print("Generando grafos de prueba (ordenados por n)...")
    graphs = get_all_graphs(num_random=NUM_RANDOM_GRAPHS, random_seed=42)
    print(f"  Total de grafos: {len(graphs)}\n")

    logger = UnifiedLogger(SCRIPT_NAME, LOG_FILE)
    print(f"  Log iniciado: {LOG_FILE}\n")

    ok_count = 0
    fail_count = 0
    exact_count = 0
    prob_count = 0
    t0 = time.time()

    iterator = tqdm(graphs, desc="Verificando", ncols=90,
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') \
               if TQDM_AVAILABLE else graphs

    try:
        for G, name, familia in iterator:
            if not nx.is_connected(G):
                continue
            n = G.number_of_nodes()
            chi = chromatic_exact(G, max_k=15 if n <= 20 else 12)
            if chi is None:
                continue
            p, method = compute_p_hybrid(G)
            formula_ok = (chi == 1 + p)
            if "EXACTO" in method:
                exact_count += 1
            else:
                prob_count += 1
            if formula_ok:
                ok_count += 1
            else:
                fail_count += 1
            logger.add_entry(
                graph_name=f"[{familia}] {name}",
                chi=chi, p=p, formula_ok=formula_ok, method=method,
                extra={"n": n, "m": G.number_of_edges()}
            )
            if not TQDM_AVAILABLE or not formula_ok:
                print(f"  [{'OK' if formula_ok else 'FALLO'}] {name:<35} chi={chi} p={p} [{method}]")
    except KeyboardInterrupt:
        print("\n\n  !! Interrumpido — guardando log parcial...")
    finally:
        elapsed = (time.time() - t0) / 60
        logger.set_summary(
            Exactos=f"{exact_count} grafos exhaustivos",
            Probabilisticos=f"{prob_count} grafos por muestreo"
        )
        logger.write_log()
        print_footer(ok_count, fail_count, elapsed)
        print(f"\n  Exactos (n<={EXACT_THRESHOLD}): {exact_count}  |  Prob (n>{EXACT_THRESHOLD}): {prob_count}")
        print(f"  Log: {LOG_FILE}")

    return fail_count == 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    success = main()
    sys.exit(0 if success else 1)
