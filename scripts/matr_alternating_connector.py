"""
SCRIPT 6 — LEMA 8.3f: CONECTOR ALTERNADO (idea de Mizael)  — V20
=================================================================
CAMBIOS V20:
  - Version estandarizada a V20.
  - Prueba formal del Caso 3b (anti-destruccion) documentada en
    conjecture/lema83f_caso3b_prueba_formal.md.
  - Sin cambios funcionales respecto a V2.

CAMBIOS V2:
  - Fase 3 nueva: repair agresivo de branch sets aislados.
    Antes de la V2, ciclos impares (C_7, C_9...) fallaban porque
    el BFS absorbía los únicos vecinos del vértice minoritario.
    V2 detecta estos casos y mueve un vértice vecino al branch set
    aislado, manteniendo la conexidad del branch set donante.
  - 0 fallos en todos los grafos de prueba.

IDEA CENTRAL (del dibujo de Mizael, Marzo 2026):
  Para cada par (Bi, Bj) en el grafo contraido, siempre existe
  adjacencia via:
    Case A: arista DIRECTA entre Bi y Bj en G
    Case B: existe Bm con aristas hacia AMBOS Bi y Bj
            (el "conector morado" del dibujo de Mizael)
  GAP REAL = par sin ninguna cobertura. DEBE SER 0 SIEMPRE.

Investigador : Mizael Antonio Tovar Reyes
Ubicacion    : Ciudad Juarez, Chihuahua, Mexico
"""

import sys
import time
import itertools
from pathlib import Path
from collections import deque
import networkx as nx

try:
    from core_utils import (
        chromatic_exact, get_optimal_coloring,
        compute_p_with_expansion_vertices,
        get_all_graphs, print_header, print_footer, UnifiedLogger,
        EXACT_THRESHOLD, TQDM_AVAILABLE
    )
    if TQDM_AVAILABLE:
        from tqdm import tqdm
except ImportError:
    print("ERROR: No se encontro core_utils.py en el mismo directorio.")
    sys.exit(1)

SCRIPT_NAME       = "SCRIPT 6 — LEMA 8.3f"
DESCRIPTION       = "Verifica: conector alternado cubre todo par (Bi,Bj) — V2"
BASE_DIR          = Path(__file__).resolve().parent
LOG_FILE          = BASE_DIR / "log_script6_lema83f.txt"
NUM_RANDOM_GRAPHS = 500


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCCION DE BRANCH SETS V2 — 3 FASES
# ─────────────────────────────────────────────────────────────────────────────

def build_branch_sets_v2(G, coloring, chi):
    """
    Fase 1 — Inicializar B_i = A_i (clases de color).
    Fase 2 — BFS repair: conectar vertices aislados dentro de cada B_i.
    Fase 3 — Repair agresivo: si algun B_ci queda sin vecinos en el
             grafo contraido, tomar un vertice nb de algun B_cj vecino
             (en G) y moverlo a B_ci, verificando que B_cj sigue conexo.
    """
    classes = {}
    for v, c in coloring.items():
        classes.setdefault(c, set()).add(v)
    colors = sorted(classes.keys())
    if len(colors) != chi:
        return None, None

    # FASE 1
    branch_sets = {c: set(classes[c]) for c in colors}

    # FASE 2
    for c in colors:
        class_nodes = list(classes[c])
        if not class_nodes:
            continue
        center = max(class_nodes, key=lambda v: G.degree(v))
        component = {center}
        q = deque([center])
        while q:
            v = q.popleft()
            for u in G.neighbors(v):
                if u not in component and u in classes[c]:
                    component.add(u)
                    q.append(u)
        isolated = classes[c] - component
        for iso in isolated:
            try:
                path = nx.shortest_path(G, center, iso)
                for pv in path:
                    branch_sets[c].add(pv)
            except nx.NetworkXNoPath:
                pass

    # FASE 3 — repair agresivo (hasta 20 iteraciones)
    for _ in range(20):
        node_to_bs = {}
        for c, bs in branch_sets.items():
            for v in bs:
                node_to_bs[v] = c

        contracted = {c: set() for c in colors}
        for u, v in G.edges():
            ci = node_to_bs.get(u)
            cj = node_to_bs.get(v)
            if ci and cj and ci != cj:
                contracted[ci].add(cj)
                contracted[cj].add(ci)

        isolated_bs = [c for c in colors if not contracted[c]]
        if not isolated_bs:
            break

        for ci in isolated_bs:
            best_nb     = None
            best_score  = -1
            best_source = None

            for v in branch_sets[ci]:
                for nb in G.neighbors(v):
                    cj = node_to_bs.get(nb)
                    if cj is None or cj == ci:
                        continue
                    score     = sum(1 for x in G.neighbors(nb) if x in branch_sets[ci])
                    remaining = branch_sets[cj] - {nb}
                    if not remaining:
                        continue
                    subg = G.subgraph(remaining)
                    if len(remaining) == 1 or nx.is_connected(subg):
                        if score > best_score:
                            best_score  = score
                            best_nb     = nb
                            best_source = cj

            if best_nb is not None:
                branch_sets[best_source].discard(best_nb)
                branch_sets[ci].add(best_nb)
                node_to_bs[best_nb] = ci

    return branch_sets, colors


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICACION DEL CONECTOR ALTERNADO
# ─────────────────────────────────────────────────────────────────────────────

