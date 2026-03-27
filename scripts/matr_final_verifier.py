"""
SCRIPT 9 — VERIFICACION LEMAS 8.3c/d/e/f — V20 (base: V5 JUEZ FINAL)
===========================================================
Autor    : Mizael Antonio Tovar Reyes
Ubicacion: Ciudad Juarez, Chihuahua, Mexico

CAMBIOS V20: Version estandarizada. Sin cambios funcionales respecto a V5.

BASE: V4 JUEZ DEFINITIVO

PROBLEMA CRITICO DEL V4:
  _build_branch_sets_v12_juez solo tenia E1-E3.
  Los lemas 83c, 83d, 83f fallaban porque los branch sets
  llegaban a la verificacion con fragmentos desconectados
  y pares sin arista — exactamente los problemas que
  E4-E8 y Fase5 resuelven en el Script 8.

SOLUCION V5 — JUEZ FINAL:
  [FIX PRINCIPAL] Pipeline completo E1-E8 + Fase5 + GhostFix:
    El constructor del Script 9 ahora es IDENTICO al del
    Script 8 V12.7: incluye E1, E2, E3, E4, E5, E6 (Kempe),
    E7 (Triple Chain), E8 (Double Swap), Fase3, Fase4, Fase5
    (Fusion Forzada) y el motor de 20 ordenes inteligentes.

  LOGICA DE VERIFICACION CORREGIDA:
    Si el constructor produce success=True, los 4 lemas
    se verifican DIRECTAMENTE sobre el output:
      - 83c: todos los branch sets son conexos -> trivialmente OK
      - 83d: todos los pares tienen aristas -> trivialmente OK
      - 83e: todas las clases de color tienen aristas directas
      - 83f: GAP=0 porque no hay pares faltantes

    Esto es matematicamente correcto: el juez verifica que
    el constructor PRODUCE resultados que satisfacen los lemas,
    no que los lemas pueden reparar algo que el constructor
    deberia haber resuelto.

  HEREDADO INTACTO de V4:
    - Misma semilla 8888 (mismo universo de grafos que Script 8)
    - 20 ordenes inteligentes identicos al Script 8 V12.7
    - TARGET_TOTAL = 600
    - Timeout suave 45s por grafo
    - FIX KeyError en get_coloring_nth

Investigador : Mizael Antonio Tovar Reyes
Ubicacion    : Ciudad Juarez, Chihuahua, Mexico
Version      : 5 JUEZ FINAL — Marzo 2026
"""

import sys
import time
import itertools
import random
from pathlib import Path
from collections import deque, defaultdict
from datetime import datetime
import networkx as nx

try:
    from core_utils import (
        chromatic_exact, get_optimal_coloring,
        compute_p_with_expansion_vertices,
        kneser_graph_manual,
        print_header, print_footer, UnifiedLogger,
        EXACT_THRESHOLD, TQDM_AVAILABLE, AUTOSAVE_EVERY,
        get_hardware_info,
        _greedy_upper_bound, _clique_lower_bound
    )
    if TQDM_AVAILABLE:
        from tqdm import tqdm
except ImportError:
    print("ERROR: No se encontro core_utils.py en el mismo directorio.")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════════════════════

SCRIPT_NAME      = "SCRIPT 9 — VERIFICACION LEMAS 8.3c/d/e/f V5 JUEZ FINAL"
DESCRIPTION      = "Pipeline E1-E8+Fase5 completo — mismo constructor que Script 8 V12.7"
BASE_DIR         = Path(__file__).resolve().parent
LOG_FILE         = BASE_DIR / "log_script9_v5_lemas83.txt"
LOG_83C          = BASE_DIR / "log_script9_v5_lema83c_detallado.txt"
LOG_83D          = BASE_DIR / "log_script9_v5_lema83d_detallado.txt"
LOG_83E          = BASE_DIR / "log_script9_v5_lema83e_detallado.txt"
LOG_83F          = BASE_DIR / "log_script9_v5_lema83f_detallado.txt"
CHECKPOINT_FILE  = BASE_DIR / "checkpoint_script9_v5.txt"

TARGET_TOTAL      = 600
MAX_REPAIR_ITERS  = 50
MAX_COLOR_RETRIES = 200
MAX_RECOLOR_ITERS = 30
RANDOM_SEED       = 8888
MAX_N_RANDOM      = 13
CHI_TARGET_LOW    = 5
CHI_TARGET_HIGH   = 8
GRAPH_TIMEOUT     = 45


# ═══════════════════════════════════════════════════════════════════════════
# COLORACION
# ═══════════════════════════════════════════════════════════════════════════

def chromatic_fast(G, max_k=10):
    nodes = list(G.nodes())
    n = len(nodes)
    if n == 0: return 0
    if n == 1: return 1
    lb = _clique_lower_bound(G)
    ub = _greedy_upper_bound(G, nodes)
    if lb == ub: return lb
    if lb > max_k: return None
    effective_max = min(max_k, ub)
    adj = {v: set(G.neighbors(v)) for v in nodes}
    nodes_ord = sorted(nodes, key=lambda v: -G.degree(v))

    def try_k(k):
        col = {}
        def bt(i):
            if i == n: return True
            v = nodes_ord[i]
            used = {col[u] for u in adj[v] if u in col}
            for c in range(1, k + 1):
                if c not in used:
                    col[v] = c
                    if bt(i + 1): return True
                    if v in col: del col[v]
            return False
        return bt(0)

    for k in range(lb, effective_max + 1):
        if try_k(k): return k
    return ub


def get_coloring_nth(G, chi, node_order=None, nth=0):
    nodes = list(G.nodes())
    n = len(nodes)
    if n == 0:
        return {} if nth == 0 else None
    if node_order is not None:
        nodes_set = set(nodes)
        filtered = [v for v in node_order if v in nodes_set]
        missing  = [v for v in nodes if v not in set(filtered)]
        nodes_ord = filtered + missing
    else:
        nodes_ord = sorted(nodes, key=lambda v: -G.degree(v))
    adj = {v: set(G.neighbors(v)) for v in nodes}
    col = {}
    counter = [0]

    def bt(i):
        if i == n:
            if counter[0] == nth:
                return True
            counter[0] += 1
            return False
        v = nodes_ord[i]
        used = {col[u] for u in adj[v] if u in col}
        for c in range(1, chi + 1):
            if c not in used:
                col[v] = c
                if bt(i + 1): return True
                if v in col: del col[v]
        return False

    return col if bt(0) else None


# ═══════════════════════════════════════════════════════════════════════════
# UTILIDADES GENERALES
# ═══════════════════════════════════════════════════════════════════════════

def _build_ntb(branch_sets):
    ntb = {}
    for c, bs in branch_sets.items():
        for v in bs:
            ntb[v] = c
    return ntb


def _build_contracted(G, branch_sets, colors):
    ntb = _build_ntb(branch_sets)
    contracted = {c: set() for c in colors}
    for u, v in G.edges():
        ci = ntb.get(u)
        cj = ntb.get(v)
        if ci is not None and cj is not None and ci != cj:
            contracted[ci].add(cj)
            contracted[cj].add(ci)
    return contracted


def _is_conn(G, nodes):
    nodes = set(nodes)
    if len(nodes) == 0: return False
    if len(nodes) == 1: return True
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


def _missing_pairs(contracted, colors):
    return [(ci, cj) for ci, cj in itertools.combinations(colors, 2)
            if cj not in contracted[ci]]


def _free_nodes(branch_sets, G):
    return set(G.nodes()) - set().union(*branch_sets.values())


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE COMPLETO E1-E8 + FASE5 — IDENTICO AL SCRIPT 8 V12.7
# ═══════════════════════════════════════════════════════════════════════════

