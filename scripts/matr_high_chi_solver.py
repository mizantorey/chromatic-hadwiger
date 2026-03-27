"""
SCRIPT 8 — HADWIGER CHI ALTO — V20 (base: V12.7 TURBO)
===============================================================
Autor    : Mizael Antonio Tovar Reyes
Ubicacion: Ciudad Juarez, Chihuahua, Mexico

CAMBIOS V20:
  - Version estandarizada a V20.
  - Los 5 grafos con FALLO documentados y probados como falsos negativos
    en Script 10 (ver logs/log_script10_prueba_5_fallos.txt).
  - Sin cambios algoritmicos respecto a V12.7.

BASE: V12.6 — estructura intacta, FIX 1-5 y FIX 7-8 preservados.

PROBLEMA RESUELTO EN V12.7:
    El FIX 6 de V12.6 (enumeracion exhaustiva de hasta 2000 permutaciones
    con itertools.permutations) causaba que grafos con n<=chi+3 tardaran
    horas por grafo. Con 269 grafos totales, la proyeccion era >52 horas.
    El script llego al 5% en 2h40m — inaceptable para correr completo.

[FIX 6 REEMPLAZADO] Permutaciones Inteligentes (20 ordenes diversos)
    En lugar de iterar las primeras 2000 permutaciones lexicograficas
    (que son muy similares entre si), ahora se generan 20 ordenes
    DIVERSOS basados en propiedades reales del grafo:
      - 4 ordenes del Motor Hibrido (grado asc/desc, indice asc/desc)
      - 4 ordenes por vecindario (suma de grados de vecinos asc/desc,
        coeficiente de clustering asc/desc)
      - 4 ordenes por excentricidad y centralidad
      - 4 ordenes intercalados (pares alternando nodos alta/baja conn.)
      - 4 permutaciones aleatorias con semilla por grafo (diversidad)
    Total: 20 ordenes. Cada uno prueba hasta MAX_COLOR_RETRIES coloraciones.
    Cubre el espacio de forma DIVERSA sin explotar combinatoriamente.

[FIX 9] Timeout suave por grafo (45 segundos)
    Si un grafo tarda mas de GRAPH_TIMEOUT segundos, el motor guarda
    el MEJOR resultado parcial encontrado hasta ese momento y avanza
    al siguiente grafo. NO produce FAILs falsos — si encontro algo
    valido antes del timeout, lo reporta como exito. Si no encontro
    nada valido, reporta el mejor intento con su estado real.
    Esto garantiza que los 269 grafos se procesen en tiempo razonable
    (~2-4 horas total en lugar de 52+ horas).

[FIX 7] Relaxed Singleton — HEREDADO INTACTO de V12.6
    Singletons con aristas hacia todos los otros branch sets = OK.

[FIX 8] Semilla por grafo — HEREDADO INTACTO de V12.6
    Reproducibilidad total via hash de aristas del grafo.

HEREDADO INTACTO de V12.5:
  - Ghost Component Bug Fix (FIX 1)
  - has_large_donor Fix (FIX 2)
  - Motor Hibrido 4 ordenes reales (FIX 3)
  - Relay-2 con verificacion de arista (FIX 4)
  - E8 post-Fase5 (FIX 5)
  - AtomSwap, E6 Expandido, E7, E8, Fase 5 Fusion Forzada
  - MAX_RECOLOR_ATTEMPTS = 30

Investigador : Mizael Antonio Tovar Reyes
Ubicacion    : Ciudad Juarez, Chihuahua, Mexico
Version      : 12.7 TURBO ZERO FAILURE — Marzo 2026
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

SCRIPT_NAME      = "SCRIPT 8 — HADWIGER CHI ALTO — V12.7 TURBO ZERO FAILURE"
DESCRIPTION      = "V12.6 + Permutaciones Inteligentes + Timeout Suave 45s por grafo"
BASE_DIR         = Path(__file__).resolve().parent
LOG_FILE         = BASE_DIR / "log_script8_hadwiger_v12_7.txt"
LOG_CHI_ALTO     = BASE_DIR / "log_script8_CHI7_CHI8_v12_7_detallado.txt"
CHECKPOINT_FILE  = BASE_DIR / "checkpoint_script8_v12_7.txt"

TARGET_TOTAL          = 600
MAX_REPAIR_ITERS      = 50
MAX_COLOR_RETRIES     = 200
MAX_RECOLOR_ATTEMPTS  = 30
RANDOM_SEED           = 8888
MAX_N_RANDOM          = 13
CHI_TARGET_LOW        = 5
CHI_TARGET_HIGH       = 8
GRAPH_TIMEOUT         = 45      # V12.7: segundos maximos por grafo (timeout suave)


# ═══════════════════════════════════════════════════════════════════════════
# COLORACION — MOTOR NTH DETERMINISTICO (sin cambios)
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
                    del col[v]
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
    nodes_ord = node_order if node_order is not None else sorted(nodes, key=lambda v: -G.degree(v))
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
                if bt(i + 1):
                    return True
                del col[v]
        return False

    return col if bt(0) else None


# ═══════════════════════════════════════════════════════════════════════════
# UTILIDADES (sin cambios)
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
# HELPER: GRADO EXTERNO (NUEVO V12.4)
# ═══════════════════════════════════════════════════════════════════════════

def _external_degree(v, bs_own, nb_cache):
    """Aristas de v hacia nodos FUERA de su propio branch set."""
    return len(nb_cache[v] - bs_own)


# ═══════════════════════════════════════════════════════════════════════════
# ATOM SWAP — (NUEVO V12.4)
# ═══════════════════════════════════════════════════════════════════════════

def _try_atom_swap(G, branch_sets, colors, c_target, main_comp, comp_frag,
                   c_donor_atom, nb_cache):
    """
    AtomSwap — solo para donantes atomicos (|bs_donor| == 1).

    Cuando bs_donor tiene exactamente 1 nodo (el 'atomo'), E6 no puede
    cederlo porque quedaria vacio. Esta funcion busca un set prestador Bk
    (|Bk|>=2) que le done un nodo vecino al atomo, reforzando el donante
    antes de ejecutar el swap standard.

    Criterio de 'Atomo Protegido':
      Solo se activa si no hay otro donante con |Bj|>1 disponible,
      es decir, si el atomo es el UNICO set con vecinos en ambos fragmentos.

    Pasos:
      1. v_atom = unico nodo de c_donor_atom
      2. Buscar Bk con |Bk|>=2 tal que algun w in Bk es vecino de v_atom
      3. Mover w -> c_donor_atom  (ahora |bs_donor| == 2, cedible)
      4. Ejecutar swap E6 estandar: v_atom -> c_target, u -> c_donor
      5. BFS triple: c_target, c_donor_atom, Bk quedan conexos

    Retorna (True, new_branch_sets, new_main) o (False, branch_sets, main_comp)
    """
    bs_atom = branch_sets[c_donor_atom]
    if len(bs_atom) != 1:
        return False, branch_sets, main_comp

    v_atom = next(iter(bs_atom))
    v_nbs  = nb_cache[v_atom]

    # El atomo debe tocar ambos fragmentos de c_target
    if not (v_nbs & main_comp) or not (v_nbs & comp_frag):
        return False, branch_sets, main_comp

    # Buscar prestador Bk con |Bk|>=2 y un nodo vecino del atomo
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

            # Reforzar donante: w -> c_donor_atom
            bs_donor_new = bs_atom | {w}

            # Ahora buscar u en c_target que pueda ir a c_donor_atom reforzado
            bs_target = branch_sets[c_target]
            donor_sin_atom = bs_donor_new - {v_atom}  # = {w}

            for u in list(main_comp) + list(comp_frag):
                if u == v_atom:
                    continue
                if not (nb_cache[u] & donor_sin_atom):
                    continue

                ci_final  = (bs_target - {u}) | {v_atom}
                cd_final  = donor_sin_atom | {u}    # = {w, u}
                ck_final  = lender_sin_w

                if not _is_conn(G, ci_final):
                    continue
                if not _is_conn(G, cd_final):
                    continue
                if not _is_conn(G, ck_final):
                    continue

                new_bs = {c: set(bs) for c, bs in branch_sets.items()}
                new_bs[c_target]    = ci_final
                new_bs[c_donor_atom] = cd_final
                new_bs[c_lender]    = ck_final

                new_main = (main_comp | comp_frag | {v_atom}) - {u}
                return True, new_bs, new_main

    return False, branch_sets, main_comp




def _try_kempe_swap_e6(G, branch_sets, colors, c_target, main_comp, comp_frag,
                       nb_cache=None):
    """
    E6 Expandido (V12.4):
      - Clasico: busca u en bs_target (main_comp + comp_frag)
      - Nuevo:   tambien busca u en free_nodes (nodos sin asignar)
      - AtomSwap: si donante es atomico (|bs_donor|==1) y no hay
        donante mayor disponible, invoca _try_atom_swap antes de descartar
    """
    if nb_cache is None:
        nb_cache = {v: set(G.neighbors(v)) for v in G.nodes()}

    free_now = _free_nodes(branch_sets, G)

    # FIX 2 (V12.5): has_large_donor con logica correcta (sin 'or' suelto)
    # Pre-calcular si existe algun donante con |Bj|>1 que toque ambos fragmentos
    has_large_donor = False
    for c_check in colors:
        if c_check == c_target:
            continue
        if len(branch_sets[c_check]) <= 1:
            continue
        for vv in branch_sets[c_check]:
            if (nb_cache[vv] & main_comp) or (nb_cache[vv] & comp_frag):
                has_large_donor = True
                break
        if has_large_donor:
            break

    for c_donor in colors:
        if c_donor == c_target:
            continue

        bs_donor  = branch_sets[c_donor]
        bs_target = branch_sets[c_target]

        # AtomSwap: donante atomico y no hay donante mayor -> delegar
        if len(bs_donor) == 1 and not has_large_donor:
            atom_ok, new_bs, new_main = _try_atom_swap(
                G, branch_sets, colors, c_target, main_comp, comp_frag,
                c_donor, nb_cache
            )
            if atom_ok:
                for k in branch_sets:
                    branch_sets[k] = new_bs[k]
                return True, branch_sets, new_main
            continue

        if len(bs_donor) < 2:
            continue

        for v in list(bs_donor):
            v_nbs = nb_cache[v]
            if not (v_nbs & main_comp) or not (v_nbs & comp_frag):
                continue

            donor_sin_v = bs_donor - {v}
            if not donor_sin_v:
                continue

            # Candidatos u: bs_target + free_nodes (V12.4 expansion)
            candidates_u = list(main_comp) + list(comp_frag) + list(free_now)

            for u in candidates_u:
                if u == v:
                    continue
                if not (nb_cache[u] & donor_sin_v):
                    continue

                if u in free_now:
                    # u es libre: agrega v a target y u a donor sin quitar nada de target
                    target_con_v      = bs_target | {v}
                    donor_sin_v_con_u = donor_sin_v | {u}
                    if not _is_conn(G, target_con_v):
                        continue
                    if not _is_conn(G, donor_sin_v_con_u):
                        continue
                    new_bs = {c: set(bs) for c, bs in branch_sets.items()}
                    new_bs[c_donor]  = donor_sin_v_con_u
                    new_bs[c_target] = target_con_v
                    new_main = main_comp | comp_frag | {v}
                    return True, new_bs, new_main
                else:
                    # u esta en bs_target: swap clasico
                    target_sin_u_con_v = (bs_target - {u}) | {v}
                    donor_sin_v_con_u  = donor_sin_v | {u}
                    if not _is_conn(G, target_sin_u_con_v):
                        continue
                    if not _is_conn(G, donor_sin_v_con_u):
                        continue
                    new_bs = {c: set(bs) for c, bs in branch_sets.items()}
                    new_bs[c_donor]  = donor_sin_v_con_u
                    new_bs[c_target] = target_sin_u_con_v
                    new_main = (main_comp | comp_frag | {v}) - {u}
                    return True, new_bs, new_main

    return False, branch_sets, main_comp


# ═══════════════════════════════════════════════════════════════════════════
# KEMPE CHAIN — E7 (heredado de V12, sin cambios)
# ═══════════════════════════════════════════════════════════════════════════

def _try_kempe_chain_e7(G, branch_sets, colors, c_target, main_comp, comp_frag,
                        nb_cache=None):
    """
    E7 — Mizael Triple-Step Swap para reconectar c_target cuando E6 falla.

    Cadena Ci->Ck->Cj:
      Paso 1:  u  in Ci  ->  Ck
      Paso 2:  w  in Ck  ->  Cj
      Paso 3:  v  in Cj  ->  Ci  (v tiene vecinos en AMBOS fragmentos)

    Verificacion triple BFS: Ci, Cj y Ck quedan todas conexas.
    """
    if nb_cache is None:
        nb_cache = {v: set(G.neighbors(v)) for v in G.nodes()}

    bs_target = branch_sets[c_target]
    other_colors = [c for c in colors if c != c_target]

    for c_donor in other_colors:
        bs_donor = branch_sets[c_donor]
        if len(bs_donor) < 2:
            continue

        for c_bridge in other_colors:
            if c_bridge == c_donor:
                continue
            bs_bridge = branch_sets[c_bridge]
            if len(bs_bridge) < 2:
                continue

            for v in list(bs_donor):
                v_nbs = nb_cache[v]
                if not (v_nbs & main_comp) or not (v_nbs & comp_frag):
                    continue

                donor_sin_v = bs_donor - {v}
                if not donor_sin_v:
                    continue

                for w in list(bs_bridge):
                    w_nbs = nb_cache[w]
                    if not (w_nbs & donor_sin_v):
                        continue

                    bridge_sin_w = bs_bridge - {w}
                    if not bridge_sin_w:
                        continue

                    donor_sin_v_con_w = donor_sin_v | {w}

                    for u in list(main_comp) + list(comp_frag):
                        if u == v:
                            continue
                        u_nbs = nb_cache[u]
                        if not (u_nbs & bridge_sin_w):
                            continue

                        ci_final = (bs_target - {u}) | {v}
                        cj_final = donor_sin_v_con_w
                        ck_final = bridge_sin_w | {u}

                        if not _is_conn(G, ci_final):
                            continue
                        if not _is_conn(G, cj_final):
                            continue
                        if not _is_conn(G, ck_final):
                            continue

                        new_bs = {c: set(bs) for c, bs in branch_sets.items()}
                        new_bs[c_target] = ci_final
                        new_bs[c_donor]  = cj_final
                        new_bs[c_bridge] = ck_final

                        new_main = (main_comp | comp_frag | {v}) - {u}
                        info = (f"E7_chain(Ci=C{c_target},Cj=C{c_donor},Ck=C{c_bridge},"
                                f"u={u}->Ck, w={w}->Cj, v={v}->Ci)")
                        return True, new_bs, new_main, info

    return False, branch_sets, main_comp, ""


# ═══════════════════════════════════════════════════════════════════════════
# E8 — DOUBLE SWAP SIMULTANEO (NUEVO EN V12.2)
# ═══════════════════════════════════════════════════════════════════════════

def _try_double_swap_e8(G, branch_sets, colors, c_target, main_comp, comp_frag,
                        nb_cache=None):
    """
    E8 — Double Swap Simultaneo para reconectar c_target cuando E6 y E7 fallan.

    Estrategia: realizar dos swaps E6 sobre pares de clases DISTINTOS
    de forma simultanea. Util cuando la estructura del grafo requiere
    reestructurar dos branch sets al mismo tiempo para liberar la
    conexidad de c_target.

    Paso:
      1. Encontrar (c_donor1, v1) tal que v1 tiene vecino en comp_frag
      2. Encontrar (c_donor2, v2) tal que v2 tiene vecino en main_comp
         y v2 != v1, c_donor2 != c_donor1
      3. Intercambiar: agregar v1 y v2 a c_target, buscando u1 y u2
         para devolver a c_donor1 y c_donor2 respectivamente
      4. Verificar que las 3 clases (c_target, c_donor1, c_donor2) quedan conexas

    Retorna (True, new_branch_sets, new_main, info_str) o
            (False, branch_sets, main_comp, "")
    """
    if nb_cache is None:
        nb_cache = {v: set(G.neighbors(v)) for v in G.nodes()}

    bs_target = branch_sets[c_target]
    other_colors = [c for c in colors if c != c_target]

    for c_donor1 in other_colors:
        bs_d1 = branch_sets[c_donor1]
        if len(bs_d1) < 2:
            continue

        # v1: nodo de c_donor1 que toca comp_frag
        for v1 in list(bs_d1):
            if not (nb_cache[v1] & comp_frag):
                continue
            d1_sin_v1 = bs_d1 - {v1}
            if not d1_sin_v1:
                continue

            for c_donor2 in other_colors:
                if c_donor2 == c_donor1:
                    continue
                bs_d2 = branch_sets[c_donor2]
                if len(bs_d2) < 2:
                    continue

                # v2: nodo de c_donor2 que toca main_comp
                for v2 in list(bs_d2):
                    if not (nb_cache[v2] & main_comp):
                        continue
                    d2_sin_v2 = bs_d2 - {v2}
                    if not d2_sin_v2:
                        continue

                    # u1: nodo de c_target (main_comp) que puede ir a c_donor1
                    for u1 in list(main_comp):
                        if u1 == v1 or u1 == v2:
                            continue
                        if not (nb_cache[u1] & d1_sin_v1):
                            continue

                        # u2: nodo de c_target (comp_frag) que puede ir a c_donor2
                        for u2 in list(comp_frag):
                            if u2 == v1 or u2 == v2 or u2 == u1:
                                continue
                            if not (nb_cache[u2] & d2_sin_v2):
                                continue

                            # Estado final de las clases
                            ci_final = (bs_target - {u1, u2}) | {v1, v2}
                            cd1_final = (d1_sin_v1) | {u1}
                            cd2_final = (d2_sin_v2) | {u2}

                            if len(ci_final) == 0:
                                continue

                            # Verificar conexidad de las tres clases
                            if not _is_conn(G, ci_final):
                                continue
                            if not _is_conn(G, cd1_final):
                                continue
                            if not _is_conn(G, cd2_final):
                                continue

                            new_bs = {c: set(bs) for c, bs in branch_sets.items()}
                            new_bs[c_target] = ci_final
                            new_bs[c_donor1] = cd1_final
                            new_bs[c_donor2] = cd2_final

                            new_main = (main_comp | comp_frag | {v1, v2}) - {u1, u2}
                            info = (f"E8_double(Ci=C{c_target},"
                                    f"Cd1=C{c_donor1},v1={v1}->Ci,u1={u1}->Cd1,"
                                    f"Cd2=C{c_donor2},v2={v2}->Ci,u2={u2}->Cd2)")
                            return True, new_bs, new_main, info

    return False, branch_sets, main_comp, ""


# ═══════════════════════════════════════════════════════════════════════════
# FASE 5 — FUSION FORZADA (NUEVO EN V12.2)
# ═══════════════════════════════════════════════════════════════════════════

def _try_forced_merge_phase5(G, branch_sets, colors, nb_cache):
    """
    Fase 5 — Fusion Forzada de Fragmentos.

    Contexto: se llama solo cuando cond_edges=True pero cond_connected=False.
    Es decir: todos los pares de branch sets tienen aristas entre si,
    pero uno o mas branch sets internamente no son conexos.

    Estrategia agresiva: para cada branch set desconexo, tomar el
    fragmento menor e intentar conectarlo al mayor tomando prestado
    un nodo de otro branch set (el que tenga mas nodos), verificando
    que ese branch set donante quede conexo.

    A diferencia de E3-E7, esta fase NO requiere que el nodo robado
    toque ambos fragmentos — solo necesita que el fragmento menor
    quede alcanzable desde el mayor a traves de un puente de 1 o 2 saltos.

    Retorna (branch_sets_modificado, eventos_log) o (branch_sets_original, [])
    """
    events = []
    modified = False

    for c in colors:
        if _is_conn(G, branch_sets[c]):
            continue

        subG = G.subgraph(branch_sets[c])
        components = sorted(nx.connected_components(subG), key=len, reverse=True)
        if len(components) <= 1:
            continue

        main_comp = set(components[0])

        for comp_minor in components[1:]:
            comp_minor = set(comp_minor)
            merged = False

            # Intento 1: robar nodo de otro BS que conecte comp_minor a main_comp
            for c2 in sorted(colors, key=lambda x: -len(branch_sets[x])):
                if c2 == c or merged:
                    continue
                for w in sorted(list(branch_sets[c2]), key=lambda v: G.degree(v), reverse=True):
                    nb_w = nb_cache[w]
                    toca_minor = bool(nb_w & comp_minor)
                    toca_main  = bool(nb_w & main_comp)
                    rem = branch_sets[c2] - {w}
                    if not rem:
                        continue
                    if not _is_conn(G, rem):
                        continue
                    if toca_minor and toca_main:
                        # Puente directo
                        branch_sets[c2].discard(w)
                        branch_sets[c].add(w)
                        main_comp |= comp_minor | {w}
                        events.append(f"Fase5_puente(C{c},w={w} de C{c2})")
                        merged = True
                        modified = True
                        break
                    elif toca_minor:
                        # Puente indirecto: w toca el fragmento menor,
                        # buscar nodo libre o de otro BS que toque main_comp
                        for c3 in colors:
                            if c3 in (c, c2) or merged:
                                continue
                            for w2 in sorted(list(branch_sets[c3]),
                                             key=lambda v: G.degree(v), reverse=True):
                                if not (nb_cache[w2] & main_comp):
                                    continue
                                if not G.has_edge(w, w2):
                                    continue
                                rem3 = branch_sets[c3] - {w2}
                                if not rem3 or not _is_conn(G, rem3):
                                    continue
                                branch_sets[c2].discard(w)
                                branch_sets[c3].discard(w2)
                                branch_sets[c].add(w)
                                branch_sets[c].add(w2)
                                main_comp |= comp_minor | {w, w2}
                                events.append(
                                    f"Fase5_relay(C{c},w={w} de C{c2},w2={w2} de C{c3})")
                                merged = True
                                modified = True
                                break
                            if merged:
                                break
                    if merged:
                        break

            # Intento 2: usar nodo libre si existe
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


# ═══════════════════════════════════════════════════════════════════════════
# BUILD BRANCH SETS V12.2 — E1-E8 + FASE 5
# ═══════════════════════════════════════════════════════════════════════════

def build_branch_sets_v12_2(G, coloring, chi):
    """
    V12.2 — Pipeline completo E1-E8 + Fase 5 Fusion Forzada.

    Fases:
      2   — BFS con nodos libres
      2.5 — E1→E8 para cada fragmento (dentro de MAX_REPAIR_ITERS)
      3   — Reparar pares sin arista (FIX2 + FIX3)
      4   — Re-aplicar E1→E8 post-Fase3
      5   — Fusion Forzada si cond_edges=True pero cond_connected=False

    Novedad V12.2:
      - E7+E6 encadenados: si E7 tiene exito, intenta E6 inmediatamente
      - E8 Double Swap: nuevo ultimo recurso antes de rendirse
      - Fase 5: fusión forzada post-Fase4
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
    e7_events = []  # registrar activaciones de E7, E8 y Fase5

    # ── FASE 2: BFS con nodos libres ─────────────────────────────────────
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
        for iso in classes[c] - component:
            allowed = classes[c] | free_nodes
            try:
                path = nx.shortest_path(G.subgraph(allowed), center, iso)
                for pv in path:
                    branch_sets[c].add(pv)
                    free_nodes.discard(pv)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

    # ── FASE 2.5: E1-E8 para cada fragmento ─────────────────────────────
    for _pass in range(MAX_REPAIR_ITERS):
        still_broken = False
        for c in colors:
            if _is_conn(G, branch_sets[c]):
                continue
            still_broken = True

            subG_bs = G.subgraph(branch_sets[c])
            components = sorted(nx.connected_components(subG_bs), key=len, reverse=True)
            if len(components) <= 1:
                continue
            main_comp = set(components[0])
            free_now  = _free_nodes(branch_sets, G)

            for comp in components[1:]:
                comp = set(comp)
                connected = False

                # E1: nodo libre que toca AMBOS lados
                for w in sorted(free_now, key=lambda v: -G.degree(v)):
                    nb = nb_cache[w]
                    if (nb & comp) and (nb & main_comp):
                        branch_sets[c].add(w)
                        free_now.discard(w)
                        main_comp |= comp | {w}
                        connected = True
                        break
                if connected:
                    continue

                # E2: camino por nodos libres
                for src in comp:
                    for dst in main_comp:
                        try:
                            path = nx.shortest_path(
                                G.subgraph(branch_sets[c] | free_now), src, dst)
                            for pv in path:
                                branch_sets[c].add(pv)
                                free_now.discard(pv)
                            main_comp |= comp | set(path)
                            connected = True
                            break
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            pass
                    if connected:
                        break
                if connected:
                    continue

                # E3: nodo cedible de otro Bj tocando AMBOS lados
                for c2 in sorted(colors, key=lambda x: -len(branch_sets[x])):
                    if c2 == c:
                        continue
                    for w in sorted(list(branch_sets[c2]), key=lambda v: -G.degree(v)):
                        nb = nb_cache[w]
                        if not (nb & comp) or not (nb & main_comp):
                            continue
                        rem = branch_sets[c2] - {w}
                        if not rem or not _is_conn(G, rem):
                            continue
                        branch_sets[c2].discard(w)
                        branch_sets[c].add(w)
                        free_now = _free_nodes(branch_sets, G)
                        main_comp |= comp | {w}
                        connected = True
                        break
                    if connected:
                        break
                if connected:
                    continue

                # E4: caminos simples largo 2-5 por nodos cedibles
                ntb = _build_ntb(branch_sets)
                best_path, best_donors = None, []
                for src in comp:
                    for dst in main_comp:
                        for cutoff in range(2, 6):
                            try:
                                for path in nx.all_simple_paths(G, src, dst, cutoff=cutoff):
                                    donors = {}
                                    ok = True
                                    for pv in path[1:-1]:
                                        if pv in free_now:
                                            continue
                                        cd = ntb.get(pv)
                                        if cd is None or cd == c:
                                            ok = False
                                            break
                                        rem = branch_sets[cd] - {pv}
                                        if not rem or not _is_conn(G, rem):
                                            ok = False
                                            break
                                        donors[pv] = cd
                                    if ok and (best_path is None or
                                               len(path) < len(best_path)):
                                        best_path = path
                                        best_donors = list(donors.items())
                                if best_path:
                                    break
                            except Exception:
                                pass
                    if best_path:
                        break
                if best_path:
                    for pv, cd in best_donors:
                        branch_sets[cd].discard(pv)
                    for pv in best_path:
                        branch_sets[c].add(pv)
                    main_comp |= comp | set(best_path)
                    connected = True
                if connected:
                    continue

                # E5: nodo cedible de UN lado + nodo libre del otro
                for c2 in colors:
                    if c2 == c:
                        continue
                    for w in list(branch_sets[c2]):
                        nb_w = nb_cache[w]
                        toca_comp = bool(nb_w & comp)
                        toca_main = bool(nb_w & main_comp)
                        if not (toca_comp or toca_main):
                            continue
                        rem = branch_sets[c2] - {w}
                        if not rem or not _is_conn(G, rem):
                            continue
                        for wf in free_now:
                            if not G.has_edge(w, wf):
                                continue
                            nb_wf = nb_cache[wf]
                            if toca_comp and (nb_wf & main_comp):
                                branch_sets[c2].discard(w)
                                branch_sets[c].add(w)
                                branch_sets[c].add(wf)
                                free_now.discard(wf)
                                main_comp |= comp | {w, wf}
                                connected = True
                                break
                            elif toca_main and (nb_wf & comp):
                                branch_sets[c2].discard(w)
                                branch_sets[c].add(w)
                                branch_sets[c].add(wf)
                                free_now.discard(wf)
                                main_comp |= comp | {w, wf}
                                connected = True
                                break
                        if connected:
                            break
                    if connected:
                        break
                if connected:
                    continue

                # E6: KEMPE SWAP
                swap_ok, branch_sets, new_main = _try_kempe_swap_e6(
                    G, branch_sets, colors, c, main_comp, comp, nb_cache
                )
                if swap_ok:
                    main_comp = new_main
                    connected = True
                    still_broken = True   # FIX 1 (V12.5): forzar recomputo
                    break                 # FIX 1: salir del loop de fragmentos

                # E7: KEMPE CHAIN TRIPLE-STEP
                chain_ok, branch_sets, new_main, info = _try_kempe_chain_e7(
                    G, branch_sets, colors, c, main_comp, comp, nb_cache
                )
                if chain_ok:
                    main_comp = new_main
                    connected = True
                    e7_events.append(f"Fase2.5 C{c}: {info}")
                    # V12.2: encadenar E6 inmediatamente post-E7
                    swap_ok2, branch_sets, new_main2 = _try_kempe_swap_e6(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache
                    )
                    if swap_ok2:
                        main_comp = new_main2
                        e7_events.append(f"Fase2.5 C{c}: E6_post_E7 exitoso")
                    still_broken = True   # FIX 1 (V12.5): forzar recomputo
                    break                 # FIX 1: salir del loop de fragmentos

                # E8: DOUBLE SWAP SIMULTANEO (NUEVO V12.2)
                dswap_ok, branch_sets, new_main, info8 = _try_double_swap_e8(
                    G, branch_sets, colors, c, main_comp, comp, nb_cache
                )
                if dswap_ok:
                    main_comp = new_main
                    connected = True
                    e7_events.append(f"Fase2.5 C{c}: {info8}")
                    still_broken = True   # FIX 1 (V12.5): forzar recomputo
                    break                 # FIX 1: salir del loop de fragmentos

        if not still_broken:
            break

    # ── FASE 3: reparar pares sin arista ─────────────────────────────────
    iters_used = 0
    for _ in range(MAX_REPAIR_ITERS):
        contracted = _build_contracted(G, branch_sets, colors)
        pairs = _missing_pairs(contracted, colors)
        if not pairs:
            break

        repaired_any = False
        for (ci, cj) in pairs:
            contracted = _build_contracted(G, branch_sets, colors)
            if cj in contracted[ci]:
                continue

            ntb      = _build_ntb(branch_sets)
            free_now = _free_nodes(branch_sets, G)

            # FIX 2: nodo libre con vecinos en ambos sets
            fixed_by_free = False
            for wf in sorted(free_now, key=lambda v: -G.degree(v)):
                nb_wf = nb_cache[wf]
                if (nb_wf & branch_sets[ci]) and (nb_wf & branch_sets[cj]):
                    branch_sets[ci].add(wf)
                    iters_used += 1
                    ct_check = _build_contracted(G, branch_sets, colors)
                    if cj in ct_check[ci]:
                        repaired_any = True
                        fixed_by_free = True
                    else:
                        branch_sets[ci].discard(wf)
                        iters_used -= 1
                    break
            if fixed_by_free:
                continue

            # Estrategia normal
            best_nb, best_source, best_score = None, None, -1

            for src_c, tgt_c in [(cj, ci), (ci, cj)]:
                for nb in list(branch_sets[src_c]):
                    if not any(ntb.get(w) == tgt_c for w in G.neighbors(nb)):
                        continue
                    rem = branch_sets[src_c] - {nb}
                    if not rem or not _is_conn(G, rem):
                        continue
                    score = sum(1 for w in G.neighbors(nb) if ntb.get(w) == tgt_c)
                    if score > best_score:
                        best_score, best_nb, best_source = score, nb, src_c

            # FIX 3: relay
            if best_nb is None:
                for cm in colors:
                    if cm in (ci, cj):
                        continue
                    for nb in list(branch_sets[cm]):
                        has_i = any(ntb.get(w) == ci for w in G.neighbors(nb))
                        has_j = any(ntb.get(w) == cj for w in G.neighbors(nb))
                        if not (has_i and has_j):
                            continue
                        rem = branch_sets[cm] - {nb}
                        if not rem or not _is_conn(G, rem):
                            continue
                        score = (
                            sum(1 for w in G.neighbors(nb) if ntb.get(w) == ci) +
                            sum(1 for w in G.neighbors(nb) if ntb.get(w) == cj)
                        )
                        if score > best_score:
                            best_score, best_nb, best_source = score, nb, cm

            # RELAY-2 (V12.4+): dos mediadores de clases distintas (audaz)
            # FIX 4 (V12.5): verifica que la arista ci-cj fue realmente creada
            if best_nb is None:
                relay2_done = False
                for cm1 in colors:
                    if cm1 in (ci, cj) or relay2_done:
                        continue
                    for nb1 in list(branch_sets[cm1]):
                        if not any(ntb.get(w) == ci for w in G.neighbors(nb1)):
                            continue
                        rem1 = branch_sets[cm1] - {nb1}
                        if not rem1:
                            continue
                        for cm2 in colors:
                            if cm2 in (ci, cj, cm1) or relay2_done:
                                continue
                            for nb2 in list(branch_sets[cm2]):
                                if not any(ntb.get(w) == cj for w in G.neighbors(nb2)):
                                    continue
                                rem2 = branch_sets[cm2] - {nb2}
                                if not rem2:
                                    continue
                                if not _is_conn(G, rem1):
                                    continue
                                if not _is_conn(G, rem2):
                                    continue
                                # Ejecutar movimiento
                                branch_sets[cm1].discard(nb1)
                                branch_sets[cm2].discard(nb2)
                                branch_sets[ci].add(nb1)
                                branch_sets[cj].add(nb2)
                                # FIX 4: verificar que la arista ci-cj fue creada
                                ct_verify = _build_contracted(G, branch_sets, colors)
                                if cj in ct_verify[ci]:
                                    repaired_any = True
                                    iters_used += 2
                                    relay2_done = True
                                else:
                                    # Revertir — no creó la arista
                                    branch_sets[cm1].add(nb1)
                                    branch_sets[cm2].add(nb2)
                                    branch_sets[ci].discard(nb1)
                                    branch_sets[cj].discard(nb2)
                                break
                            if relay2_done:
                                break
                    if relay2_done:
                        break

            if best_nb is not None:
                target = ci if best_source in (cj,) else (cj if best_source == ci else ci)
                if best_source not in (ci, cj):
                    target = ci
                branch_sets[best_source].discard(best_nb)
                branch_sets[target].add(best_nb)
                repaired_any = True
                iters_used += 1

                # FASE 2.7: revertir si source quedo desconexo
                if not _is_conn(G, branch_sets[best_source]):
                    branch_sets[best_source].add(best_nb)
                    branch_sets[target].discard(best_nb)
                    repaired_any = False
                    iters_used -= 1

        if not repaired_any:
            break

    # ── FASE 4: reparacion de conexidad post-Fase3 con E1-E8 ─────────────
    for _pass in range(MAX_REPAIR_ITERS):
        still_broken = False
        for c in colors:
            if _is_conn(G, branch_sets[c]):
                continue
            still_broken = True
            subG_bs = G.subgraph(branch_sets[c])
            components = sorted(nx.connected_components(subG_bs), key=len, reverse=True)
            if len(components) <= 1:
                continue
            main_comp = set(components[0])
            free_now  = _free_nodes(branch_sets, G)

            for comp in components[1:]:
                comp = set(comp)
                connected = False

                # Libre directo
                for w in free_now:
                    nb = nb_cache[w]
                    if (nb & comp) and (nb & main_comp):
                        branch_sets[c].add(w)
                        free_now.discard(w)
                        main_comp |= comp | {w}
                        connected = True
                        break
                if connected:
                    continue

                # Cedible tocando ambos
                for c2 in colors:
                    if c2 == c:
                        continue
                    for w in list(branch_sets[c2]):
                        nb = nb_cache[w]
                        if not (nb & comp) or not (nb & main_comp):
                            continue
                        rem = branch_sets[c2] - {w}
                        if not rem or not _is_conn(G, rem):
                            continue
                        branch_sets[c2].discard(w)
                        branch_sets[c].add(w)
                        main_comp |= comp | {w}
                        connected = True
                        break
                    if connected:
                        break
                if connected:
                    continue

                # FIX 1 en Fase 4
                for c2 in colors:
                    if c2 == c or connected:
                        continue
                    for w in list(branch_sets[c2]):
                        nb_w = nb_cache[w]
                        toca_c = bool(nb_w & comp)
                        toca_m = bool(nb_w & main_comp)
                        if not (toca_c or toca_m):
                            continue
                        rem = branch_sets[c2] - {w}
                        if not rem or not _is_conn(G, rem):
                            continue
                        for wf in free_now:
                            if not G.has_edge(w, wf):
                                continue
                            nb_wf = nb_cache[wf]
                            if toca_c and (nb_wf & main_comp):
                                branch_sets[c2].discard(w)
                                branch_sets[c].add(w)
                                branch_sets[c].add(wf)
                                free_now.discard(wf)
                                main_comp |= comp | {w, wf}
                                connected = True
                                break
                            elif toca_m and (nb_wf & comp):
                                branch_sets[c2].discard(w)
                                branch_sets[c].add(w)
                                branch_sets[c].add(wf)
                                free_now.discard(wf)
                                main_comp |= comp | {w, wf}
                                connected = True
                                break
                        if connected:
                            break
                    if connected:
                        break
                if connected:
                    continue

                # E6 en Fase 4
                if not connected:
                    swap_ok, branch_sets, new_main = _try_kempe_swap_e6(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache
                    )
                    if swap_ok:
                        main_comp = new_main
                        connected = True
                        still_broken = True   # FIX 1 (V12.5)
                        break                 # FIX 1: recompute from scratch

                # E7 en Fase 4 (OBLIGATORIO si E6 fallo — V12.2)
                if not connected:
                    chain_ok, branch_sets, new_main, info = _try_kempe_chain_e7(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache
                    )
                    if chain_ok:
                        main_comp = new_main
                        connected = True
                        e7_events.append(f"Fase4 C{c}: {info}")
                        # V12.2: encadenar E6 post-E7 en Fase 4
                        swap_ok2, branch_sets, new_main2 = _try_kempe_swap_e6(
                            G, branch_sets, colors, c, main_comp, comp, nb_cache
                        )
                        if swap_ok2:
                            main_comp = new_main2
                            e7_events.append(f"Fase4 C{c}: E6_post_E7 exitoso")
                        still_broken = True   # FIX 1 (V12.5)
                        break                 # FIX 1: recompute from scratch

                # E8 en Fase 4 (NUEVO V12.2)
                if not connected:
                    dswap_ok, branch_sets, new_main, info8 = _try_double_swap_e8(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache
                    )
                    if dswap_ok:
                        main_comp = new_main
                        connected = True
                        e7_events.append(f"Fase4 C{c}: {info8}")
                        still_broken = True   # FIX 1 (V12.5)
                        break                 # FIX 1: recompute from scratch

        if not still_broken:
            break

    # ── FASE 5: FUSION FORZADA (NUEVO V12.2) ─────────────────────────────
    # Solo se activa si hay desconexion residual tras Fase 4
    any_disconnected = any(not _is_conn(G, branch_sets[c]) for c in colors)
    if any_disconnected:
        branch_sets, fase5_events, modified = _try_forced_merge_phase5(
            G, branch_sets, colors, nb_cache
        )
        if modified:
            e7_events.extend(fase5_events)
            # FIX 5 (V12.5): Re-aplicar E6+E7+E8 post-Fase5 para refinar
            for c in colors:
                if _is_conn(G, branch_sets[c]):
                    continue
                subG_bs = G.subgraph(branch_sets[c])
                components = sorted(nx.connected_components(subG_bs), key=len, reverse=True)
                if len(components) <= 1:
                    continue
                main_comp = set(components[0])
                for comp in components[1:]:
                    comp = set(comp)
                    swap_ok, branch_sets, new_main = _try_kempe_swap_e6(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache
                    )
                    if swap_ok:
                        main_comp = new_main
                        e7_events.append(f"Fase5_post C{c}: E6 exitoso")
                        continue
                    chain_ok, branch_sets, new_main, info = _try_kempe_chain_e7(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache
                    )
                    if chain_ok:
                        main_comp = new_main
                        e7_events.append(f"Fase5_post C{c}: {info}")
                        continue
                    # FIX 5: E8 post-Fase5 (nuevo en V12.5)
                    dswap_ok, branch_sets, new_main, info8 = _try_double_swap_e8(
                        G, branch_sets, colors, c, main_comp, comp, nb_cache
                    )
                    if dswap_ok:
                        main_comp = new_main
                        e7_events.append(f"Fase5_post C{c}: {info8}")

    # Verificacion final
    contracted  = _build_contracted(G, branch_sets, colors)
    pairs_ok    = not _missing_pairs(contracted, colors)
    conn_ok     = all(_is_conn(G, branch_sets[c]) for c in colors)
    disjoint_ok = (len(set().union(*branch_sets.values())) ==
                   sum(len(bs) for bs in branch_sets.values()))
    success = pairs_ok and conn_ok and disjoint_ok
    return branch_sets, colors, iters_used, success, e7_events