def verify_conector_alternado(G, branch_sets, colors):
    node_to_bs = {}
    for c, bs in branch_sets.items():
        for v in bs:
            node_to_bs[v] = c

    contracted = {c: set() for c in colors}
    for u, v in G.edges():
        ci = node_to_bs.get(u)
        cj = node_to_bs.get(v)
        if ci and cj and ci != cj:
            contracted[ci].add(cj)
            contracted[cj].add(ci)

    direct_pairs = []
    bridge_pairs = []
    gap_pairs    = []

    for ci, cj in itertools.combinations(colors, 2):
        if cj in contracted[ci]:
            direct_pairs.append((ci, cj))
        else:
            bm = next(
                (cm for cm in colors
                 if cm != ci and cm != cj
                 and ci in contracted[cm] and cj in contracted[cm]),
                None
            )
            if bm is not None:
                bridge_pairs.append((ci, cj, bm))
            else:
                gap_pairs.append((ci, cj))

    return direct_pairs, bridge_pairs, gap_pairs


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICACION DE UN GRAFO
# ─────────────────────────────────────────────────────────────────────────────

def verify_graph(G, name, familia):
    n   = G.number_of_nodes()
    chi = chromatic_exact(G, max_k=15 if n <= 20 else 10)
    if chi is None or chi < 2:
        return None

    coloring = get_optimal_coloring(G, chi)
    if coloring is None:
        return None

    p_g, ordering, exp_vertices, method = compute_p_with_expansion_vertices(G)

    branch_sets, colors = build_branch_sets_v2(G, coloring, chi)
    if branch_sets is None:
        return None

    direct, bridge, gaps = verify_conector_alternado(G, branch_sets, colors)

    return {
        "name"       : name,
        "familia"    : familia,
        "n"          : n,
        "m"          : G.number_of_edges(),
        "chi"        : chi,
        "p"          : p_g,
        "method"     : method,
        "formula_ok" : (len(gaps) == 0),
        "total_pairs": chi * (chi - 1) // 2,
        "direct"     : len(direct),
        "bridge"     : len(bridge),
        "gaps"       : len(gaps),
        "gaps_detail": gaps,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print_header(SCRIPT_NAME, DESCRIPTION)
    print("  LO QUE VERIFICA ESTE SCRIPT:")
    print("  Para cada par (Bi, Bj) en el grafo contraido:")
    print("    Case A — arista directa Bi <-> Bj en G")
    print("    Case B — existe Bm adyacente a AMBOS (conector de Mizael)")
    print("    GAP    — ningun caso cubre el par  [DEBE SER SIEMPRE 0]")
    print()
    print("  ALGORITMO V2: Fase 1 (init) + Fase 2 (BFS) + Fase 3 (repair agresivo)")
    print()
    print("Generando grafos de prueba (ordenados por n)...")
    graphs = get_all_graphs(num_random=NUM_RANDOM_GRAPHS, random_seed=2025)
    print(f"  Total de grafos: {len(graphs)}\n")

    logger = UnifiedLogger(SCRIPT_NAME, LOG_FILE)
    print(f"  Log iniciado: {LOG_FILE}\n")

    ok_count     = 0
    fail_count   = 0
    total_direct = 0
    total_bridge = 0
    total_gaps   = 0
    gap_grafos   = []
    t0           = time.time()

    iterator = tqdm(graphs, desc="Verificando", ncols=90,
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') \
               if TQDM_AVAILABLE else graphs

    try:
        for G, name, familia in iterator:
            if not nx.is_connected(G):
                continue

            result = verify_graph(G, name, familia)
            if result is None:
                continue

            total_direct += result["direct"]
            total_bridge += result["bridge"]
            total_gaps   += result["gaps"]

            if result["formula_ok"]:
                ok_count += 1
            else:
                fail_count += 1
                gap_grafos.append(result)

            logger.add_entry(
                graph_name=f"[{result['familia']}] {result['name']}",
                chi=result["chi"],
                p=result["p"],
                formula_ok=result["formula_ok"],
                method=result["method"],
                extra={
                    "direct" : result["direct"],
                    "bridge" : result["bridge"],
                    "gaps"   : result["gaps"],
                    "n"      : result["n"],
                    "m"      : result["m"],
                }
            )

            if not TQDM_AVAILABLE or result["bridge"] > 0 or not result["formula_ok"]:
                tag = ""
                if result["gaps"] > 0:
                    tag = f" [GAP REAL ⚠️  {result['gaps_detail']}]"
                elif result["bridge"] > 0:
                    tag = f" [CaseB={result['bridge']}]"
                print(
                    f"  [{'OK' if result['formula_ok'] else 'FALLO'}] "
                    f"[{result['familia']:<15}] {result['name']:<30} "
                    f"chi={result['chi']:<3} direct={result['direct']:<3} "
                    f"bridge={result['bridge']:<3} gap={result['gaps']}"
                    f"{tag}"
                )

    except KeyboardInterrupt:
        print("\n\n  !! Interrumpido — guardando log parcial...")
    finally:
        elapsed = (time.time() - t0) / 60
        logger.set_summary(
            Pares_directos_CaseA      = total_direct,
            Pares_puente_CaseB_Mizael = total_bridge,
            Pares_sin_cobertura_GAP   = total_gaps,
            Gaps_en_grafos            = len(gap_grafos),
        )
        logger.write_log()
        print_footer(ok_count, fail_count, elapsed)
        print()
        print(f"  ── CONECTOR ALTERNADO — Lema 8.3f ───────────────────────────")
        print(f"  Pares Case A (arista directa)        : {total_direct}")
        print(f"  Pares Case B (puente Bm — Mizael)    : {total_bridge}")
        print(f"  Pares sin cobertura (GAP REAL)       : {total_gaps}")
        print(f"  ───────────────────────────────────────────────────────────────")
        if total_gaps == 0:
            print(f"  ✅  GAP = 0 — Lema 8.3f VERIFICADO COMPUTACIONALMENTE")
            print(f"      Case B cubre {total_bridge} pares adicionales mas alla de Case A")
        else:
            print(f"  ⚠️   GAPS ({total_gaps}) — REVISAR:")
            for r in gap_grafos[:5]:
                print(f"      {r['name']}  chi={r['chi']}  gaps={r['gaps_detail']}")
        print(f"  ───────────────────────────────────────────────────────────────")
        print(f"  Log: {LOG_FILE}")

    return fail_count == 0 and total_gaps == 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    success = main()
    sys.exit(0 if success else 1)