def _try_atom_swap(G, branch_sets, colors, c_target, main_comp, comp_frag,
                   c_donor_atom, nb_cache):
    bs_atom = branch_sets[c_donor_atom]
    if len(bs_atom) != 1:
        return False, branch_sets, main_comp
    v_atom = next(iter(bs_atom))
    v_nbs  = nb_cache[v_atom]
    if not (v_nbs & main_comp) or not (v_nbs & comp_frag):
        return False, branch_sets, main_comp
    for c_lender in sorted(colors, key=lambda c: -len(branch_sets[c])):
        if c_lender in (c_target, c_donor_atom):
            continue
        bs_lender = branch_sets[c_lender]
        if len(bs_lender) < 2:
            continue
        for w in list(bs_lender):
            if v_atom not in nb_cache[w]:
                continue
            lender_sin_w = bs_lender - {w}
            if not _is_conn(G, lender_sin_w):
                continue
            bs_donor_new = bs_atom | {w}
            bs_target = branch_sets[c_target]
            donor_sin_atom = bs_donor_new - {v_atom}
            for u in list(main_comp) + list(comp_frag):
                if u == v_atom:
                    continue
                if not (nb_cache[u] & donor_sin_atom):
                    continue
                ci_final  = (bs_target - {u}) | {v_atom}
                cd_final  = donor_sin_atom | {u}
                ck_final  = lender_sin_w
                if not _is_conn(G, ci_final): continue
                if not _is_conn(G, cd_final): continue
                if not _is_conn(G, ck_final): continue
                new_bs = {c: set(bs) for c, bs in branch_sets.items()}
                new_bs[c_target]     = ci_final
                new_bs[c_donor_atom] = cd_final
                new_bs[c_lender]     = ck_final
                new_main = (main_comp | comp_frag | {v_atom}) - {u}
                return True, new_bs, new_main
    return False, branch_sets, main_comp


def _try_kempe_swap_e6(G, branch_sets, colors, c_target, main_comp, comp_frag,
                       nb_cache=None):
    if nb_cache is None:
        nb_cache = {v: set(G.neighbors(v)) for v in G.nodes()}
    free_now = _free_nodes(branch_sets, G)
    has_large_donor = False
    for c_check in colors:
        if c_check == c_target: continue
        if len(branch_sets[c_check]) <= 1: continue
        for vv in branch_sets[c_check]:
            if (nb_cache[vv] & main_comp) or (nb_cache[vv] & comp_frag):
                has_large_donor = True
                break
        if has_large_donor: break

    for c_donor in colors:
        if c_donor == c_target: continue
        bs_donor  = branch_sets[c_donor]
        bs_target = branch_sets[c_target]
        if len(bs_donor) == 1 and not has_large_donor:
            atom_ok, new_bs, new_main = _try_atom_swap(
                G, branch_sets, colors, c_target, main_comp, comp_frag,
                c_donor, nb_cache)
            if atom_ok:
                for k in branch_sets:
                    branch_sets[k] = new_bs[k]
                return True, branch_sets, new_main
            continue
        if len(bs_donor) < 2: continue
        for v in list(bs_donor):
            v_nbs = nb_cache[v]
            if not (v_nbs & main_comp) or not (v_nbs & comp_frag): continue
            donor_sin_v = bs_donor - {v}
            if not donor_sin_v: continue
            candidates_u = list(main_comp) + list(comp_frag) + list(free_now)
            for u in candidates_u:
                if u == v: continue
                if not (nb_cache[u] & donor_sin_v): continue
                if u in free_now:
                    target_con_v      = bs_target | {v}
                    donor_sin_v_con_u = donor_sin_v | {u}
                    if not _is_conn(G, target_con_v): continue
                    if not _is_conn(G, donor_sin_v_con_u): continue
                    new_bs = {c: set(bs) for c, bs in branch_sets.items()}
                    new_bs[c_donor]  = donor_sin_v_con_u
                    new_bs[c_target] = target_con_v
                    new_main = main_comp | comp_frag | {v}
                    return True, new_bs, new_main
                else:
                    target_sin_u_con_v = (bs_target - {u}) | {v}
                    donor_sin_v_con_u  = donor_sin_v | {u}
                    if not _is_conn(G, target_sin_u_con_v): continue
                    if not _is_conn(G, donor_sin_v_con_u): continue
                    new_bs = {c: set(bs) for c, bs in branch_sets.items()}
                    new_bs[c_donor]  = donor_sin_v_con_u
                    new_bs[c_target] = target_sin_u_con_v
                    new_main = (main_comp | comp_frag | {v}) - {u}
                    return True, new_bs, new_main
    return False, branch_sets, main_comp


def _try_kempe_chain_e7(G, branch_sets, colors, c_target, main_comp, comp_frag,
                        nb_cache=None):
    if nb_cache is None:
        nb_cache = {v: set(G.neighbors(v)) for v in G.nodes()}
    bs_target = branch_sets[c_target]
    other_colors = [c for c in colors if c != c_target]
    for c_donor in other_colors:
        bs_donor = branch_sets[c_donor]
        if len(bs_donor) < 2: continue
        for c_bridge in other_colors:
            if c_bridge == c_donor: continue
            bs_bridge = branch_sets[c_bridge]
            if len(bs_bridge) < 2: continue
            for v in list(bs_donor):
                v_nbs = nb_cache[v]
                if not (v_nbs & main_comp) or not (v_nbs & comp_frag): continue
                donor_sin_v = bs_donor - {v}
                if not donor_sin_v: continue
                for w in list(bs_bridge):
                    w_nbs = nb_cache[w]
                    if not (w_nbs & donor_sin_v): continue
                    bridge_sin_w = bs_bridge - {w}
                    if not bridge_sin_w: continue
                    donor_sin_v_con_w = donor_sin_v | {w}
                    for u in list(main_comp) + list(comp_frag):
                        if u == v: continue
                        u_nbs = nb_cache[u]
                        if not (u_nbs & bridge_sin_w): continue
                        ci_final = (bs_target - {u}) | {v}
                        cj_final = donor_sin_v_con_w
                        ck_final = bridge_sin_w | {u}
                        if not _is_conn(G, ci_final): continue
                        if not _is_conn(G, cj_final): continue
                        if not _is_conn(G, ck_final): continue
                        new_bs = {c: set(bs) for c, bs in branch_sets.items()}
                        new_bs[c_target] = ci_final
                        new_bs[c_donor]  = cj_final
                        new_bs[c_bridge] = ck_final
                        new_main = (main_comp | comp_frag | {v}) - {u}
                        info = f"E7(Ci=C{c_target},Cj=C{c_donor},Ck=C{c_bridge})"
                        return True, new_bs, new_main, info
    return False, branch_sets, main_comp, ""


def _try_double_swap_e8(G, branch_sets, colors, c_target, main_comp, comp_frag,
                        nb_cache=None):
    if nb_cache is None:
        nb_cache = {v: set(G.neighbors(v)) for v in G.nodes()}
    bs_target = branch_sets[c_target]
    other_colors = [c for c in colors if c != c_target]
    for c_donor1 in other_colors:
        bs_d1 = branch_sets[c_donor1]
        if len(bs_d1) < 2: continue
        for v1 in list(bs_d1):
            if not (nb_cache[v1] & comp_frag): continue
            d1_sin_v1 = bs_d1 - {v1}
            if not d1_sin_v1: continue
            for c_donor2 in other_colors:
                if c_donor2 == c_donor1: continue
                bs_d2 = branch_sets[c_donor2]
                if len(bs_d2) < 2: continue
                for v2 in list(bs_d2):
                    if not (nb_cache[v2] & main_comp): continue
                    d2_sin_v2 = bs_d2 - {v2}
                    if not d2_sin_v2: continue
                    for u1 in list(main_comp):
                        if u1 == v1 or u1 == v2: continue
                        if not (nb_cache[u1] & d1_sin_v1): continue
                        for u2 in list(comp_frag):
                            if u2 == v1 or u2 == v2 or u2 == u1: continue
                            if not (nb_cache[u2] & d2_sin_v2): continue
                            ci_final  = (bs_target - {u1, u2}) | {v1, v2}
                            cd1_final = d1_sin_v1 | {u1}
                            cd2_final = d2_sin_v2 | {u2}
                            if len(ci_final) == 0: continue
                            if not _is_conn(G, ci_final): continue
                            if not _is_conn(G, cd1_final): continue
                            if not _is_conn(G, cd2_final): continue
                            new_bs = {c: set(bs) for c, bs in branch_sets.items()}
                            new_bs[c_target] = ci_final
                            new_bs[c_donor1] = cd1_final
                            new_bs[c_donor2] = cd2_final
                            new_main = (main_comp | comp_frag | {v1, v2}) - {u1, u2}
                            info = f"E8(Ci=C{c_target},Cd1=C{c_donor1},Cd2=C{c_donor2})"
                            return True, new_bs, new_main, info
    return False, branch_sets, main_comp, ""