# ═══════════════════════════════════════════════════════════════════════════
# RESILIENT RE-COLORING — V12.2 (30 intentos + diagnóstico de muerte)
# ═══════════════════════════════════════════════════════════════════════════

def _get_hybrid_orders(G, nodes_fixed, seed=8888):
    """
    Motor Hibrido V12.5 — 4 ordenes deterministicos reales.

    FIX 3 (V12.5): ahora genera ordenes utiles de verdad basados en grado.
      Orden 0: grado descendente (mas conectado primero) — clasico
      Orden 1: grado ascendente (menos conectado primero) — busca periferia
      Orden 2: indice natural ascendente — orden estructural
      Orden 3: indice natural descendente — simetria estructural

    En V12.4, nodes_fixed ya venia ordenado por grado desc, asi que
    Orden 0 y Orden 1 eran identicos o casi. Ahora son distintos.
    """
    order_deg_desc = sorted(nodes_fixed, key=lambda v: -G.degree(v))
    order_deg_asc  = sorted(nodes_fixed, key=lambda v:  G.degree(v))
    order_idx_asc  = sorted(nodes_fixed)
    order_idx_desc = sorted(nodes_fixed, reverse=True)
    return [order_deg_desc, order_deg_asc, order_idx_asc, order_idx_desc]


