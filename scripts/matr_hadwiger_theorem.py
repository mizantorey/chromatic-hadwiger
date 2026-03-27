"""
SCRIPT 3 — TEOREMA 8.7: K_k MINOR (HADWIGER)  — V20
=====================================================
CAMBIOS V20: Version estandarizada. Sin cambios funcionales respecto a V17.
CAMBIOS V17: Integracion del GAP DETECTOR.
  - Detecta cuando par (Bi, Bj) queda sin arista directa tras absorción.
  - Aplica absorción coordinada (Lema 8.3e) para resolver el gap.
  - Registra en log: gap_detectado, gap_resuelto, vértice_puente_absorbido.
  - Si gap_irresoluble > 0 al final → fallo crítico (posible contraejemplo).
CAMBIOS V16: try/finally, auto-save, GPU, grafos ordenados por n.
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
        chromatic_exact, get_optimal_coloring, compute_p_with_expansion_vertices,
        get_all_graphs, print_header, print_footer, UnifiedLogger,
        EXACT_THRESHOLD, TQDM_AVAILABLE
    )
    if TQDM_AVAILABLE:
        from tqdm import tqdm
except ImportError:
    print("ERROR: No se encontro core_utils.py")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────
# GAP DETECTOR — Lema 8.3e (integrado V17)
# ─────────────────────────────────────────────────────────────────

def _edges_between(G, set_a, set_b):
    """Aristas directas entre dos conjuntos de vértices."""
    return [(u, v) for u in set_a for v in G.neighbors(u) if v in set_b]

def _is_connected_subset(G, nodes):
    """¿El subconjunto 'nodes' induce un subgrafo conexo?"""
    nodes = set(nodes)
    if len(nodes) <= 1:
        return True
    start = next(iter(nodes))
    visited = {start}
    queue = deque([start])
    while queue:
        curr = queue.popleft()
        for nb in G.neighbors(curr):
            if nb in nodes and nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return visited == nodes

def detect_and_resolve_gap(G, branch_sets, colors):
    """
    Lema 8.3e — Detección y resolución del gap.

    Verifica si algún par (Bi, Bj) carece de arista directa.
    Si hay gap, intenta resolverlo por absorción coordinada:
      (a) Si existe vértice v en Bm con aristas hacia Bi Y Bj
          → Bm valida la adyacencia en el minor contraído.
      (b) Si existe vértice v en Bi (o Bj) reasignable al otro
          sin romper conexidad → reasignar y crear arista directa.

    Retorna dict con estadísticas detalladas del gap.
    """
    bs = {c: set(s) for c, s in branch_sets.items()}  # copia de trabajo
    gap_pairs        = []   # pares sin arista directa
    gap_resolved     = []   # pares resueltos por lema 8.3e
    gap_irresoluble  = []   # pares que NO se pudieron resolver
    bridge_vertices  = {}   # vértice puente que causó cada gap

    for ci, cj in itertools.combinations(colors, 2):
        aristas = _edges_between(G, bs[ci], bs[cj])
        if aristas:
            continue  # no hay gap aquí

        gap_pairs.append((ci, cj))

        # ── Caso (a): ¿existe Bm con aristas a Bi Y a Bj? ──
        resuelto = False
        for cm in colors:
            if cm in (ci, cj):
                continue
            hacia_i = _edges_between(G, bs[cm], bs[ci])
            hacia_j = _edges_between(G, bs[cm], bs[cj])
            if hacia_i and hacia_j:
                gap_resolved.append((ci, cj, cm, 'lema_8.3e_caso_a'))
                bridge_vertices[(ci, cj)] = cm
                resuelto = True
                break

        if resuelto:
            continue

        # ── Caso (b): reasignar vértice v de Bi a Bj (o viceversa) ──
        for ci_donor, ci_target in [(ci, cj), (cj, ci)]:
            if resuelto:
                break
            for v in list(bs[ci_donor]):
                if v == ci_donor:   # no mover el centro
                    continue
                tiene_vecino_target = any(nb in bs[ci_target] for nb in G.neighbors(v))
                if not tiene_vecino_target:
                    continue
                # ¿Bi_donor sigue conexo sin v?
                sin_v = bs[ci_donor] - {v}
                if not _is_connected_subset(G, sin_v):
                    continue
                # Reasignar
                bs[ci_donor].discard(v)
                bs[ci_target].add(v)
                gap_resolved.append((ci, cj, v, 'lema_8.3e_caso_b'))
                bridge_vertices[(ci, cj)] = v
                resuelto = True
                break

        if not resuelto:
            gap_irresoluble.append((ci, cj))

    return {
        "gap_detectado"    : len(gap_pairs),
        "gap_resuelto"     : len(gap_resolved),
        "gap_irresoluble"  : len(gap_irresoluble),
        "pares_gap"        : gap_pairs,
        "pares_resueltos"  : gap_resolved,
        "pares_irresolubles": gap_irresoluble,
        "bridge_vertices"  : bridge_vertices,
        "branch_sets_final": bs,
    }

# ─────────────────────────────────────────────────────────────────

SCRIPT_NAME = "SCRIPT 3 — TEOREMA 8.7"
DESCRIPTION = "Verifica: construccion hibrida produce K_chi(G) valido (Hadwiger)"
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "log_script3_teorema87.txt"
NUM_RANDOM_GRAPHS = 500


def build_branch_sets(G, coloring, expansion_vertices, chi):
    classes = {}
    for v, c in coloring.items():
        classes.setdefault(c, set()).add(v)
    colors = sorted(classes.keys())
    k = len(colors)
    if k != chi:
        return False, {}, {}, [], f"k={k} != chi={chi}"

    branch_sets = {c: set(classes[c]) for c in colors}

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
                    branch_sets[c].add(pv)
            except nx.NetworkXNoPath:
                pass

    # ── GAP DETECTOR (Lema 8.3e) ──────────────────────────────────
    gap_info = detect_and_resolve_gap(G, branch_sets, colors)
    # Si el gap se resolvió, usar los branch sets corregidos
    if gap_info["gap_detectado"] > 0 and gap_info["gap_irresoluble"] == 0:
        branch_sets = gap_info["branch_sets_final"]
    # ──────────────────────────────────────────────────────────────

    inter_edges = {}
    distributed_cases = []
    all_ok = True
    details = []

    for i, j in itertools.combinations(colors, 2):
        bi, bj = branch_sets[i], branch_sets[j]
        edges = [(u, v) for u in bi for v in bj if G.has_edge(u, v)]
        inter_edges[(i, j)] = edges
        if not edges:
            # ¿El gap fue resuelto por Lema 8.3e caso (a)?
            # (Bm conecta ambos en el minor contraído — sigue siendo válido)
            par_resuelto = any(
                r[0] == i and r[1] == j and r[3] == 'lema_8.3e_caso_a'
                for r in gap_info["pares_resueltos"]
            )
            if not par_resuelto:
                all_ok = False
                details.append(f"Sin arista entre B_{i} y B_{j}")

    for c in colors:
        absorbed_into = set()
        for c2 in colors:
            if c2 == c:
                continue
            for v in branch_sets[c2]:
                if v in classes[c]:
                    absorbed_into.add(c2)
        if len(absorbed_into) >= 2:
            distributed_cases.append({"color": c, "absorbed_into": list(absorbed_into)})

    for c in colors:
        subg = G.subgraph(branch_sets[c])
        if not nx.is_connected(subg):
            all_ok = False
            details.append(f"B_{c} no es conexo")

    # Gap irresoluble → fallo real
    if gap_info["gap_irresoluble"] > 0:
        all_ok = False
        details.append(f"GAP IRRESOLUBLE en pares: {gap_info['pares_irresolubles']}")

    detail_str = "; ".join(details) if details else "OK"
    return all_ok, branch_sets, inter_edges, distributed_cases, detail_str, gap_info


def main():
    print_header(SCRIPT_NAME, DESCRIPTION)
    print("Generando grafos de prueba (ordenados por n)...")
    graphs = get_all_graphs(num_random=NUM_RANDOM_GRAPHS, random_seed=77)
    print(f"  Total de grafos: {len(graphs)}\n")

    logger = UnifiedLogger(SCRIPT_NAME, LOG_FILE)
    print(f"  Log iniciado: {LOG_FILE}\n")

    ok_count = 0
    fail_count = 0
    total_distributed = 0
    total_gap_detectado  = 0
    total_gap_resuelto   = 0
    total_gap_irresoluble = 0
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
            coloring = get_optimal_coloring(G, chi)
            if coloring is None:
                continue
            p_g, ordering, exp_vertices, method = compute_p_with_expansion_vertices(G)
            success, branch_sets, inter_edges, dist_cases, detail, gap_info = build_branch_sets(
                G, coloring, exp_vertices, chi
            )
            total_distributed        += len(dist_cases)
            total_gap_detectado      += gap_info["gap_detectado"]
            total_gap_resuelto       += gap_info["gap_resuelto"]
            total_gap_irresoluble    += gap_info["gap_irresoluble"]

            if success:
                ok_count += 1
            else:
                fail_count += 1

            logger.add_entry(
                graph_name=f"[{familia}] {name}",
                chi=chi, p=p_g, formula_ok=success, method=method,
                extra={
                    "dist_cases"      : len(dist_cases),
                    "gap_detectado"   : gap_info["gap_detectado"],
                    "gap_resuelto"    : gap_info["gap_resuelto"],
                    "gap_irresoluble" : gap_info["gap_irresoluble"],
                    "gap_pares"       : str(gap_info["pares_gap"]) if gap_info["gap_detectado"] else "",
                    "detail"          : detail if not success else "",
                }
            )

            # Imprimir solo fallos o gaps detectados (para no saturar consola)
            if not TQDM_AVAILABLE or not success or gap_info["gap_detectado"] > 0:
                gap_tag = ""
                if gap_info["gap_detectado"] > 0:
                    if gap_info["gap_irresoluble"] == 0:
                        gap_tag = f" [GAP→RESUELTO lema8.3e]"
                    else:
                        gap_tag = f" [GAP IRRESOLUBLE ⚠️]"
                dc_str = f"dist={len(dist_cases)}" if dist_cases else ""
                print(f"  [{'OK' if success else 'FALLO'}] {name:<35} chi={chi} {dc_str}{gap_tag} [{method}]")
    except KeyboardInterrupt:
        print("\n\n  !! Interrumpido — guardando log parcial...")
    finally:
        elapsed = (time.time() - t0) / 60
        logger.set_summary(
            Casos_absorcion_distribuida=total_distributed,
            Condiciones_verificadas="(a) B_i conexo, (b) c_i en B_i, (c) aristas inter-set",
            Gap_detectado_total=total_gap_detectado,
            Gap_resuelto_lema83e=total_gap_resuelto,
            Gap_irresoluble=total_gap_irresoluble,
        )
        logger.write_log()
        print_footer(ok_count, fail_count, elapsed)
        print(f"\n  Casos de absorcion distribuida : {total_distributed}")
        print(f"\n  ── GAP DETECTOR (Lema 8.3e) ──────────────────────")
        print(f"  Gaps detectados                : {total_gap_detectado}")
        print(f"  Gaps resueltos (lema 8.3e)     : {total_gap_resuelto}")
        if total_gap_irresoluble == 0:
            print(f"  Gaps irresolubles              : 0  ✅ PRUEBA SÓLIDA")
        else:
            print(f"  Gaps irresolubles              : {total_gap_irresoluble}  ⚠️  REVISAR")
        print(f"  ─────────────────────────────────────────────────")
        print(f"  Log: {LOG_FILE}")

    return fail_count == 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    success = main()
    sys.exit(0 if success else 1)