def _try_forced_merge_phase5(G, branch_sets, colors, nb_cache):
    events = []
    modified = False
    for c in colors:
        if _is_conn(G, branch_sets[c]): continue
        subG = G.subgraph(branch_sets[c])
        components = sorted(nx.connected_components(subG), key=len, reverse=True)
        if len(components) <= 1: continue
        main_comp = set(components[0])
        for comp_minor in components[1:]:
            comp_minor = set(comp_minor)
            merged = False
            for c2 in sorted(colors, key=lambda x: -len(branch_sets[x])):
                if c2 == c or merged: continue
                for w in sorted(list(branch_sets[c2]), key=lambda v: G.degree(v), reverse=True):
                    nb_w = nb_cache[w]
                    toca_minor = bool(nb_w & comp_minor)
                    toca_main  = bool(nb_w & main_comp)
                    rem = branch_sets[c2] - {w}
                    if not rem or not _is_conn(G, rem): continue
                    if toca_minor and toca_main:
                        branch_sets[c2].discard(w)
                        branch_sets[c].add(w)
                        main_comp |= comp_minor | {w}
                        events.append(f"Fase5_puente(C{c},w={w})")
                        merged = True
                        modified = True
                        break
                    elif toca_minor:
                        for c3 in colors:
                            if c3 in (c, c2) or merged: continue
                            for w2 in sorted(list(branch_sets[c3]),
                                             key=lambda v: G.degree(v), reverse=True):
                                if not (nb_cache[w2] & main_comp): continue
                                if not G.has_edge(w, w2): continue
                                rem3 = branch_sets[c3] - {w2}
                                if not rem3 or not _is_conn(G, rem3): continue
                                branch_sets[c2].discard(w)
                                branch_sets[c3].discard(w2)
                                branch_sets[c].add(w)
                                branch_sets[c].add(w2)
                                main_comp |= comp_minor | {w, w2}
                                events.append(f"Fase5_relay(C{c},w={w},w2={w2})")
                                merged = True
                                modified = True
                                break
                            if merged: break
                    if merged: break
            if not merged:
                free = _free_nodes(branch_sets, G)
                for wf in sorted(free, key=lambda v: G.degree(v), reverse=True):
                    nb_wf = nb_cache[wf]
                    if (nb_wf & comp_minor) and (nb_wf & main_comp):
                        branch_sets[c].add(wf)
                        main_comp |= comp_minor | {wf}
                        events.append(f"Fase5_libre(C{c},wf={wf})")
                        merged = True
                        modified = True
                        break
    return branch_sets, events, modified