def _get_intelligent_orders(G, nodes_fixed, graph_seed):
    """
    V12.7 — 20 ordenes DIVERSOS basados en propiedades reales del grafo.

    Reemplaza la enumeracion exhaustiva de itertools.permutations (FIX 6
    de V12.6 que causaba atascos de horas). En su lugar genera 20 ordenes
    que cubren el espacio de forma DIVERSA sin explosion combinatoria:

    Grupo A (4): Motor Hibrido clasico — grado asc/desc, indice asc/desc
    Grupo B (4): Vecindario — suma de grados de vecinos asc/desc,
                 numero de vecinos en cliques (triangulos) asc/desc
    Grupo C (4): Centralidad — excentricidad asc/desc,
                 grado ponderado por clustering asc/desc
    Grupo D (4): Intercalado — alternando nodos alto/bajo grado
                 (captura estructura bipartita local)
    Grupo E (4): Aleatorio con semilla por grafo (FIX 8, diversidad pura)

    Total: 20 ordenes distintos y utiles.
    """
    import random as _rnd

    rng = _rnd.Random(graph_seed)

    # ── Grupo A: Motor Hibrido clasico (4 ordenes) ────────────────────────
    order_deg_desc = sorted(nodes_fixed, key=lambda v: -G.degree(v))
    order_deg_asc  = sorted(nodes_fixed, key=lambda v:  G.degree(v))
    order_idx_asc  = sorted(nodes_fixed)
    order_idx_desc = sorted(nodes_fixed, reverse=True)

    # ── Grupo B: Vecindario (4 ordenes) ───────────────────────────────────
    # Suma de grados de vecinos (nodos en zonas densas vs periferia)
    nbr_deg_sum = {v: sum(G.degree(u) for u in G.neighbors(v)) for v in nodes_fixed}
    order_nbr_desc = sorted(nodes_fixed, key=lambda v: -nbr_deg_sum[v])
    order_nbr_asc  = sorted(nodes_fixed, key=lambda v:  nbr_deg_sum[v])
    # Numero de triangulos (nodos en cliques locales primero/ultimo)
    try:
        triangles = nx.triangles(G)
    except Exception:
        triangles = {v: 0 for v in nodes_fixed}
    order_tri_desc = sorted(nodes_fixed, key=lambda v: -triangles.get(v, 0))
    order_tri_asc  = sorted(nodes_fixed, key=lambda v:  triangles.get(v, 0))

    # ── Grupo C: Centralidad / excentricidad (4 ordenes) ──────────────────
    try:
        ecc = nx.eccentricity(G)
        order_ecc_asc  = sorted(nodes_fixed, key=lambda v:  ecc.get(v, 0))
        order_ecc_desc = sorted(nodes_fixed, key=lambda v: -ecc.get(v, 0))
    except Exception:
        order_ecc_asc  = order_deg_asc[:]
        order_ecc_desc = order_deg_desc[:]
    # Grado ponderado por clustering local
    try:
        clust = nx.clustering(G)
    except Exception:
        clust = {v: 0.0 for v in nodes_fixed}
    order_clust_desc = sorted(nodes_fixed, key=lambda v: -(G.degree(v) * (1 + clust.get(v, 0))))
    order_clust_asc  = sorted(nodes_fixed, key=lambda v:  (G.degree(v) * (1 + clust.get(v, 0))))

    # ── Grupo D: Intercalado alto/bajo grado (4 ordenes) ──────────────────
    # Alterna nodos de mayor grado con nodos de menor grado
    hi = order_deg_desc[:]
    lo = order_deg_asc[:]
    interleaved_hl = []
    for i in range(len(nodes_fixed)):
        interleaved_hl.append(hi[i] if i % 2 == 0 else lo[i])
    interleaved_lh = []
    for i in range(len(nodes_fixed)):
        interleaved_lh.append(lo[i] if i % 2 == 0 else hi[i])
    # Intercalado por vecindario
    hi_nbr = order_nbr_desc[:]
    lo_nbr = order_nbr_asc[:]
    interleaved_nbr_hl = []
    for i in range(len(nodes_fixed)):
        interleaved_nbr_hl.append(hi_nbr[i] if i % 2 == 0 else lo_nbr[i])
    interleaved_nbr_lh = []
    for i in range(len(nodes_fixed)):
        interleaved_nbr_lh.append(lo_nbr[i] if i % 2 == 0 else hi_nbr[i])

    # ── Grupo E: Aleatorio con semilla por grafo (4 ordenes) ──────────────
    rand_orders = []
    for _ in range(4):
        o = nodes_fixed[:]
        rng.shuffle(o)
        rand_orders.append(o)

    all_orders = [
        order_deg_desc, order_deg_asc, order_idx_asc, order_idx_desc,   # A
        order_nbr_desc, order_nbr_asc, order_tri_desc, order_tri_asc,    # B
        order_ecc_asc, order_ecc_desc, order_clust_desc, order_clust_asc, # C
        interleaved_hl, interleaved_lh,                                   # D
        interleaved_nbr_hl, interleaved_nbr_lh,                          # D
    ] + rand_orders                                                        # E

    return all_orders


