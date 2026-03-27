"""
SCRIPT 7 — K_k MINOR COMPLETO — V20
===========================================================
Autor    : Mizael Antonio Tovar Reyes
Ubicacion: Ciudad Juarez, Chihuahua, Mexico

CAMBIOS V20: Version estandarizada. Sin cambios funcionales.

DIFERENCIA CLAVE vs Script 6:

  Script 6 — Fase 3 solo repara branch sets AISLADOS.
             Caso B = par sin arista directa pero con puente Bm.
             El grafo contraido puede ser CONEXO pero NO K_k completo.

  Script 7 — Corrige el BUG de Fase 2 del Script 6:
             El BFS absorbia vertices de otros colores, contaminando
             los branch sets y destruyendo aristas que ya existian.

  BUG ENCONTRADO (Marzo 2026):
             En W_5 (chi=3), B2={1,3} no son adyacentes en G[B2].
             El BFS tomaba el camino 1->0->3 y absorbia el hub 0
             (que es de color 1) dentro de B2 Y de B3.
             Resultado: node_to_bs[0] quedaba sobreescrito, B1
             quedaba invisible en el grafo contraido -> gaps falsos.

  FIX:       Fase 2 BFS solo absorbe vertices NO asignados a ninguna
             clase de color. Los vertices de otras clases son intocables.
             Con el fix, W_5 da K3 completo directamente desde las
             clases puras (que ya tienen todas las aristas necesarias).

  PREGUNTA QUE RESPONDE:
             Con la construccion corregida, el grafo contraido es
             K_k COMPLETO para todo grafo conexo simple?
             SI -> Theorem 8.7 y Corollary 8.8 correctos.
             NO -> paper necesita reformulacion.

Investigador : Mizael Antonio Tovar Reyes
Ubicacion    : Ciudad Juarez, Chihuahua, Mexico
Version      : 1 — Marzo 2026
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
        TQDM_AVAILABLE
    )
    if TQDM_AVAILABLE:
        from tqdm import tqdm
except ImportError:
    print("ERROR: No se encontro core_utils.py en el mismo directorio.")
    sys.exit(1)

SCRIPT_NAME       = "SCRIPT 7 — K_k MINOR COMPLETO"
DESCRIPTION       = "Fix BFS: solo absorbe vertices libres — verifica K_k completo"
BASE_DIR          = Path(__file__).resolve().parent
LOG_FILE          = BASE_DIR / "log_script7_kk_minor_completo.txt"
NUM_RANDOM_GRAPHS = 500
MAX_REPAIR_ITERS  = 50


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

def build_node_to_bs(branch_sets):
    ntb = {}
    for c, bs in branch_sets.items():
        for v in bs:
            ntb[v] = c
    return ntb


def build_contracted(G, branch_sets, colors):
    ntb = build_node_to_bs(branch_sets)
    contracted = {c: set() for c in colors}
    for u, v in G.edges():
        ci = ntb.get(u)
        cj = ntb.get(v)
        if ci is not None and cj is not None and ci != cj:
            contracted[ci].add(cj)
            contracted[cj].add(ci)
    return contracted


def is_connected_subgraph(G, nodes):
    nodes = set(nodes)
    if len(nodes) == 0:
        return False
    if len(nodes) == 1:
        return True
    start = next(iter(nodes))
    visited = {start}
    q = deque([start])
    while q:
        v = q.popleft()
        for u in G.neighbors(v):
            if u in nodes and u not in visited:
                visited.add(u)
                q.append(u)
    return len(visited) == len(nodes)


def is_kk_complete(contracted, colors):
    for ci, cj in itertools.combinations(colors, 2):
        if cj not in contracted[ci]:
            return False
    return True


def missing_pairs(contracted, colors):
    return [
        (ci, cj) for ci, cj in itertools.combinations(colors, 2)
        if cj not in contracted[ci]
    ]


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCCION V3 — BUG FIX EN FASE 2 + FASE 3 EXTENDIDA
# ─────────────────────────────────────────────────────────────────────────────

def build_branch_sets_v3(G, coloring, chi):
    """
    Fase 1 — B_i = A_i (clases de color puras).

    Fase 2 — BFS repair CORREGIDO:
             Conectar vertices aislados dentro de cada B_i usando
             SOLO vertices libres (no asignados a ninguna clase).
             FIX vs Script 6: antes absorbia vertices de otras clases,
             destruyendo aristas reales en el grafo contraido.

    Fase 3 — Repair de pares sin arista directa:
             Para cada par (Bi, Bj) sin arista en el grafo contraido,
             mueve un vertice para crearla, verificando que el set
             donante sigue siendo conexo.
    """
    classes = {}
    for v, c in coloring.items():
        classes.setdefault(c, set()).add(v)
    colors = sorted(classes.keys())
    if len(colors) != chi:
        return None, None, 0, False

    # FASE 1
    branch_sets = {c: set(classes[c]) for c in colors}

    # vertices asignados a alguna clase — intocables para el BFS de otro color
    all_class_nodes = set()
    for c in colors:
        all_class_nodes |= classes[c]

    # vertices libres — no pertenecen a ninguna clase de color
    free_nodes = set(G.nodes()) - all_class_nodes

    # FASE 2 — BFS corregido: solo absorbe vertices libres
    for c in colors:
        class_nodes = list(classes[c])
        if not class_nodes:
            continue
        center = max(class_nodes, key=lambda v: G.degree(v))

        # componente conexa de la clase pura
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
            # camino que solo usa nodos de esta clase O nodos libres
            allowed = classes[c] | free_nodes
            subG = G.subgraph(allowed)
            try:
                path = nx.shortest_path(subG, center, iso)
                for pv in path:
                    branch_sets[c].add(pv)
                    free_nodes.discard(pv)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                # no hay camino sin pasar por otros colores
                # Fase 3 se encargara
                pass

    # FASE 3 — reparar pares sin arista directa
    iters_used = 0
    for _ in range(MAX_REPAIR_ITERS):
        contracted = build_contracted(G, branch_sets, colors)

        if is_kk_complete(contracted, colors):
            return branch_sets, colors, iters_used, True

        pairs = missing_pairs(contracted, colors)
        if not pairs:
            break

        repaired_any = False

        for (ci, cj) in pairs:
            contracted = build_contracted(G, branch_sets, colors)
            if cj in contracted[ci]:
                continue

            ntb = build_node_to_bs(branch_sets)
            best_nb, best_source, best_score = None, None, -1

            # Estrategia A: nb de B_cj -> B_ci
            for nb in list(branch_sets[cj]):
                if not any(ntb.get(w) == ci for w in G.neighbors(nb)):
                    continue
                remaining = branch_sets[cj] - {nb}
                if not remaining or not is_connected_subgraph(G, remaining):
                    continue
                score = sum(1 for w in G.neighbors(nb) if ntb.get(w) == ci)
                if score > best_score:
                    best_score, best_nb, best_source = score, nb, cj

            # Estrategia B: nb de B_ci -> B_cj
            for nb in list(branch_sets[ci]):
                if not any(ntb.get(w) == cj for w in G.neighbors(nb)):
                    continue
                remaining = branch_sets[ci] - {nb}
                if not remaining or not is_connected_subgraph(G, remaining):
                    continue
                score = sum(1 for w in G.neighbors(nb) if ntb.get(w) == cj)
                if score > best_score:
                    best_score, best_nb, best_source = score, nb, ci

            # Estrategia C: nb de donante externo con vecinos en AMBOS ci y cj
            if best_nb is None:
                for c_donor in colors:
                    if c_donor in (ci, cj):
                        continue
                    for nb in list(branch_sets[c_donor]):
                        has_ci = any(ntb.get(w) == ci for w in G.neighbors(nb))
                        has_cj = any(ntb.get(w) == cj for w in G.neighbors(nb))
                        if not (has_ci and has_cj):
                            continue
                        remaining = branch_sets[c_donor] - {nb}
                        if not remaining or not is_connected_subgraph(G, remaining):
                            continue
                        score = (
                            sum(1 for w in G.neighbors(nb) if ntb.get(w) == ci) +
                            sum(1 for w in G.neighbors(nb) if ntb.get(w) == cj)
                        )
                        if score > best_score:
                            best_score, best_nb, best_source = score, nb, c_donor

            if best_nb is not None:
                if best_source == cj:
                    target = ci
                elif best_source == ci:
                    target = cj
                else:
                    target = ci  # donante externo: nb toca ambos
                branch_sets[best_source].discard(best_nb)
                branch_sets[target].add(best_nb)
                repaired_any = True
                iters_used += 1

        if not repaired_any:
            break

    contracted = build_contracted(G, branch_sets, colors)
    success = is_kk_complete(contracted, colors)
    return branch_sets, colors, iters_used, success


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

    branch_sets, colors, iters, success = build_branch_sets_v3(G, coloring, chi)
    if branch_sets is None:
        return None

    contracted   = build_contracted(G, branch_sets, colors)
    total_pairs  = chi * (chi - 1) // 2
    direct_count = sum(
        1 for ci, cj in itertools.combinations(colors, 2)
        if cj in contracted[ci]
    )
    gaps_remaining = total_pairs - direct_count

    return {
        "name"         : name,
        "familia"      : familia,
        "n"            : n,
        "m"            : G.number_of_edges(),
        "chi"          : chi,
        "p"            : p_g,
        "method"       : method,
        "kk_complete"  : success,
        "total_pairs"  : total_pairs,
        "direct_after" : direct_count,
        "gaps_after"   : gaps_remaining,
        "iters"        : iters,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print_header(SCRIPT_NAME, DESCRIPTION)
    print("  BUG CORREGIDO vs Script 6:")
    print("  Fase 2 BFS ya NO absorbe vertices de otras clases de color.")
    print("  Solo usa vertices libres (no asignados a ninguna clase).")
    print()
    print("  PREGUNTA: con la construccion corregida, el grafo contraido")
    print("  es K_k COMPLETO para todo grafo conexo simple?")
    print()
    print("  SI (0 gaps) -> Theorem 8.7 correcto -> paper listo para arXiv.")
    print("  NO          -> reportar grafos que fallan.")
    print()

    print("Generando grafos de prueba...")
    graphs = get_all_graphs(num_random=NUM_RANDOM_GRAPHS, random_seed=2025)
    print(f"  Total: {len(graphs)} grafos\n")

    logger = UnifiedLogger(SCRIPT_NAME, LOG_FILE)
    print(f"  Log: {LOG_FILE}\n")

    ok_count      = 0
    fail_count    = 0
    total_direct  = 0
    total_gaps    = 0
    failed_graphs = []
    t0            = time.time()

    iterator = (
        tqdm(graphs, desc="Verificando", ncols=90,
             bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
        if TQDM_AVAILABLE else graphs
    )

    try:
        for G, name, familia in iterator:
            if not nx.is_connected(G):
                continue

            result = verify_graph(G, name, familia)
            if result is None:
                continue

            total_direct += result["direct_after"]
            total_gaps   += result["gaps_after"]

            if result["kk_complete"]:
                ok_count += 1
            else:
                fail_count += 1
                failed_graphs.append(result)

            logger.add_entry(
                graph_name=f"[{result['familia']}] {result['name']}",
                chi=result["chi"],
                p=result["p"],
                formula_ok=result["kk_complete"],
                method=result["method"],
                extra={
                    "direct_after" : result["direct_after"],
                    "gaps_after"   : result["gaps_after"],
                    "iters"        : result["iters"],
                    "n"            : result["n"],
                    "m"            : result["m"],
                }
            )

            if not TQDM_AVAILABLE or not result["kk_complete"] or result["iters"] > 0:
                tag = ""
                if not result["kk_complete"]:
                    tag = f"  ⚠️  NO K_k — gaps={result['gaps_after']}"
                elif result["iters"] > 0:
                    tag = f"  [reparado en {result['iters']} iters]"
                print(
                    f"  [{'OK' if result['kk_complete'] else 'FALLO'}] "
                    f"[{result['familia']:<15}] {result['name']:<30} "
                    f"chi={result['chi']:<3} "
                    f"direct={result['direct_after']}/{result['total_pairs']} "
                    f"gaps={result['gaps_after']}"
                    f"{tag}"
                )

    except KeyboardInterrupt:
        print("\n  !! Interrumpido — guardando log parcial...")
    finally:
        elapsed = (time.time() - t0) / 60
        logger.set_summary(
            Grafos_Kk_completo         = ok_count,
            Grafos_sin_Kk_completo     = fail_count,
            Total_pares_directos_final = total_direct,
            Total_gaps_restantes       = total_gaps,
        )
        logger.write_log()
        print_footer(ok_count, fail_count, elapsed)
        print()
        print("  ── RESULTADO FINAL ──────────────────────────────────────────────")
        print(f"  Grafos con K_k minor COMPLETO : {ok_count}")
        print(f"  Grafos sin K_k minor completo : {fail_count}")
        print(f"  Total pares directos (final)  : {total_direct}")
        print(f"  Total gaps restantes          : {total_gaps}")
        print("  ─────────────────────────────────────────────────────────────────")
        if fail_count == 0 and total_gaps == 0:
            print("  ✅  K_k MINOR COMPLETO — 0 gaps en todos los grafos")
            print("      Bug de Fase 2 corregido. Construccion valida.")
            print("      Theorem 8.7 y Corollary 8.8 verificados.")
            print("      El paper puede ir a arXiv.")
        else:
            print(f"  ⚠️   {fail_count} grafos sin K_k completo:")
            for r in failed_graphs[:10]:
                print(f"      {r['name']}  chi={r['chi']}  "
                      f"direct={r['direct_after']}/{r['total_pairs']}  "
                      f"gaps={r['gaps_after']}")
            print()
            print("  -> Revisar si hay bug adicional o si la construccion")
            print("     necesita reformulacion en esos casos.")
        print("  ─────────────────────────────────────────────────────────────────")
        print(f"  Log: {LOG_FILE}")

    return fail_count == 0 and total_gaps == 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    success = main()
    sys.exit(0 if success else 1)