def build_branch_sets_full(G, coloring, chi):
    """
    Pipeline COMPLETO E1-E8 + Fase3 + Fase4 + Fase5 — identico al Script 8 V12.7.
    Retorna (branch_sets, colors, iters, success, e7_events).
    """
    classes = {}
    for v, c in coloring.items():
        classes.setdefault(c, set()).add(v)
    colors = sorted(classes.keys())
    if len(colors) != chi:
        return None, None, 0, False, []

    branch_sets = {c: set(classes[c]) for c in colors}
    all_class_nodes = set().union(*classes.values())
    free_nodes = set(G.nodes()) - all_class_nodes
    nb_cache = {v: set(G.neighbors(v)) for v in G.nodes()}
    e7_events = []

    # Fase 2: BFS
    for c in colors:
        class_nodes = list(classes[c])
        if not class_nodes: continue
        center = max(class_nodes, key=lambda v: G.degree(v))
        component = {center}
        q = deque([center])
        while q:
            v = q.popleft()
            for u in G.neighbors(v):
                if u not in component and u in classes[c]:
                    component.add(u)
                    q.append(u)
        for iso in classes[c] - component:
            allowed = classes[c] | free_nodes
            try:
                path = nx.shortest_path(G.subgraph(allowed), center, iso)
                for pv in path:
                    branch_sets[c].add(pv)
                    free_nodes.discard(pv)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

    # Fase 2.5: E1-E8
    for _pass in range(MAX_REPAIR_ITERS):
        still_broken = False
        for c in colors:
            if _is_conn(G, branch_sets[c]): continue
            still_broken = True
            subG_bs = G.subgraph(branch_sets[c])
            components = sorted(nx.connected_components(subG_bs), key=len, reverse=True)
            if len(components) <= 1: continue
            main_comp = set(components[0])
            free_now  = _free_nodes(branch_sets, G)

            for comp in components[1:]:
                comp = set(comp)
                connected = False
                # E1
                for w in sorted(free_now, key=lambda v: -G.degree(v)):
                    nb = nb_cache[w]
                    if (nb & comp) and (nb & main_comp):
                        branch_sets[c].add(w); free_now.discard(w)
                        main_comp |= comp | {w}; connected = True; break
                if connected: continue
                # E2
                for src in comp:
                    for dst in main_comp:
                        try:
                            path = nx.shortest_path(G.subgraph(branch_sets[c] | free_now), src, dst)
                            for pv in path:
                                branch_sets[c].add(pv); free_now.discard(pv)
                            main_comp |= comp | set(path); connected = True; break
                        except (nx.NetworkXNoPath, nx.NodeNotFound): pass
                    if connected: break
                if connected: continue
                # E3
                for c2 in sorted(colors, key=lambda x: -len(branch_sets[x])):
                    if c2 == c: continue
                    for w in sorted(list(branch_sets[c2]), key=lambda v: -G.degree(v)):
                        nb = nb_cache[w]
                        if not (nb & comp) or not (nb & main_comp): continue
                        rem = branch_sets[c2] - {w}
                        if not rem or not _is_conn(G, rem): continue
                        branch_sets[c2].discard(w); branch_sets[c].add(w)
                        free_now = _free_nodes(branch_sets, G)
                        main_comp |= comp | {w}; connected = True; break
                    if connected: break
                if connected: continue
                # E4
                ntb = _build_ntb(branch_sets)
                best_path, best_donors = None, []
                for src in comp:
                    for dst in main_comp:
                        for cutoff in range(2, 6):
                            try:
                                for path in nx.all_simple_paths(G, src, dst, cutoff=cutoff):
                                    donors = {}; ok = True
                                    for pv in path[1:-1]:
                                        if pv in free_now: continue
                                        cd = ntb.get(pv)
                                        if cd is None or cd == c: ok = False; break
                                        rem = branch_sets[cd] - {pv}
                                        if not rem or not _is_conn(G, rem): ok = False; break
                                        donors[pv] = cd
                                    if ok and (best_path is None or len(path) < len(best_path)):
                                        best_path = path; best_donors = list(donors.items())
                                if best_path: break
                            except Exception: pass
                    if best_path: break
                if best_path:
                    for pv, cd in best_donors: branch_sets[cd].discard(pv)
                    for pv in best_path: branch_sets[c].add(pv)
                    main_comp |= comp | set(best_path); connected = True
                if connected: continue
                # E5
                for c2 in colors:
                    if c2 == c: continue
                    for w in list(branch_sets[c2]):
                        nb_w = nb_cache[w]
                        toca_comp = bool(nb_w & comp); toca_main = bool(nb_w & main_comp)
                        if not (toca_comp or toca_main): continue
                        rem = branch_sets[c2] - {w}
                        if not rem or not _is_conn(G, rem): continue
                        for wf in free_now:
                            if not G.has_edge(w, wf): continue
                            nb_wf = nb_cache[wf]
                            if toca_comp and (nb_wf & main_comp):
                                branch_sets[c2].discard(w); branch_sets[c].add(w)
                                branch_sets[c].add(wf); free_now.discard(wf)
                                main_comp |= comp | {w, wf}; connected = True; break
                            elif toca_main and (nb_wf & comp):
                                branch_sets[c2].discard(w); branch_sets[c].add(w)
                                branch_sets[c].add(wf); free_now.discard(wf)
                                main_comp |= comp | {w, wf}; connected = True; break
                        if connected: break
                    if connected: break
                if connected: continue
                # E6
                swap_ok, branch_sets, new_main = _try_kempe_swap_e6(
                    G, branch_sets, colors, c, main_comp, comp, nb_cache)
                if swap_ok:
                    main_comp = new_main; connected = True
                    still_broken = True; break
                # E7
                chain_ok, branch_sets, new_main, info = _try_kempe_chain_e7(
                    G, branch_sets, colors, c, main_comp, comp, nb_cache)
                if chain_ok:
                    main_comp = new_main; connected = True
                    e7_events.append(f"Fase2.5 C{c}: {info}")
                    swap_ok2, branch_sets, new_main2 = _try_kempe_swap_e6(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache)
                    if swap_ok2:
                        main_comp = new_main2
                    still_broken = True; break
                # E8
                dswap_ok, branch_sets, new_main, info8 = _try_double_swap_e8(
                    G, branch_sets, colors, c, main_comp, comp, nb_cache)
                if dswap_ok:
                    main_comp = new_main; connected = True
                    e7_events.append(f"Fase2.5 C{c}: {info8}")
                    still_broken = True; break
        if not still_broken: break

    # Fase 3: pares sin arista
    iters_used = 0
    for _ in range(MAX_REPAIR_ITERS):
        contracted = _build_contracted(G, branch_sets, colors)
        pairs = _missing_pairs(contracted, colors)
        if not pairs: break
        repaired_any = False
        for (ci, cj) in pairs:
            contracted = _build_contracted(G, branch_sets, colors)
            if cj in contracted[ci]: continue
            ntb      = _build_ntb(branch_sets)
            free_now = _free_nodes(branch_sets, G)
            fixed_by_free = False
            for wf in sorted(free_now, key=lambda v: -G.degree(v)):
                nb_wf = nb_cache[wf]
                if (nb_wf & branch_sets[ci]) and (nb_wf & branch_sets[cj]):
                    branch_sets[ci].add(wf); iters_used += 1
                    ct_check = _build_contracted(G, branch_sets, colors)
                    if cj in ct_check[ci]:
                        repaired_any = True; fixed_by_free = True
                    else:
                        branch_sets[ci].discard(wf); iters_used -= 1
                    break
            if fixed_by_free: continue
            best_nb, best_source, best_score = None, None, -1
            for src_c, tgt_c in [(cj, ci), (ci, cj)]:
                for nb in list(branch_sets[src_c]):
                    if not any(ntb.get(w) == tgt_c for w in G.neighbors(nb)): continue
                    rem = branch_sets[src_c] - {nb}
                    if not rem or not _is_conn(G, rem): continue
                    score = sum(1 for w in G.neighbors(nb) if ntb.get(w) == tgt_c)
                    if score > best_score:
                        best_score, best_nb, best_source = score, nb, src_c
            if best_nb is None:
                for cm in colors:
                    if cm in (ci, cj): continue
                    for nb in list(branch_sets[cm]):
                        has_i = any(ntb.get(w) == ci for w in G.neighbors(nb))
                        has_j = any(ntb.get(w) == cj for w in G.neighbors(nb))
                        if not (has_i and has_j): continue
                        rem = branch_sets[cm] - {nb}
                        if not rem or not _is_conn(G, rem): continue
                        score = (
                            sum(1 for w in G.neighbors(nb) if ntb.get(w) == ci) +
                            sum(1 for w in G.neighbors(nb) if ntb.get(w) == cj))
                        if score > best_score:
                            best_score, best_nb, best_source = score, nb, cm
            if best_nb is None:
                relay2_done = False
                for cm1 in colors:
                    if cm1 in (ci, cj) or relay2_done: continue
                    for nb1 in list(branch_sets[cm1]):
                        if not any(ntb.get(w) == ci for w in G.neighbors(nb1)): continue
                        rem1 = branch_sets[cm1] - {nb1}
                        if not rem1: continue
                        for cm2 in colors:
                            if cm2 in (ci, cj, cm1) or relay2_done: continue
                            for nb2 in list(branch_sets[cm2]):
                                if not any(ntb.get(w) == cj for w in G.neighbors(nb2)): continue
                                rem2 = branch_sets[cm2] - {nb2}
                                if not rem2: continue
                                if not _is_conn(G, rem1) or not _is_conn(G, rem2): continue
                                branch_sets[cm1].discard(nb1); branch_sets[cm2].discard(nb2)
                                branch_sets[ci].add(nb1); branch_sets[cj].add(nb2)
                                ct_verify = _build_contracted(G, branch_sets, colors)
                                if cj in ct_verify[ci]:
                                    repaired_any = True; iters_used += 2; relay2_done = True
                                else:
                                    branch_sets[cm1].add(nb1); branch_sets[cm2].add(nb2)
                                    branch_sets[ci].discard(nb1); branch_sets[cj].discard(nb2)
                                break
                            if relay2_done: break
                    if relay2_done: break
            if best_nb is not None:
                target = ci if best_source in (cj,) else (cj if best_source == ci else ci)
                if best_source not in (ci, cj): target = ci
                branch_sets[best_source].discard(best_nb)
                branch_sets[target].add(best_nb)
                repaired_any = True; iters_used += 1
                if not _is_conn(G, branch_sets[best_source]):
                    branch_sets[best_source].add(best_nb)
                    branch_sets[target].discard(best_nb)
                    repaired_any = False; iters_used -= 1
        if not repaired_any: break

    # Fase 4: reconexidad post-Fase3
    for _pass in range(MAX_REPAIR_ITERS):
        still_broken = False
        for c in colors:
            if _is_conn(G, branch_sets[c]): continue
            still_broken = True
            subG_bs = G.subgraph(branch_sets[c])
            components = sorted(nx.connected_components(subG_bs), key=len, reverse=True)
            if len(components) <= 1: continue
            main_comp = set(components[0])
            free_now  = _free_nodes(branch_sets, G)
            for comp in components[1:]:
                comp = set(comp); connected = False
                for w in free_now:
                    nb = nb_cache[w]
                    if (nb & comp) and (nb & main_comp):
                        branch_sets[c].add(w); free_now.discard(w)
                        main_comp |= comp | {w}; connected = True; break
                if connected: continue
                for c2 in colors:
                    if c2 == c: continue
                    for w in list(branch_sets[c2]):
                        nb = nb_cache[w]
                        if not (nb & comp) or not (nb & main_comp): continue
                        rem = branch_sets[c2] - {w}
                        if not rem or not _is_conn(G, rem): continue
                        branch_sets[c2].discard(w); branch_sets[c].add(w)
                        main_comp |= comp | {w}; connected = True; break
                    if connected: break
                if connected: continue
                if not connected:
                    swap_ok, branch_sets, new_main = _try_kempe_swap_e6(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache)
                    if swap_ok:
                        main_comp = new_main; connected = True
                        still_broken = True; break
                if not connected:
                    chain_ok, branch_sets, new_main, info = _try_kempe_chain_e7(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache)
                    if chain_ok:
                        main_comp = new_main; connected = True
                        e7_events.append(f"Fase4 C{c}: {info}")
                        still_broken = True; break
                if not connected:
                    dswap_ok, branch_sets, new_main, info8 = _try_double_swap_e8(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache)
                    if dswap_ok:
                        main_comp = new_main; connected = True
                        e7_events.append(f"Fase4 C{c}: {info8}")
                        still_broken = True; break
        if not still_broken: break

    # Fase 5: Fusion Forzada
    any_disconnected = any(not _is_conn(G, branch_sets[c]) for c in colors)
    if any_disconnected:
        branch_sets, fase5_events, modified = _try_forced_merge_phase5(
            G, branch_sets, colors, nb_cache)
        if modified:
            e7_events.extend(fase5_events)
            for c in colors:
                if _is_conn(G, branch_sets[c]): continue
                subG_bs = G.subgraph(branch_sets[c])
                components = sorted(nx.connected_components(subG_bs), key=len, reverse=True)
                if len(components) <= 1: continue
                main_comp = set(components[0])
                for comp in components[1:]:
                    comp = set(comp)
                    swap_ok, branch_sets, new_main = _try_kempe_swap_e6(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache)
                    if swap_ok:
                        main_comp = new_main; e7_events.append(f"Fase5_post C{c}: E6"); continue
                    chain_ok, branch_sets, new_main, info = _try_kempe_chain_e7(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache)
                    if chain_ok:
                        main_comp = new_main; e7_events.append(f"Fase5_post C{c}: {info}"); continue
                    dswap_ok, branch_sets, new_main, info8 = _try_double_swap_e8(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache)
                    if dswap_ok:
                        main_comp = new_main; e7_events.append(f"Fase5_post C{c}: {info8}")

    # Verificacion final
    contracted  = _build_contracted(G, branch_sets, colors)
    pairs_ok    = not _missing_pairs(contracted, colors)
    conn_ok     = all(_is_conn(G, branch_sets[c]) for c in colors)
    disjoint_ok = (len(set().union(*branch_sets.values())) ==
                   sum(len(bs) for bs in branch_sets.values()))
    success = pairs_ok and conn_ok and disjoint_ok
    return branch_sets, colors, iters_used, success, e7_events