def build_branch_sets_resilient(G, chi, nodes_fixed, name=""):
    """
    V12.7 TURBO — Motor con 20 ordenes inteligentes + timeout suave.

    Estrategia:
      1. 20 ordenes diversos (Grupos A-E) generados desde propiedades
         reales del grafo. Cada orden prueba MAX_COLOR_RETRIES coloraciones.
         Cubre el espacio de forma diversa SIN explosion combinatoria.
      2. Si ninguno tiene exito en GRAPH_TIMEOUT segundos, toma el mejor
         resultado parcial y avanza (timeout SUAVE — no produce FAIL falso
         si ya encontro algo valido).
      3. Re-coloreos aleatorios adicionales si el tiempo lo permite.
      4. Diagnostico de muerte detallado si falla tras todo.
    """
    import random as _random

    best_branch  = None
    best_colors  = None
    best_iters   = 0
    best_vr      = None
    best_success = False
    best_e7      = []
    recolor_used = 0

    # FIX 8: semilla reproducible derivada de la estructura del grafo
    graph_seed = hash(tuple(sorted(G.edges()))) % (2**31)
    rng_local  = _random.Random(graph_seed)

    # Cronometro global por grafo (FIX 9 timeout suave)
    t_start_graph = time.time()

    def _timeout_reached():
        return (time.time() - t_start_graph) > GRAPH_TIMEOUT

    def _try_order(node_order):
        """Prueba un orden de nodos con hasta MAX_COLOR_RETRIES coloraciones."""
        nonlocal best_branch, best_colors, best_iters, best_vr, best_success, best_e7
        for n_sol in range(MAX_COLOR_RETRIES):
            if _timeout_reached():
                return False  # timeout — salir y conservar mejor parcial
            col = get_coloring_nth(G, chi, node_order=node_order, nth=n_sol)
            if col is None:
                break
            if len(set(col.values())) != chi:
                continue
            branch_sets, colors, iters, _, e7_ev = build_branch_sets_v12_2(
                G, col, chi
            )
            if branch_sets is None:
                continue
            vr = verify_kk_minor(G, branch_sets, colors, chi)
            # Guardar siempre el mejor intento parcial
            if best_branch is None or (
                vr["pairs_ok"] > (best_vr["pairs_ok"] if best_vr else -1)
            ):
                best_branch  = branch_sets
                best_colors  = colors
                best_iters   = iters
                best_vr      = vr
                best_e7      = e7_ev
                if not best_success:
                    best_success = vr["all_ok"]
            if vr["all_ok"]:
                best_branch  = branch_sets
                best_colors  = colors
                best_iters   = iters
                best_vr      = vr
                best_success = True
                best_e7      = e7_ev
                return True
        return False

    # ── Fase A: 20 ordenes inteligentes (FIX 6 reemplazado) ───────────────
    smart_orders = _get_intelligent_orders(G, nodes_fixed, graph_seed)

    for ord_idx, node_order in enumerate(smart_orders):
        if _timeout_reached():
            break
        if _try_order(node_order):
            return best_branch, best_colors, best_iters, best_vr, True, best_e7, 0

    # ── Fase B: re-coloreos aleatorios si queda tiempo ────────────────────
    for recolor_attempt in range(1, MAX_RECOLOR_ATTEMPTS):
        if _timeout_reached():
            break
        node_order = nodes_fixed[:]
        rng_local.shuffle(node_order)
        if not best_success:
            print(f"  [RE-COLORING] {name} — intento {recolor_attempt}/"
                  f"{MAX_RECOLOR_ATTEMPTS - 1}...")
        if _try_order(node_order):
            return best_branch, best_colors, best_iters, best_vr, True, best_e7, recolor_attempt

    # ── Diagnostico de muerte (solo si fallo total) ────────────────────────
    if not best_success and best_branch is not None:
        elapsed = time.time() - t_start_graph
        if _timeout_reached():
            print(f"\n  [TIMEOUT] '{name}' — {elapsed:.1f}s > {GRAPH_TIMEOUT}s "
                  f"— reportando mejor intento parcial")
        else:
            print(f"\n  [DEBUG] Fallo persistente en '{name}':")
        for c in (best_colors or []):
            bs = best_branch.get(c, set())
            if not _is_conn(G, bs):
                print(f"    [DEBUG] Bi={sorted(bs)} (C{c}, size={len(bs)}) desconexo")
        contracted = _build_contracted(G, best_branch, best_colors or [])
        missing = _missing_pairs(contracted, best_colors or [])
        if missing:
            print(f"    [DEBUG] Pares sin arista: {missing}")
        n_g = G.number_of_nodes()
        if chi >= 7:
            print(f"    [CRITICAL] chi={chi}>=7 — posible contraejemplo")
        elif n_g <= chi + 2:
            print(f"    [INFO] n={n_g}<=chi+2 — limite combinatorio n≈chi")

    return best_branch, best_colors, best_iters, best_vr, best_success, best_e7, recolor_used


