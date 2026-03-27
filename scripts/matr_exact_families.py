"""
SCRIPT 4 — FAMILIAS EXACTAS  — V20
====================================
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
        compute_p_hybrid, print_header, print_footer, UnifiedLogger,
        EXACT_THRESHOLD, TQDM_AVAILABLE
    )
    if TQDM_AVAILABLE:
        from tqdm import tqdm
except ImportError:
    print("ERROR: No se encontro core_utils.py")
    sys.exit(1)

SCRIPT_NAME = "SCRIPT 4 — FAMILIAS EXACTAS"
DESCRIPTION = "Verifica: Proposicion 6.1 + Teorema 5.1 (valores teoricos)"
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "log_script4_familias.txt"


def get_test_cases():
    cases = []
    # K_n: chi=n, p=n-1
    for n in range(2, 16):
        cases.append((nx.complete_graph(n), f"K_{n}", "Completos_K_n", n, n - 1))
    # Bipartitos: chi=2, p=1
    for n in [3, 4, 5, 6, 7, 8, 10, 15]:
        cases.append((nx.path_graph(n), f"Path_P{n}", "Bipartitos", 2, 1))
    for n in [4, 6, 8, 10, 12, 14, 16]:
        cases.append((nx.cycle_graph(n), f"C_{n}_par", "Bipartitos", 2, 1))
    for p, q in [(2, 2), (2, 3), (3, 3), (4, 4), (2, 5), (3, 5), (4, 5), (5, 5)]:
        cases.append((nx.complete_bipartite_graph(p, q), f"K_{p},{q}", "Bipartitos", 2, 1))
    for d in [2, 3, 4]:
        cases.append((nx.hypercube_graph(d), f"Cubo_Q{d}", "Bipartitos", 2, 1))
    for n in [3, 4, 5, 6, 8, 10]:
        cases.append((nx.star_graph(n), f"Star_S{n}", "Bipartitos", 2, 1))
    # Ciclos impares: chi=3, p=2
    for n in [5, 7, 9, 11, 13, 15, 17, 19, 21]:
        cases.append((nx.cycle_graph(n), f"C_{n}_impar", "Ciclos_impares", 3, 2))
    # Ruedas
    for n in range(4, 15):
        G = nx.wheel_graph(n)
        cycle_size = n - 1
        chi_esp = 4 if cycle_size % 2 == 1 else 3
        cases.append((G, f"W_{n}", "Wheels", chi_esp, chi_esp - 1))
    # Ordenar por n
    cases.sort(key=lambda x: x[0].number_of_nodes())
    return cases


def main():
    print_header(SCRIPT_NAME, DESCRIPTION)
    print("Generando casos de prueba con valores teoricos (ordenados por n)...")
    cases = get_test_cases()
    print(f"  Total de casos: {len(cases)}\n")

    logger = UnifiedLogger(SCRIPT_NAME, LOG_FILE)
    print(f"  Log iniciado: {LOG_FILE}\n")

    family_stats = {}
    ok_count = 0
    fail_count = 0
    t0 = time.time()

    iterator = tqdm(cases, desc="Verificando", ncols=90,
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') \
               if TQDM_AVAILABLE else cases

    try:
        for G, name, familia, chi_esperado, p_esperado in iterator:
            if familia not in family_stats:
                family_stats[familia] = {"ok": 0, "fail": 0}
            if not nx.is_connected(G):
                continue
            n = G.number_of_nodes()
            p_calc, method = compute_p_hybrid(G)
            formula_ok = (p_calc == p_esperado)
            if formula_ok:
                ok_count += 1
                family_stats[familia]["ok"] += 1
            else:
                fail_count += 1
                family_stats[familia]["fail"] += 1
            logger.add_entry(
                graph_name=f"[{familia}] {name}",
                chi=chi_esperado, p=p_calc, formula_ok=formula_ok, method=method,
                extra={"p_esp": p_esperado, "n": n}
            )
            if not TQDM_AVAILABLE:
                match = "=" if p_calc == p_esperado else "!="
                print(f"  [{'OK' if formula_ok else 'FALLO'}] {name:<15} p_esp={p_esperado} p_calc={p_calc} {match} [{method}]")
    except KeyboardInterrupt:
        print("\n\n  !! Interrumpido — guardando log parcial...")
    finally:
        elapsed = (time.time() - t0) / 60
        family_summary = "; ".join([f"{f}: {s['ok']}/{s['ok']+s['fail']}" for f, s in family_stats.items()])
        logger.set_summary(Por_familia=family_summary)
        logger.write_log()
        print_footer(ok_count, fail_count, elapsed)
        print(f"\n  Desglose por familia:")
        for familia, stats in family_stats.items():
            total = stats["ok"] + stats["fail"]
            print(f"    [{'OK' if stats['fail']==0 else 'FALLO'}] {familia:<20}: {stats['ok']}/{total}")
        print(f"  Log: {LOG_FILE}")

    return fail_count == 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    success = main()
    sys.exit(0 if success else 1)