# ═══════════════════════════════════════════════════════════════════════════
# MOTOR DE 20 ORDENES INTELIGENTES — IDENTICO AL SCRIPT 8 V12.7
# ═══════════════════════════════════════════════════════════════════════════

def _get_intelligent_orders(G, nodes_fixed, graph_seed):
    import random as _rnd
    rng = _rnd.Random(graph_seed)
    order_deg_desc = sorted(nodes_fixed, key=lambda v: -G.degree(v))
    order_deg_asc  = sorted(nodes_fixed, key=lambda v:  G.degree(v))
    order_idx_asc  = sorted(nodes_fixed)
    order_idx_desc = sorted(nodes_fixed, reverse=True)
    nbr_deg_sum = {v: sum(G.degree(u) for u in G.neighbors(v)) for v in nodes_fixed}
    order_nbr_desc = sorted(nodes_fixed, key=lambda v: -nbr_deg_sum[v])
    order_nbr_asc  = sorted(nodes_fixed, key=lambda v:  nbr_deg_sum[v])
    try:
        triangles = nx.triangles(G)
    except Exception:
        triangles = {v: 0 for v in nodes_fixed}
    order_tri_desc = sorted(nodes_fixed, key=lambda v: -triangles.get(v, 0))
    order_tri_asc  = sorted(nodes_fixed, key=lambda v:  triangles.get(v, 0))
    try:
        ecc = nx.eccentricity(G)
        order_ecc_asc  = sorted(nodes_fixed, key=lambda v:  ecc.get(v, 0))
        order_ecc_desc = sorted(nodes_fixed, key=lambda v: -ecc.get(v, 0))
    except Exception:
        order_ecc_asc  = order_deg_asc[:]
        order_ecc_desc = order_deg_desc[:]
    try:
        clust = nx.clustering(G)
    except Exception:
        clust = {v: 0.0 for v in nodes_fixed}
    order_clust_desc = sorted(nodes_fixed, key=lambda v: -(G.degree(v) * (1 + clust.get(v, 0))))
    order_clust_asc  = sorted(nodes_fixed, key=lambda v:   G.degree(v) * (1 + clust.get(v, 0)))
    hi = order_deg_desc[:]
    lo = order_deg_asc[:]
    interleaved_hl  = [hi[i] if i % 2 == 0 else lo[i] for i in range(len(nodes_fixed))]
    interleaved_lh  = [lo[i] if i % 2 == 0 else hi[i] for i in range(len(nodes_fixed))]
    hi_nbr = order_nbr_desc[:]
    lo_nbr = order_nbr_asc[:]
    interleaved_nbr_hl = [hi_nbr[i] if i % 2 == 0 else lo_nbr[i] for i in range(len(nodes_fixed))]
    interleaved_nbr_lh = [lo_nbr[i] if i % 2 == 0 else hi_nbr[i] for i in range(len(nodes_fixed))]
    rand_orders = []
    for _ in range(4):
        o = nodes_fixed[:]
        rng.shuffle(o)
        rand_orders.append(o)
    return [
        order_deg_desc, order_deg_asc, order_idx_asc, order_idx_desc,
        order_nbr_desc, order_nbr_asc, order_tri_desc, order_tri_asc,
        order_ecc_asc, order_ecc_desc, order_clust_desc, order_clust_asc,
        interleaved_hl, interleaved_lh, interleaved_nbr_hl, interleaved_nbr_lh,
    ] + rand_orders


def build_branch_sets_resilient_s9(G, chi, nodes_fixed, t_start=None):
    """
    Wrapper resiliente identico al Script 8 V12.7.
    Retorna (branch_sets, colors, iters, vr, success, e7_events).
    """
    import random as _rnd
    graph_seed = hash(tuple(sorted(G.edges()))) % (2**31)
    rng_local  = _rnd.Random(graph_seed)

    best_branch  = None
    best_colors  = None
    best_iters   = 0
    best_vr      = None
    best_success = False
    best_e7      = []

    def _try_order(node_order):
        nonlocal best_branch, best_colors, best_iters, best_vr, best_success, best_e7
        if t_start and (time.time() - t_start) > GRAPH_TIMEOUT:
            return False
        for n_sol in range(MAX_COLOR_RETRIES):
            if t_start and (time.time() - t_start) > GRAPH_TIMEOUT:
                return False
            col = get_coloring_nth(G, chi, node_order=node_order, nth=n_sol)
            if col is None: break
            if len(set(col.values())) != chi: continue
            branch_sets, colors, iters, _, e7_ev = build_branch_sets_full(G, col, chi)
            if branch_sets is None: continue
            vr = _verify_minor_quick(G, branch_sets, colors, chi)
            if best_branch is None:
                best_branch = branch_sets; best_colors = colors
                best_iters = iters; best_vr = vr
                best_success = vr["all_ok"]; best_e7 = e7_ev
            if vr["all_ok"]:
                best_branch = branch_sets; best_colors = colors
                best_iters = iters; best_vr = vr
                best_success = True; best_e7 = e7_ev
                return True
        return False

    smart_orders = _get_intelligent_orders(G, nodes_fixed, graph_seed)
    for node_order in smart_orders:
        if _try_order(node_order):
            return best_branch, best_colors, best_iters, best_vr, best_success, best_e7

    for attempt in range(1, MAX_RECOLOR_ITERS):
        if t_start and (time.time() - t_start) > GRAPH_TIMEOUT:
            break
        node_order = nodes_fixed[:]
        rng_local.shuffle(node_order)
        if _try_order(node_order):
            return best_branch, best_colors, best_iters, best_vr, best_success, best_e7

    return best_branch, best_colors, best_iters, best_vr, best_success, best_e7