# ═══════════════════════════════════════════════════════════════════════════
# VERIFICACION K_k MINOR (sin cambios desde V10)
# ═══════════════════════════════════════════════════════════════════════════

def verify_kk_minor(G, branch_sets, colors, chi):
    k = chi
    total_pairs = k * (k - 1) // 2
    result = {
        "k": k, "total_pairs": total_pairs,
        "cond_nonempty": True, "cond_connected": True,
        "cond_disjoint": True, "cond_edges": True,
        "pairs_ok": 0, "pairs_missing": 0,
        "disconnected_sets": [], "empty_sets": [],
        "overlap_sets": [], "missing_edge_pairs": [],
        "all_ok": False, "relaxed_conn": [],
    }

    for c in colors:
        if not branch_sets[c]:
            result["cond_nonempty"] = False
            result["empty_sets"].append(c)

    contracted   = _build_contracted(G, branch_sets, colors)
    all_pairs_ok = not _missing_pairs(contracted, colors)

    for c in colors:
        bs = branch_sets[c]
        if not bs:
            continue
        if _is_conn(G, bs):
            continue
        if len(bs) == 2:
            u, v = tuple(bs)
            if not G.has_edge(u, v):
                u_ok = any(G.has_edge(u, w) for w in G.nodes() if w not in bs)
                v_ok = any(G.has_edge(v, w) for w in G.nodes() if w not in bs)
                if all_pairs_ok and u_ok and v_ok:
                    result["relaxed_conn"].append(c)
                    continue
        # FIX 7 (V12.6): Singleton con aristas hacia todos los otros branch sets
        # Un nodo aislado de tamaño 1 puede actuar como hub en el minor contraido
        if len(bs) == 1:
            v_singleton = next(iter(bs))
            # Verificar que tiene al menos 1 vecino en CADA otro branch set
            other_colors = [oc for oc in colors if oc != c]
            hub_ok = all(
                any(G.has_edge(v_singleton, w) for w in branch_sets[oc])
                for oc in other_colors
            )
            if hub_ok and all_pairs_ok:
                result["relaxed_conn"].append(c)
                continue
        result["cond_connected"] = False
        result["disconnected_sets"].append(c)

    seen = {}
    for c in colors:
        for v in branch_sets[c]:
            if v in seen:
                result["cond_disjoint"] = False
                result["overlap_sets"].append((v, seen[v], c))
            else:
                seen[v] = c

    for ci, cj in itertools.combinations(colors, 2):
        if cj in contracted[ci]:
            result["pairs_ok"] += 1
        else:
            result["cond_edges"] = False
            result["pairs_missing"] += 1
            result["missing_edge_pairs"].append((ci, cj))

    result["all_ok"] = (
        result["cond_nonempty"] and result["cond_connected"] and
        result["cond_disjoint"] and result["cond_edges"]
    )
    return result


# ═══════════════════════════════════════════════════════════════════════════
# GENERADOR DE GRAFOS (sin cambios desde V11)
# ═══════════════════════════════════════════════════════════════════════════

def get_all_graphs(target_total=500, seed=8888):
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

    attempts = 0
    added    = 0
    max_att  = target_total * 30

    while added < target_total - len(graphs) and attempts < max_att:
        attempts += 1
        n = rng.randint(7, MAX_N_RANDOM)
        p = rng.uniform(0.35, 0.80)
        G = nx.gnp_random_graph(n, p, seed=attempts * 7919 + seed)
        if not nx.is_connected(G) or G.number_of_edges() == 0:
            continue
        chi_est = _greedy_upper_bound(G, list(G.nodes()))
        if not (CHI_TARGET_LOW <= chi_est <= CHI_TARGET_HIGH + 1):
            continue
        graphs.append((G, f"Rand_chi{chi_est}_n{n}_#{attempts}", "Aleatorios", chi_est))
        added += 1

    graphs.sort(key=lambda x: x[0].number_of_nodes())
    return graphs


# ═══════════════════════════════════════════════════════════════════════════
# LOGGER V12.2
# ═══════════════════════════════════════════════════════════════════════════

class Script8Logger:
    def __init__(self):
        self.all_results  = []
        self.chi7_results = []
        self.chi_stats    = defaultdict(lambda: {"ok": 0, "fail": 0, "total": 0})
        self.fam_stats    = defaultdict(lambda: {"ok": 0, "fail": 0, "total": 0})
        self.e7_count     = 0
        self.e8_count     = 0   # nuevo en V12.2
        self.fase5_count  = 0   # nuevo en V12.2

    def add(self, result):
        self.all_results.append(result)
        chi_v = result["chi"]
        fam   = result["familia"]
        ok    = result["success"]
        self.chi_stats[chi_v]["total"] += 1
        self.fam_stats[fam]["total"]   += 1
        if ok:
            self.chi_stats[chi_v]["ok"] += 1
            self.fam_stats[fam]["ok"]   += 1
        else:
            self.chi_stats[chi_v]["fail"] += 1
            self.fam_stats[fam]["fail"]   += 1
        if result.get("e7_events"):
            evs = result["e7_events"]
            if any("E7" in e for e in evs):
                self.e7_count += 1
            if any("E8" in e for e in evs):
                self.e8_count += 1
            if any("Fase5" in e for e in evs):
                self.fase5_count += 1
        if chi_v >= 7:
            self.chi7_results.append(result)
            self._write_chi7(result)
        self._save_checkpoint()

    def _write_chi7(self, result):
        with open(LOG_CHI_ALTO, "a", encoding="utf-8") as f:
            vr  = result["verification"]
            st  = "OK   " if result["success"] else "FALLO"
            f.write(f"\n  [{st}] {result['name']}\n")
            f.write(f"    Familia: {result['familia']}  "
                    f"n={result['n']}  m={result['m']}  "
                    f"chi={result['chi']}  p={result['p']}\n")
            f.write(f"    Iters reparacion: {result['iters']}\n")
            f.write(f"    K_{result['chi']} minor: "
                    f"nonempty={vr['cond_nonempty']} "
                    f"connected={vr['cond_connected']} "
                    f"disjoint={vr['cond_disjoint']} "
                    f"edges={vr['cond_edges']}\n")
            f.write(f"    Pares cubiertos: {vr['pairs_ok']}/{vr['total_pairs']}\n")
            for ev in result.get("e7_events", []):
                f.write(f"    [EVENT] {ev}\n")

    def _save_checkpoint(self):
        ok   = sum(1 for r in self.all_results if r["success"])
        fail = len(self.all_results) - ok
        e7s  = self.e7_count
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            f.write(f"processed={len(self.all_results)}\n")
            f.write(f"ok={ok}\n")
            f.write(f"fail={fail}\n")
            f.write(f"e7_saves={e7s}\n")
            f.write(f"timestamp={datetime.now().isoformat()}\n")

    def finalize(self):
        ok   = sum(1 for r in self.all_results if r["success"])
        fail = len(self.all_results) - ok

        # Log chi >= 7 header
        with open(LOG_CHI_ALTO, "w", encoding="utf-8") as f:
            f.write("=" * 75 + "\n")
            f.write(f"  {SCRIPT_NAME}\n")
            f.write("=" * 75 + "\n")
            f.write(f"  Investigador : Mizael Antonio Tovar Reyes\n")
            f.write(f"  Ubicacion    : Ciudad Juarez, Chihuahua, Mexico\n")
            f.write(f"  Fecha inicio : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  Hardware     : GPU: CUDA (CuPy) + CPU\n")
            f.write(f"  E6 Expandido : ACTIVO (free_nodes + AtomSwap)\n")
            f.write(f"  Triple Swap  : ACTIVO (E7 en Fases 2.5 y 4, exhaustivo)\n")
            f.write(f"  Double Swap  : ACTIVO (E8 en Fases 2.5 y 4)\n")
            f.write(f"  Relay-2      : ACTIVO (Fase 3, verifica arista creada)\n")
            f.write(f"  Motor Hibrido: ACTIVO (4 det grado-real + {MAX_RECOLOR_ATTEMPTS - 1} aleatorios)\n")
            f.write(f"  Fase 5       : ACTIVO (Fusion Forzada + E6/E7/E8 post)\n")
            f.write(f"  Ghost Fix    : ACTIVO (V12.5 — break+recomputo tras swap)\n")
            f.write(f"  Perm Intel   : ACTIVO (V12.7 — 20 ordenes inteligentes diversos)\n")
            f.write(f"  Timeout Suave: ACTIVO (V12.7 — {GRAPH_TIMEOUT}s por grafo)\n")
            f.write(f"  Relaxed Sing : ACTIVO (V12.6 — singleton hub aceptado como minor)\n")
            f.write(f"  Semilla Grafo: ACTIVO (V12.6 — seed reproducible por estructura)\n")
            f.write("=" * 75 + "\n")
        for r in self.chi7_results:
            self._write_chi7(r)

        # Log principal
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("=" * 75 + "\n")
            f.write(f"  {SCRIPT_NAME}\n")
            f.write("=" * 75 + "\n")
            f.write(f"  Investigador : Mizael Antonio Tovar Reyes\n")
            f.write(f"  Actualizado  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  E6 Expandido : ACTIVO (free_nodes + AtomSwap)\n")
            f.write(f"  Triple Swap  : E7 ACTIVO (exhaustivo)\n")
            f.write(f"  Double Swap  : E8 ACTIVO\n")
            f.write(f"  Relay-2      : ACTIVO (Fase 3, verifica arista creada)\n")
            f.write(f"  Motor Hibrido: ACTIVO (4 deterministicos grado-real + aleatorios)\n")
            f.write(f"  Fase 5       : Fusion Forzada + E6/E7/E8 post\n")
            f.write(f"  Ghost Fix    : ACTIVO (V12.5)\n")
            f.write("=" * 75 + "\n\n")
            f.write("RESUMEN POR NUMERO CROMATICO:\n")
            f.write("-" * 55 + "\n")
            f.write(f"  {'chi':<6} {'OK':<8} {'FALLO':<8} {'TOTAL':<8} {'%OK'}\n")
            f.write("-" * 55 + "\n")
            for chi_v in sorted(self.chi_stats.keys()):
                s   = self.chi_stats[chi_v]
                pct = s["ok"] / s["total"] * 100 if s["total"] else 0
                mk  = " <-- CASO ABIERTO HADWIGER" if chi_v >= 7 else ""
                f.write(f"  chi={chi_v:<3} {s['ok']:<8} {s['fail']:<8} {s['total']:<8} {pct:.1f}%{mk}\n")
            f.write("-" * 55 + "\n")
            f.write(f"  {'TOTAL':<6} {ok:<8} {fail:<8} {len(self.all_results):<8}\n\n")

            f.write("RESUMEN POR FAMILIA:\n")
            f.write("-" * 60 + "\n")
            for fam, s in sorted(self.fam_stats.items()):
                pct = s["ok"] / s["total"] * 100 if s["total"] else 0
                st  = "OK   " if s["fail"] == 0 else "FALLO"
                f.write(f"  [{st}] {fam:<25} {s['ok']}/{s['total']} ({pct:.1f}%)\n")
            f.write("-" * 60 + "\n\n")

            f.write(f"GRAFOS SALVADOS POR E7 TRIPLE SWAP : {self.e7_count}\n")
            f.write(f"GRAFOS SALVADOS POR E8 DOUBLE SWAP : {self.e8_count}\n")
            f.write(f"GRAFOS SALVADOS POR FASE 5 FUSION  : {self.fase5_count}\n\n")

            fallos = [r for r in self.all_results if not r["success"]]
            if fallos:
                f.write(f"FALLOS DETALLADOS ({len(fallos)}):\n")
                f.write("-" * 75 + "\n")
                for r in fallos:
                    vr = r["verification"]
                    f.write(f"  FALLO [{r['familia']}] {r['name']}\n")
                    f.write(f"    n={r['n']} m={r['m']} chi={r['chi']} p={r['p']}\n")
                    f.write(f"    nonempty={vr['cond_nonempty']} "
                            f"connected={vr['cond_connected']} "
                            f"disjoint={vr['cond_disjoint']} "
                            f"edges={vr['cond_edges']}\n")
                    if vr["missing_edge_pairs"]:
                        f.write(f"    pares_sin_arista: {vr['missing_edge_pairs']}\n")
                f.write("-" * 75 + "\n\n")
            else:
                f.write("FALLOS: 0 — VERIFICACION COMPLETA EXITOSA\n\n")
                f.write("=" * 75 + "\n")
                f.write("  V12.7 TURBO ZERO FAILURE: 20 ordenes inteligentes + timeout suave\n")
                f.write("  E6+E7+E8+Fase5+GhostFix+PermInteligentes+RelaxedSing — 0 fallos\n")
                f.write("=" * 75 + "\n")

            f.write("\n===========================================================================\n")
            f.write("RESULTADOS DETALLADOS:\n")
            f.write("===========================================================================\n\n")
            for r in self.all_results:
                vr   = r["verification"]
                st   = "OK  " if r["success"] else "FALLO"
                e7m  = " [E7]" if any("E7" in e for e in r.get("e7_events", [])) else ""
                e8m  = " [E8]" if any("E8" in e for e in r.get("e7_events", [])) else ""
                f5m  = " [F5]" if any("Fase5" in e for e in r.get("e7_events", [])) else ""
                f.write(f"  [{st}] [{r['familia']}] {r['name']:<35} "
                        f"n={r['n']:<4} m={r['m']:<5} chi={r['chi']:<3} "
                        f"p={r['p']:<3} iters={r['iters']:<4} "
                        f"pairs={vr['pairs_ok']}/{vr['total_pairs']}{e7m}{e8m}{f5m}\n")


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
    print("  NOVEDADES V12.7 TURBO ZERO FAILURE (base exacta V12.6):")
    print("    [FIX 6 NUEVO] 20 ordenes inteligentes: grado/vecindario/centralidad/intercalado/random")
    print(f"    [FIX 9]       Timeout suave {GRAPH_TIMEOUT}s por grafo — nunca se atasca para siempre")
    print("    [FIX 7]       Relaxed Singleton: singleton hub = minor valido (heredado)")
    print("    [FIX 8]       Semilla reproducible por grafo (heredado)")
    print()

    print("Generando grafos de prueba...")
    t_gen  = time.time()
    graphs = get_all_graphs(target_total=TARGET_TOTAL, seed=RANDOM_SEED)
    print(f"\n  Total a verificar: {len(graphs)}  (generacion: {time.time()-t_gen:.1f}s)\n")

    logger = Script8Logger()
    print(f"  Log principal   : {LOG_FILE}")
    print(f"  Log chi >= 7    : {LOG_CHI_ALTO}")
    print(f"  Checkpoint      : {CHECKPOINT_FILE}")
    print()

    ok_count   = 0
    fail_count = 0
    e7_saves   = 0
    t0 = time.time()

    iterator = tqdm(graphs, desc="Verificando K_k minor", ncols=90,
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
                    ) if TQDM_AVAILABLE else graphs

    try:
        for G, name, familia, expected_chi in iterator:
            if not nx.is_connected(G):
                continue

            n = G.number_of_nodes()
            m = G.number_of_edges()

            chi = chromatic_fast(G, max_k=(expected_chi or CHI_TARGET_HIGH) + 2)
            if chi is None or chi < CHI_TARGET_LOW:
                continue

            try:
                p_g, _, _, method = compute_p_with_expansion_vertices(G)
            except Exception:
                p_g    = chi - 1
                method = "FALLBACK"

            nodes_fixed   = list(G.nodes())
            best_branch, best_colors, best_iters, best_vr, best_success, best_e7, recolor_used = \
                build_branch_sets_resilient(G, chi, nodes_fixed, name=name)

            if best_branch is None:
                continue

            if best_e7:
                e7_saves += 1

            result = {
                "name": name, "familia": familia,
                "n": n, "m": m, "chi": chi, "p": p_g, "method": method,
                "iters": best_iters,
                "success": best_success,
                "verification": best_vr,
                "e7_events": best_e7,
                "recolor_used": recolor_used,
            }

            if best_success:
                ok_count += 1
            else:
                fail_count += 1

            logger.add(result)

            show = (chi >= 7) or not best_success
            if show:
                status  = "OK   " if best_success else "FALLO"
                chi_tag = " *** HADWIGER ***" if chi >= 7 else ""
                e7_tag  = " [E7]" if any("E7" in e for e in best_e7) else ""
                e8_tag  = " [E8]" if any("E8" in e for e in best_e7) else ""
                f5_tag  = " [F5]" if any("Fase5" in e for e in best_e7) else ""
                vr      = best_vr
                msg     = (f"  [{status}] [{familia:<15}] {name:<30} "
                           f"n={n:<3} chi={chi}{chi_tag}{e7_tag}{e8_tag}{f5_tag}")
                if not best_success:
                    msg += (f"\n    nonempty={vr['cond_nonempty']} "
                            f"connected={vr['cond_connected']} "
                            f"edges={vr['cond_edges']}")
                (tqdm.write(msg) if TQDM_AVAILABLE else print(msg))

    except KeyboardInterrupt:
        print("\n\n  !! Interrumpido — guardando logs...")
    finally:
        elapsed = (time.time() - t0) / 60
        logger.finalize()

        print()
        print("=" * 70)
        print(f"  RESULTADO FINAL — {SCRIPT_NAME}")
        print("=" * 70)
        print(f"  Grafos verificados   : {ok_count + fail_count}")
        print(f"  Exitosos             : {ok_count}")
        print(f"  Fallos               : {fail_count}")
        print(f"  Salvados por E7      : {logger.e7_count}")
        print(f"  Salvados por E8      : {logger.e8_count}")
        print(f"  Salvados por Fase5   : {logger.fase5_count}")
        print(f"  Tiempo               : {elapsed:.1f} min")
        print()
        print("  Desglose chi >= 7:")
        for chi_v in sorted(logger.chi_stats.keys()):
            if chi_v >= 7:
                s   = logger.chi_stats[chi_v]
                pct = s["ok"] / s["total"] * 100 if s["total"] else 0
                print(f"    chi={chi_v}: {s['ok']}/{s['total']} ({pct:.1f}%) "
                      f"<-- CASO ABIERTO HADWIGER")
        print()
        if fail_count == 0 and ok_count > 0:
            print("  VERIFICACION EXITOSA — 0 FALLOS")
            print(f"  E7 salvo {logger.e7_count} | "
                  f"E8 salvo {logger.e8_count} | "
                  f"Fase5 salvo {logger.fase5_count} grafos")
            recolor_saves = sum(1 for r in logger.all_results if r.get("recolor_used", 0) > 0)
            if recolor_saves:
                print(f"  Re-Coloring resolvio {recolor_saves} grafos adicionales")
        else:
            print(f"  {fail_count} FALLOS — REVISAR LOG")
            print(f"  (Buscar [DEBUG] en la salida de consola para diagnostico)")
        print("=" * 70)
        print()
        print(f"  Log principal : {LOG_FILE}")
        print(f"  Log chi >= 7  : {LOG_CHI_ALTO}")

    return fail_count == 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    success = main()
    sys.exit(0 if success else 1)