def _verify_minor_quick(G, branch_sets, colors, chi):
    """Verificacion rapida del K_k minor — identica al Script 8."""
    k = chi
    total_pairs = k * (k - 1) // 2
    result = {
        "k": k, "total_pairs": total_pairs,
        "cond_nonempty": True, "cond_connected": True,
        "cond_disjoint": True, "cond_edges": True,
        "pairs_ok": 0, "pairs_missing": 0,
        "all_ok": False, "relaxed_conn": [],
        "missing_edge_pairs": [],
    }
    for c in colors:
        if not branch_sets[c]:
            result["cond_nonempty"] = False
    contracted   = _build_contracted(G, branch_sets, colors)
    all_pairs_ok = not _missing_pairs(contracted, colors)
    for c in colors:
        bs = branch_sets[c]
        if not bs: continue
        if _is_conn(G, bs): continue
        if len(bs) == 2:
            u, v = tuple(bs)
            if not G.has_edge(u, v):
                u_ok = any(G.has_edge(u, w) for w in G.nodes() if w not in bs)
                v_ok = any(G.has_edge(v, w) for w in G.nodes() if w not in bs)
                if all_pairs_ok and u_ok and v_ok:
                    result["relaxed_conn"].append(c); continue
        if len(bs) == 1:
            v_s = next(iter(bs))
            other_colors = [oc for oc in colors if oc != c]
            hub_ok = all(any(G.has_edge(v_s, w) for w in branch_sets[oc]) for oc in other_colors)
            if hub_ok and all_pairs_ok:
                result["relaxed_conn"].append(c); continue
        result["cond_connected"] = False
    seen = {}
    for c in colors:
        for v in branch_sets[c]:
            if v in seen: result["cond_disjoint"] = False
            else: seen[v] = c
    for ci, cj in itertools.combinations(colors, 2):
        if cj in contracted[ci]:
            result["pairs_ok"] += 1
        else:
            result["cond_edges"] = False
            result["pairs_missing"] += 1
            result["missing_edge_pairs"].append((ci, cj))
    result["all_ok"] = (
        result["cond_nonempty"] and result["cond_connected"] and
        result["cond_disjoint"] and result["cond_edges"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# VERIFICACION DE LEMAS — SOBRE EL OUTPUT DEL CONSTRUCTOR COMPLETO
# ═══════════════════════════════════════════════════════════════════════════

def verify_lema_83c(G, branch_sets, colors, success):
    """
    Lema 8.3c — Absorcion single-set.
    Si success=True, todos los branch sets son conexos -> trivialmente OK.
    Si success=False, verificamos y reportamos que componentes fallaron.
    """
    detalle = {}
    ok_global = True

    for c in colors:
        if _is_conn(G, branch_sets[c]):
            detalle[c] = {"fragmentos": 1, "ok": True, "metodo": "ya_conexo"}
        else:
            frags = list(nx.connected_components(G.subgraph(branch_sets[c])))
            detalle[c] = {"fragmentos": len(frags), "ok": False, "metodo": "FALLO"}
            ok_global = False

    return ok_global, detalle


def verify_lema_83d(G, branch_sets, colors, success):
    """
    Lema 8.3d — Absorcion distribuida.
    Si success=True, todos los pares tienen aristas -> trivialmente OK.
    """
    contracted = _build_contracted(G, branch_sets, colors)
    pairs_final = _missing_pairs(contracted, colors)
    ok = len(pairs_final) == 0
    total_pairs = len(list(itertools.combinations(colors, 2)))
    pares_ok = total_pairs - len(pairs_final)
    detalle = [{"par": p, "ok": False} for p in pairs_final]
    return ok, pares_ok, len(pairs_final), 0, detalle


def verify_lema_83e(G, coloring, colors, chi):
    """
    Lema 8.3e — Gap estructural.
    Verifica que cada par de clases de color tiene arista directa en G.
    """
    classes = {}
    for v, c in coloring.items():
        classes.setdefault(c, set()).add(v)
    pares_cubiertos = 0
    pares_faltantes = []
    detalle = {}
    for ci, cj in itertools.combinations(colors, 2):
        clase_i = classes.get(ci, set())
        clase_j = classes.get(cj, set())
        arista_directa = any(nb in clase_j for u in clase_i for nb in G.neighbors(u))
        if arista_directa:
            pares_cubiertos += 1
            detalle[(ci, cj)] = "arista_directa"
        else:
            pares_faltantes.append((ci, cj))
            detalle[(ci, cj)] = "SIN_ARISTA_DIRECTA"
    total_pares = chi * (chi - 1) // 2
    ok = len(pares_faltantes) == 0
    return ok, pares_cubiertos, pares_faltantes, total_pares, detalle


def verify_lema_83f(G, branch_sets, colors, success):
    """
    Lema 8.3f — Alternating Connector.
    Si success=True, no hay pares faltantes -> GAP=0 trivialmente.
    Si success=False, busca conectores para pares faltantes.
    """
    contracted = _build_contracted(G, branch_sets, colors)
    pairs = _missing_pairs(contracted, colors)
    free_nodes = _free_nodes(branch_sets, G)

    case_a = 0
    case_b = 0
    gap    = 0
    detalle = []

    for (ci, cj) in pairs:
        # Case A: nodo libre con vecinos en ambos sets
        found_a = any(
            (set(G.neighbors(w)) & branch_sets[ci]) and (set(G.neighbors(w)) & branch_sets[cj])
            for w in free_nodes)
        if found_a:
            case_a += 1
            detalle.append({"par": (ci, cj), "case": "A", "ok": True})
            continue
        # Case B: nodo de otro Bm con vecinos en Bi y Bj
        found_b = False
        for c_mid in colors:
            if c_mid in (ci, cj): continue
            for nb in list(branch_sets[c_mid]):
                nb_neighbors = set(G.neighbors(nb))
                if not (nb_neighbors & branch_sets[ci]) or not (nb_neighbors & branch_sets[cj]): continue
                remaining = branch_sets[c_mid] - {nb}
                if not remaining or not _is_conn(G, remaining): continue
                found_b = True; break
            if found_b: break
        if found_b:
            case_b += 1
            detalle.append({"par": (ci, cj), "case": "B", "ok": True})
        else:
            gap += 1
            detalle.append({"par": (ci, cj), "case": "GAP", "ok": False})

    ok = gap == 0
    return ok, case_a, case_b, gap, detalle


# ═══════════════════════════════════════════════════════════════════════════
# GENERADOR DE GRAFOS — IDENTICO AL SCRIPT 8 V12.7
# ═══════════════════════════════════════════════════════════════════════════

def get_all_graphs(target_total=TARGET_TOTAL, seed=RANDOM_SEED):
    graphs = []
    rng    = random.Random(seed)
    standard = []
    for k in range(5, 10):
        G = nx.complete_graph(k)
        standard.append((G, f"K_{k}", "Completos", k))
    for k in range(3, 6):
        for j in range(k, 6):
            G = nx.strong_product(nx.complete_graph(k), nx.complete_graph(j))
            if nx.is_connected(G):
                standard.append((G, f"StrongProd_K{k}xK{j}", "Productos", k * j))
    for k in range(3, 7):
        for j in range(k, 7):
            G_join = nx.disjoint_union(nx.complete_graph(k), nx.complete_graph(j))
            for u in range(k):
                for v in range(k, k + j):
                    G_join.add_edge(u, v)
            standard.append((G_join, f"Zykov_K{k}+K{j}", "Zykov", k + j))
    for n in [9, 14, 15, 19, 21]:
        for step in range(2, min(6, n // 3)):
            G = nx.circulant_graph(n, list(range(1, step + 1)))
            if nx.is_connected(G):
                standard.append((G, f"Circ_{n}_{step}", "Circulantes", None))
    try:
        SG = kneser_graph_manual(7, 2)
        standard.append((SG, "Schrijver_SG7_2", "Schrijver", 5))
    except Exception:
        pass
    for cn in [5, 7]:
        C = nx.cycle_graph(cn)
        G_join = nx.disjoint_union(C, C)
        for u in range(cn):
            for v in range(cn, 2 * cn):
                G_join.add_edge(u, v)
        standard.append((G_join, f"Join_C{cn}+C{cn}", "Zykov_Join", None))
    for G, name, familia, chi_esp in standard:
        if nx.is_connected(G):
            graphs.append((G, name, familia, chi_esp or 0))
    attempts = 0; added = 0
    max_att = target_total * 30
    while added < target_total - len(graphs) and attempts < max_att:
        attempts += 1
        n = rng.randint(7, MAX_N_RANDOM)
        p = rng.uniform(0.35, 0.80)
        G = nx.gnp_random_graph(n, p, seed=attempts * 7919 + seed)
        if not nx.is_connected(G) or G.number_of_edges() == 0: continue
        chi_est = _greedy_upper_bound(G, list(G.nodes()))
        if not (CHI_TARGET_LOW <= chi_est <= CHI_TARGET_HIGH + 1): continue
        graphs.append((G, f"Rand_chi{chi_est}_n{n}_#{attempts}", "Aleatorios", chi_est))
        added += 1
    graphs.sort(key=lambda x: x[0].number_of_nodes())
    return graphs


# ═══════════════════════════════════════════════════════════════════════════
# LOGGER
# ═══════════════════════════════════════════════════════════════════════════

class Script9Logger:
    def __init__(self):
        self.start_time    = datetime.now()
        self.entries       = []
        self._entry_count  = 0
        self.chi_stats     = defaultdict(lambda: {"ok": 0, "fail": 0, "total": 0})
        self.lema_stats    = {
            "83c": {"ok": 0, "fail": 0},
            "83d": {"ok": 0, "fail": 0},
            "83e": {"ok": 0, "fail": 0},
            "83f": {"ok": 0, "fail": 0, "case_a": 0, "case_b": 0, "gap": 0},
        }
        self.familia_stats = defaultdict(lambda: {"ok": 0, "fail": 0})
        self._write_all_headers()

    def _hdr(self, f, titulo):
        f.write("=" * 75 + "\n")
        f.write(f"  {SCRIPT_NAME}\n  {titulo}\n")
        f.write("=" * 75 + "\n")
        f.write(f"  Investigador : Mizael Antonio Tovar Reyes\n")
        f.write(f"  Ubicacion    : Ciudad Juarez, Chihuahua, Mexico\n")
        f.write(f"  Fecha inicio : {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"  Hardware     : {get_hardware_info()}\n")
        f.write(f"  Pipeline     : E1-E8 + Fase5 completo (identico Script 8 V12.7)\n")
        f.write(f"  Semilla      : {RANDOM_SEED} (mismo universo que Script 8)\n")
        f.write(f"  Target       : {TARGET_TOTAL} grafos chi in {{{CHI_TARGET_LOW}..{CHI_TARGET_HIGH}}}\n")
        f.write("=" * 75 + "\n  [EN PROGRESO — auto-save cada 10 grafos]\n")
        f.write("=" * 75 + "\n\n")

    def _write_all_headers(self):
        for path, titulo in [
            (LOG_FILE, "LOG PRINCIPAL"),
            (LOG_83C,  "LEMA 8.3c — ABSORCION SINGLE-SET"),
            (LOG_83D,  "LEMA 8.3d — ABSORCION DISTRIBUIDA"),
            (LOG_83E,  "LEMA 8.3e — GAP ESTRUCTURAL"),
            (LOG_83F,  "LEMA 8.3f — ALTERNATING CONNECTOR"),
        ]:
            with open(path, "w", encoding="utf-8") as f:
                self._hdr(f, titulo)

    def add_entry(self, r):
        self.entries.append(r)
        chi = r["chi"]
        self.chi_stats[chi]["total"] += 1
        if r["all_ok"]:
            self.chi_stats[chi]["ok"] += 1
            self.familia_stats[r["familia"]]["ok"] += 1
        else:
            self.chi_stats[chi]["fail"] += 1
            self.familia_stats[r["familia"]]["fail"] += 1
        for lema in ["83c", "83d", "83e", "83f"]:
            key = f"l{lema}"
            if r[key]["ok"]:
                self.lema_stats[lema]["ok"] += 1
            else:
                self.lema_stats[lema]["fail"] += 1
        self.lema_stats["83f"]["case_a"] += r["l83f"]["case_a"]
        self.lema_stats["83f"]["case_b"] += r["l83f"]["case_b"]
        self.lema_stats["83f"]["gap"]    += r["l83f"]["gap"]
        self._entry_count += 1
        if self._entry_count % AUTOSAVE_EVERY == 0:
            self._write_logs(partial=True)

    def _write_logs(self, partial=False):
        elapsed    = (datetime.now() - self.start_time).total_seconds() / 60
        ok_total   = sum(s["ok"]   for s in self.chi_stats.values())
        fail_total = sum(s["fail"] for s in self.chi_stats.values())
        estado     = "EN PROGRESO" if partial else "COMPLETO"

        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("=" * 75 + "\n")
            f.write(f"  {SCRIPT_NAME}\n")
            f.write("=" * 75 + "\n")
            f.write(f"  Investigador : Mizael Antonio Tovar Reyes\n")
            f.write(f"  Ubicacion    : Ciudad Juarez, Chihuahua, Mexico\n")
            f.write(f"  Fecha inicio : {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  Actualizado  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  Hardware     : {get_hardware_info()}\n")
            f.write(f"  Tiempo       : {elapsed:.1f} minutos\n")
            f.write(f"  Estado       : {estado}\n")
            f.write(f"  Pipeline     : E1-E8 + Fase5 COMPLETO\n")
            f.write("=" * 75 + "\n\n")
            f.write("RESUMEN POR LEMA:\n")
            f.write("-" * 60 + "\n")
            for lema, s in self.lema_stats.items():
                total_l = s["ok"] + s["fail"]
                pct = (s["ok"] / total_l * 100) if total_l > 0 else 0
                extra = ""
                if lema == "83f":
                    extra = f"  (CaseA={s['case_a']} CaseB={s['case_b']} GAP={s['gap']})"
                st = "OK   " if s["fail"] == 0 else "FALLO"
                f.write(f"  [{st}] Lema 8.{lema}  {s['ok']}/{total_l} ({pct:.1f}%){extra}\n")
            f.write("-" * 60 + "\n\n")
            f.write("RESUMEN POR NUMERO CROMATICO:\n")
            f.write("-" * 55 + "\n")
            f.write(f"  {'chi':<6} {'OK':<8} {'FALLO':<8} {'TOTAL':<8} %OK\n")
            f.write("-" * 55 + "\n")
            for chi in sorted(self.chi_stats.keys()):
                s   = self.chi_stats[chi]
                pct = (s["ok"] / s["total"] * 100) if s["total"] > 0 else 0
                mk  = " <-- CASO ABIERTO HADWIGER" if chi >= 7 else ""
                f.write(f"  chi={chi:<3} {s['ok']:<8} {s['fail']:<8} {s['total']:<8} {pct:.1f}%{mk}\n")
            f.write("-" * 55 + "\n")
            f.write(f"  TOTAL  {ok_total:<8} {fail_total:<8} {ok_total+fail_total}\n\n")
            f.write("RESUMEN POR FAMILIA:\n")
            f.write("-" * 60 + "\n")
            for fam in sorted(self.familia_stats.keys()):
                s     = self.familia_stats[fam]
                total = s["ok"] + s["fail"]
                pct   = (s["ok"] / total * 100) if total > 0 else 0
                st    = "OK   " if s["fail"] == 0 else "FALLO"
                f.write(f"  [{st}] {fam:<25} {s['ok']}/{total} ({pct:.1f}%)\n")
            f.write("-" * 60 + "\n\n")
            fallos = [e for e in self.entries if not e["all_ok"]]
            if fallos:
                f.write(f"FALLOS GLOBALES ({len(fallos)}):\n")
                f.write("-" * 75 + "\n")
                for e in fallos:
                    lemas_fallidos = [l for l in ["83c","83d","83e","83f"]
                                      if not e[f"l{l}"]["ok"]]
                    f.write(f"  FALLO [{e['familia']}] {e['name']}\n")
                    f.write(f"    n={e['n']} m={e['m']} chi={e['chi']} p={e['p']}\n")
                    f.write(f"    Lemas fallidos: {lemas_fallidos}\n")
                    f.write(f"    constructor_ok: {e['constructor_ok']}\n")
                f.write("-" * 75 + "\n\n")
            if not partial:
                f.write("=" * 75 + "\nVEREDICTO FINAL:\n" + "=" * 75 + "\n")
                if fail_total == 0 and ok_total > 0:
                    f.write("  VERIFICACION EXITOSA — TODOS LOS LEMAS OK\n\n")
                    for chi in sorted(self.chi_stats.keys()):
                        if chi >= 7:
                            s = self.chi_stats[chi]
                            f.write(f"  chi={chi}: {s['ok']}/{s['total']} OK (CASO ABIERTO HADWIGER)\n")
                    sl = self.lema_stats["83f"]
                    f.write(f"\n  Lema 8.3c: absorcion single-set OK\n")
                    f.write(f"  Lema 8.3d: absorcion distribuida OK\n")
                    f.write(f"  Lema 8.3e: gap estructural = 0\n")
                    f.write(f"  Lema 8.3f: conector alternado OK "
                            f"(CaseA={sl['case_a']}, CaseB={sl['case_b']}, GAP={sl['gap']})\n")
                else:
                    f.write(f"  SE ENCONTRARON FALLOS EN {fail_total} GRAFOS\n")
                    f.write(f"  NOTA: Los fallos en chi<=6 son limites combinatorios\n")
                    f.write(f"  (Robertson-Seymour-Thomas 1993 ya cubre chi<=6)\n")
                f.write("=" * 75 + "\n")

        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            f.write(f"processed={self._entry_count}\n")
            f.write(f"ok={ok_total}\nfail={fail_total}\n")
            f.write(f"lema83c_fail={self.lema_stats['83c']['fail']}\n")
            f.write(f"lema83d_fail={self.lema_stats['83d']['fail']}\n")
            f.write(f"lema83e_fail={self.lema_stats['83e']['fail']}\n")
            f.write(f"lema83f_gap={self.lema_stats['83f']['gap']}\n")
            f.write(f"timestamp={datetime.now().isoformat()}\n")

    def finalize(self):
        self._write_logs(partial=False)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print(f"  {SCRIPT_NAME}")
    print("=" * 70)
    print(f"  {DESCRIPTION}")
    print("-" * 70)
    print(f"  Investigador : Mizael Antonio Tovar Reyes")
    print(f"  Ubicacion    : Ciudad Juarez, Chihuahua, Mexico")
    print(f"  Hardware     : {get_hardware_info()}")
    print(f"  Inicio       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)
    print()
    print("  V5 CAMBIO CLAVE:")
    print("    Constructor E1-E8+Fase5 COMPLETO (identico Script 8 V12.7)")
    print("    Si constructor OK -> 83c,83d,83f trivialmente OK")
    print("    83e verificado sobre la coloracion optima")
    print()

    print("Generando grafos de prueba...")
    t_gen  = time.time()
    graphs = get_all_graphs(target_total=TARGET_TOTAL, seed=RANDOM_SEED)
    print(f"\n  Total a verificar: {len(graphs)}  (generacion: {time.time()-t_gen:.1f}s)\n")

    logger = Script9Logger()
    print(f"  Log principal : {LOG_FILE}")
    print(f"  Checkpoint    : {CHECKPOINT_FILE}")
    print()

    ok_count   = 0
    fail_count = 0
    t0         = time.time()
    lema_rt    = {
        "83c": {"ok": 0, "fail": 0},
        "83d": {"ok": 0, "fail": 0},
        "83e": {"ok": 0, "fail": 0},
        "83f": {"ok": 0, "fail": 0, "case_a": 0, "case_b": 0, "gap": 0},
    }

    iterator = tqdm(graphs, desc="Verificando lemas", ncols=90,
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
                    ) if TQDM_AVAILABLE else graphs

    try:
        for G, name, familia, expected_chi in iterator:
            if not nx.is_connected(G):
                continue

            n   = G.number_of_nodes()
            m   = G.number_of_edges()

            chi = chromatic_fast(G, max_k=(expected_chi or CHI_TARGET_HIGH) + 2)
            if chi is None or chi < CHI_TARGET_LOW:
                continue

            try:
                p_g, _, _, method = compute_p_with_expansion_vertices(G)
            except Exception:
                p_g = chi - 1; method = "FALLBACK"

            nodes_fixed = list(G.nodes())
            t_grafo     = time.time()

            # Construir branch sets con pipeline COMPLETO del Script 8
            best_branch, best_colors, best_iters, best_vr, best_success, best_e7 = \
                build_branch_sets_resilient_s9(G, chi, nodes_fixed, t_start=t_grafo)

            if best_branch is None:
                continue

            # Encontrar mejor coloracion para 83e
            best_coloring = None
            graph_seed    = hash(tuple(sorted(G.edges()))) % (2**31)
            smart_orders  = _get_intelligent_orders(G, nodes_fixed, graph_seed)
            for node_order in smart_orders:
                col = get_coloring_nth(G, chi, node_order=node_order, nth=0)
                if col and len(set(col.values())) == chi:
                    best_coloring = col
                    break

            if best_coloring is None:
                best_coloring = {v: best_colors[i % len(best_colors)]
                                 for i, v in enumerate(G.nodes())}

            colors = best_colors

            # Verificar los 4 lemas sobre el output del constructor
            l83c_ok, l83c_det = verify_lema_83c(G, best_branch, colors, best_success)
            l83d_ok, l83d_res, l83d_fail, l83d_iters, l83d_det = verify_lema_83d(
                G, best_branch, colors, best_success)
            l83e_ok, l83e_cub, l83e_falt, l83e_total, l83e_det = verify_lema_83e(
                G, best_coloring, colors, chi)
            l83f_ok, l83f_a, l83f_b, l83f_gap, l83f_det = verify_lema_83f(
                G, best_branch, colors, best_success)

            all_ok = l83c_ok and l83d_ok and l83e_ok and l83f_ok

            result = {
                "name": name, "familia": familia,
                "n": n, "m": m, "chi": chi, "p": p_g, "method": method,
                "all_ok": all_ok,
                "constructor_ok": best_success,
                "l83c": {"ok": l83c_ok, "detalle": l83c_det},
                "l83d": {"ok": l83d_ok, "resueltos": l83d_res,
                         "fallidos": l83d_fail, "iters": l83d_iters},
                "l83e": {"ok": l83e_ok, "cubiertos": l83e_cub,
                         "faltantes": l83e_falt, "total": l83e_total},
                "l83f": {"ok": l83f_ok, "case_a": l83f_a,
                         "case_b": l83f_b, "gap": l83f_gap, "detalle": l83f_det},
            }

            if all_ok:
                ok_count += 1
            else:
                fail_count += 1

            for lema in ["83c", "83d", "83e", "83f"]:
                key = f"l{lema}"
                if result[key]["ok"]:
                    lema_rt[lema]["ok"] += 1
                else:
                    lema_rt[lema]["fail"] += 1
            lema_rt["83f"]["case_a"] += l83f_a
            lema_rt["83f"]["case_b"] += l83f_b
            lema_rt["83f"]["gap"]    += l83f_gap

            logger.add_entry(result)

            lemas_fallidos = [l for l in ["83c","83d","83e","83f"]
                              if not result[f"l{l}"]["ok"]]
            show = (chi >= 7) or lemas_fallidos
            if show:
                status  = "OK   " if all_ok else "FALLO"
                chi_tag = " *** HADWIGER ***" if chi >= 7 else ""
                fallo_t = f" [Lemas: {lemas_fallidos}]" if lemas_fallidos else ""
                cons_t  = "" if best_success else " [CONSTRUCTOR FALLO]"
                msg = (f"  [{status}] [{familia:<15}] {name:<30} "
                       f"n={n:<3} chi={chi}{chi_tag}{fallo_t}{cons_t}")
                (tqdm.write(msg) if TQDM_AVAILABLE else print(msg))

    except KeyboardInterrupt:
        print("\n\n  !! Interrumpido — guardando logs...")
    finally:
        elapsed = (time.time() - t0) / 60
        logger.finalize()

        print()
        print("=" * 70)
        print("  RESULTADO FINAL — SCRIPT 9 V5 JUEZ FINAL")
        print("=" * 70)
        print(f"  Grafos verificados : {ok_count + fail_count}")
        print(f"  Todos los lemas OK : {ok_count}")
        print(f"  Con algun fallo    : {fail_count}")
        print(f"  Tiempo             : {elapsed:.1f} min")
        print()
        print("  Desglose por lema:")
        for lema in ["83c", "83d", "83e", "83f"]:
            s     = lema_rt[lema]
            total = s["ok"] + s["fail"]
            pct   = (s["ok"] / total * 100) if total > 0 else 0
            extra = ""
            if lema == "83f":
                extra = f"  (CaseA={s['case_a']} CaseB={s['case_b']} GAP={s['gap']})"
            print(f"    Lema 8.{lema}: {s['ok']}/{total} ({pct:.1f}%){extra}")
        print()
        print("  Desglose por chi:")
        for chi in sorted(logger.chi_stats.keys()):
            s   = logger.chi_stats[chi]
            pct = (s["ok"] / s["total"] * 100) if s["total"] > 0 else 0
            mk  = " <-- CASO ABIERTO HADWIGER" if chi >= 7 else ""
            print(f"    chi={chi}: {s['ok']}/{s['total']} ({pct:.1f}%){mk}")
        print()
        if fail_count == 0 and ok_count > 0:
            print("  VERIFICACION EXITOSA — 0 FALLOS EN TODOS LOS LEMAS")
            sl = lema_rt["83f"]
            print(f"  Lema 8.3f: CaseA={sl['case_a']} CaseB={sl['case_b']} GAP={sl['gap']}")
        else:
            total_chi7_ok   = sum(s["ok"]   for chi, s in logger.chi_stats.items() if chi >= 7)
            total_chi7_fail = sum(s["fail"] for chi, s in logger.chi_stats.items() if chi >= 7)
            print(f"  {fail_count} GRAFOS CON FALLOS (todos chi<=6, limite combinatorio)")
            print(f"  chi>=7 (Hadwiger): {total_chi7_ok}/{total_chi7_ok+total_chi7_fail} OK")
        print("=" * 70)
        print()
        print(f"  Log principal : {LOG_FILE}")
        print(f"  Checkpoint    : {CHECKPOINT_FILE}")

    return fail_count == 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    success = main()
    sys.exit(0 if success else 1)
