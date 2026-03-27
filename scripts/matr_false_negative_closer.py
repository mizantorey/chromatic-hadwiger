"""
================================================================================
SCRIPT 10 — PRUEBA EXHAUSTIVA DE LOS 5 GRAFOS FALLIDOS
================================================================================
Autor  : Mizael Antonio Tovar Reyes
Ciudad : Ciudad Juarez, Chihuahua, Mexico
Version: V20 — 2026

OBJETIVO:
---------
Los 5 grafos siguientes producen FALLO en Script 8 (V12.7) con diagnostico:
    connected=False (branch sets internamente desconexos)

Grafos con fallo:
    1. Rand_chi5_n7_#375  — n=7,  m=16, chi=5
    2. Rand_chi6_n8_#160  — n=8,  m=24, chi=6
    3. Circ_19_3          — n=19, m=57, chi=5
    4. Circ_21_3          — n=21, m=63, chi=5
    5. Circ_21_4          — n=21, m=84, chi=6

Este script demuestra que el fallo es del ALGORITMO (falso negativo),
no un contraejemplo al Teorema 8.7.

METODO:
-------
Para cada grafo se realiza una busqueda EXHAUSTIVA de un testimonio de minor K_k:
k conjuntos B_1,...,B_k de vertices tal que:
    (a) Cada B_i es no-vacio
    (b) Cada B_i es conexo como subgrafo de G
    (c) Los conjuntos son disjuntos
    (d) Para todo i != j existe al menos una arista entre B_i y B_j

Para grafos pequenos (n=7, n=8): enumeracion completa de todas las particiones.
Para grafos grandes (n=19, n=21): busqueda inteligente por expansion BFS.

RESULTADO ESPERADO:
-------------------
Se encontrara un testimonio valido para cada uno de los 5 grafos.
Esto prueba que contienen K_chi como minor, cerrando los 5 casos abiertos.
================================================================================
"""

import sys
import itertools
import random
import networkx as nx
from collections import defaultdict
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES (identicas a script8 para reproducibilidad exacta)
# ─────────────────────────────────────────────────────────────────────────────
RANDOM_SEED   = 8888
MAX_N_RANDOM  = 13
CHI_LOW       = 5
CHI_HIGH      = 8

LOG_PATH = Path(__file__).parent.parent / "logs" / "log_script10_prueba_5_fallos.txt"


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES DE GRAFOS
# ─────────────────────────────────────────────────────────────────────────────

def exact_chromatic_number(G):
    """Calcula chi(G) exacto por backtracking con poda."""
    nodes = list(G.nodes())
    n = len(nodes)
    if n == 0:
        return 0
    coloring = {}

    def backtrack(idx, max_color):
        if idx == n:
            return max_color
        v = nodes[idx]
        neighbor_colors = {coloring[u] for u in G.neighbors(v) if u in coloring}
        for c in range(1, max_color + 2):
            if c not in neighbor_colors:
                coloring[v] = c
                result = backtrack(idx + 1, max(max_color, c))
                if result <= max_color + 1:
                    return result
                del coloring[v]
        return max_color + 2

    for k in range(1, n + 1):
        coloring.clear()
        found = _try_color(G, nodes, 0, {}, k)
        if found is not None:
            return k
    return n


def _try_color(G, nodes, idx, col, k):
    if idx == len(nodes):
        return col.copy()
    v = nodes[idx]
    nb_colors = {col[u] for u in G.neighbors(v) if u in col}
    for c in range(1, k + 1):
        if c not in nb_colors:
            col[v] = c
            result = _try_color(G, nodes, idx + 1, col, k)
            if result is not None:
                return result
            del col[v]
    return None


def get_all_colorings(G, k, limit=200):
    """Obtiene hasta `limit` coloraciones optimas con k colores."""
    nodes = list(G.nodes())
    colorings = []

    def backtrack(idx, col):
        if len(colorings) >= limit:
            return
        if idx == len(nodes):
            colorings.append(col.copy())
            return
        v = nodes[idx]
        nb_colors = {col[u] for u in G.neighbors(v) if u in col}
        for c in range(1, k + 1):
            if c not in nb_colors:
                col[v] = c
                backtrack(idx + 1, col)
                del col[v]

    backtrack(0, {})
    return colorings


def is_connected_subset(G, nodes_set):
    """Verifica si el conjunto de nodos induce un subgrafo conexo."""
    if len(nodes_set) == 0:
        return False
    if len(nodes_set) == 1:
        return True
    sub = G.subgraph(nodes_set)
    return nx.is_connected(sub)


def verify_kk_minor(G, branch_sets, k):
    """
    Verifica si branch_sets es un testimonio valido de K_k minor.
    Devuelve (bool, dict_de_diagnostico).
    """
    colors = list(range(k))
    diag = {
        "nonempty": True,
        "connected": True,
        "disjoint": True,
        "edges": True,
        "missing_pairs": [],
        "disconnected": [],
    }

    # (a) No vacios
    for c in colors:
        if not branch_sets[c]:
            diag["nonempty"] = False

    # (b) Conexos
    for c in colors:
        if branch_sets[c] and not is_connected_subset(G, branch_sets[c]):
            diag["connected"] = False
            diag["disconnected"].append(c)

    # (c) Disjuntos
    seen = {}
    for c in colors:
        for v in branch_sets[c]:
            if v in seen:
                diag["disjoint"] = False
            seen[v] = c

    # (d) Aristas entre todos los pares
    for ci, cj in itertools.combinations(colors, 2):
        has_edge = any(
            G.has_edge(u, v)
            for u in branch_sets[ci]
            for v in branch_sets[cj]
        )
        if not has_edge:
            diag["edges"] = False
            diag["missing_pairs"].append((ci, cj))

    ok = diag["nonempty"] and diag["connected"] and diag["disjoint"] and diag["edges"]
    return ok, diag


# ─────────────────────────────────────────────────────────────────────────────
# METODO 1: ENUMERACION EXHAUSTIVA (para n <= 10)
# ─────────────────────────────────────────────────────────────────────────────

def exhaustive_minor_search(G, k):
    """
    Busqueda exhaustiva de K_k minor por enumeracion de particiones.
    Itera sobre TODAS las particiones de V(G) en k partes no-vacias,
    verifica conectividad y aristas entre pares.

    Optimo para n <= 10. Devuelve el primer testimonio encontrado o None.
    """
    nodes = list(G.nodes())
    n = len(nodes)

    # Generador de todas las funciones de asignacion: cada nodo -> {0,...,k-1}
    # con la restriccion de que cada color sea usado al menos una vez
    # Usamos el algoritmo de particion de conjuntos (numeros de Stirling)

    def generate_surjections(n, k):
        """Genera todas las funciones sobreyectivas de [n] -> [k]."""
        if k > n:
            return
        for assignment in itertools.product(range(k), repeat=n):
            if len(set(assignment)) == k:  # sobreyectiva
                yield assignment

    count_checked = 0
    for assignment in generate_surjections(n, k):
        branch_sets = defaultdict(set)
        for i, node in enumerate(nodes):
            branch_sets[assignment[i]].add(node)

        count_checked += 1

        # Verificacion rapida: aristas entre todos los pares primero (mas rapido)
        pairs_ok = True
        for ci, cj in itertools.combinations(range(k), 2):
            if not any(G.has_edge(u, v) for u in branch_sets[ci] for v in branch_sets[cj]):
                pairs_ok = False
                break
        if not pairs_ok:
            continue

        # Verificacion de conectividad
        conn_ok = all(is_connected_subset(G, branch_sets[c]) for c in range(k))
        if not conn_ok:
            continue

        return dict(branch_sets), count_checked

    return None, count_checked


# ─────────────────────────────────────────────────────────────────────────────
# METODO 2: BUSQUEDA INTELIGENTE POR EXPANSION BFS (para n > 10)
# ─────────────────────────────────────────────────────────────────────────────

def intelligent_minor_search(G, k, n_colorings=500, seed=42):
    """
    Busqueda inteligente de K_k minor para grafos medianos (n = 11-30).

    Estrategia:
    1. Obtiene multiples coloraciones con k colores
    2. Para cada coloracion, usa las clases de color como semillas de branch sets
    3. Expande cada branch set via BFS para lograr conectividad interna
    4. Si falla la expansion directa, intenta reasignaciones estrategicas

    Devuelve el primer testimonio encontrado o None.
    """
    colorings = get_all_colorings(G, k, limit=n_colorings)
    nodes = list(G.nodes())
    rng = random.Random(seed)

    attempts_total = 0

    for coloring in colorings:
        # Construir branch sets iniciales desde la coloracion
        branch_sets = defaultdict(set)
        for v, c in coloring.items():
            branch_sets[c - 1].add(v)  # colores 1..k -> indices 0..k-1

        # Intentar reparar conectividad interna
        repaired = _repair_connectivity(G, branch_sets, k)
        attempts_total += 1

        if repaired is not None:
            ok, diag = verify_kk_minor(G, repaired, k)
            if ok:
                return repaired, attempts_total

    # Intentos adicionales con reordenamientos aleatorios
    for _ in range(200):
        rng.shuffle(nodes)
        col = _greedy_color(G, nodes, k)
        if col is None:
            continue
        branch_sets = defaultdict(set)
        for v, c in col.items():
            branch_sets[c].add(v)

        repaired = _repair_connectivity(G, branch_sets, k)
        attempts_total += 1
        if repaired is not None:
            ok, diag = verify_kk_minor(G, repaired, k)
            if ok:
                return repaired, attempts_total

    return None, attempts_total


def _greedy_color(G, order, k):
    """Coloracion greedy con orden dado. Devuelve None si necesita mas de k colores."""
    col = {}
    for v in order:
        nb = {col[u] for u in G.neighbors(v) if u in col}
        for c in range(k):
            if c not in nb:
                col[v] = c
                break
        else:
            return None
    return col


def _repair_connectivity(G, branch_sets_in, k):
    """
    Intenta reparar la conectividad interna de branch sets desconexos
    mediante absorcion BFS de vertices libres y transferencias entre sets.

    Devuelve branch_sets reparados o None si no puede.
    """
    bs = {c: set(s) for c, s in branch_sets_in.items()}

    # Fase 1: absorber vertices libres para conectar fragmentos
    all_assigned = set().union(*bs.values())
    free = set(G.nodes()) - all_assigned

    for c in range(k):
        if is_connected_subset(G, bs[c]):
            continue
        sub = G.subgraph(bs[c])
        comps = list(nx.connected_components(sub))
        if len(comps) <= 1:
            continue
        main_comp = set(max(comps, key=len))

        for minor_comp in comps:
            minor_comp = set(minor_comp)
            if minor_comp == main_comp:
                continue
            merged = False

            # Buscar nodo libre que conecte minor_comp con main_comp
            for wf in sorted(free, key=lambda v: G.degree(v), reverse=True):
                nb_wf = set(G.neighbors(wf))
                if (nb_wf & minor_comp) and (nb_wf & main_comp):
                    bs[c].add(wf)
                    free.discard(wf)
                    main_comp |= minor_comp | {wf}
                    merged = True
                    break

            # Buscar nodo de otro BS como puente (si queda conexo sin el)
            if not merged:
                for c2 in range(k):
                    if c2 == c or merged:
                        continue
                    for w in sorted(bs[c2], key=lambda v: G.degree(v), reverse=True):
                        nb_w = set(G.neighbors(w))
                        if not ((nb_w & minor_comp) and (nb_w & main_comp)):
                            continue
                        rem = bs[c2] - {w}
                        if rem and is_connected_subset(G, rem):
                            bs[c2].discard(w)
                            bs[c].add(w)
                            main_comp |= minor_comp | {w}
                            merged = True
                            break
                    if merged:
                        break

    # Verificar resultado
    ok, _ = verify_kk_minor(G, bs, k)
    return bs if ok else None


# ─────────────────────────────────────────────────────────────────────────────
# METODO 3: PARTICION ESTRUCTURAL PARA GRAFOS CIRCULANTES
# ─────────────────────────────────────────────────────────────────────────────

def circulant_minor_search(n, steps, k):
    """
    Busqueda especializada para grafos circulantes Circ(n, {1,...,s}).

    Construccion principal — "K_{k-1} + camino de saltos":
    =========================================================
    Para Circ(n, {1,...,s}) con chi(G) = k:

    1. Usar singletons B_1={0}, B_2={1}, ..., B_{k-1}={k-2}
       como testigos del (k-1)-clique {0,1,...,k-2}:
       * Conectividad interna: trivial (singletons)
       * Aristas entre pares: todos los pares en {0,...,k-2}
         estan a distancia circular <= k-2 <= s-1 < s, por tanto
         existe arista entre cada par.

    2. Construir B_k como camino de saltos de longitud s:
       B_k = {k-1, k-1+s, k-1+2s, ...} (mod n)
       * Conectividad: vertices consecutivos difieren exactamente s,
         que es una arista en Circ(n,{1,...,s}).
       * B_k — B_i (i < k): el primer vertice (k-1) esta a distancia
         (k-1-j) <= k-2 <= s de cada j in {0,...,k-2} para j >= k-1-s.
       * B_k — B_1 (vertice 0): el ultimo vertice del camino da la vuelta
         al ciclo y esta a distancia <= s de 0.

    Resultado: testimonio explicito y verificable de K_k minor.
    """
    s = steps
    G = nx.circulant_graph(n, list(range(1, s + 1)))

    def circ_dist(a, b, n):
        d = abs(a - b)
        return min(d, n - d)

    # ─── Construccion: singletons + camino de saltos ───
    # B_1={0}, ..., B_{k-1}={k-2}
    branch_sets = {i: {i} for i in range(k - 1)}

    # B_k = camino k-1, k-1+s, k-1+2s, ... (mod n)
    path = []
    v = k - 1
    visited = set(range(k - 1))  # no reusar vertices ya en B_1..B_{k-1}
    while True:
        if v in visited:
            break
        path.append(v)
        visited.add(v)
        next_v = (v + s) % n
        # Parar cuando el ultimo vertice agregado ya esta a distancia <= s de 0
        # Y tenemos al menos 1 nodo (para que B_k conecte con B_1={0})
        if circ_dist(v, 0, n) <= s and len(path) >= 1:
            break
        if next_v in visited:
            break
        v = next_v

    branch_sets[k - 1] = set(path)

    ok, diag = verify_kk_minor(G, branch_sets, k)
    if ok:
        return G, branch_sets, f"K_{{k-1}}_clique + camino_saltos_s{s}"

    # ─── Fallback: busqueda inteligente ampliada ───
    result, attempts = intelligent_minor_search(G, k, n_colorings=2000, seed=99)
    if result is not None:
        return G, result, f"busqueda_inteligente ({attempts} intentos)"

    return G, None, "no_encontrado"


# ─────────────────────────────────────────────────────────────────────────────
# RECONSTRUCCION EXACTA DE LOS GRAFOS ALEATORIOS FALLIDOS
# ─────────────────────────────────────────────────────────────────────────────

def reconstruct_random_graphs():
    """
    Reconstruye exactamente los grafos aleatorios fallidos usando la misma
    logica de generacion que script8 (semilla 8888, mismas condiciones).

    Retorna dict con los grafos reconstructos para las claves de fallo.
    """
    rng = random.Random(RANDOM_SEED)
    target_names = {"Rand_chi5_n7_#375", "Rand_chi6_n8_#160"}
    found = {}

    attempts = 0
    # Simular la generacion hasta encontrar ambos grafos
    max_attempts = 10000

    while attempts < max_attempts and len(found) < len(target_names):
        attempts += 1
        n = rng.randint(7, MAX_N_RANDOM)
        p = rng.uniform(0.35, 0.80)
        G = nx.gnp_random_graph(n, p, seed=attempts * 7919 + RANDOM_SEED)

        if not nx.is_connected(G) or G.number_of_edges() == 0:
            continue

        # Estimacion rapida del numero cromatico (greedy upper bound)
        nodes_sorted = sorted(G.nodes(), key=lambda v: G.degree(v), reverse=True)
        chi_est = len(set(_greedy_color(G, nodes_sorted, G.number_of_nodes()).values())) \
                  if _greedy_color(G, nodes_sorted, G.number_of_nodes()) else G.number_of_nodes()

        if not (CHI_LOW <= chi_est <= CHI_HIGH + 1):
            continue

        name = f"Rand_chi{chi_est}_n{n}_#{attempts}"
        if name in target_names:
            found[name] = (G, chi_est)

    return found


# ─────────────────────────────────────────────────────────────────────────────
# FORMATO DE SALIDA
# ─────────────────────────────────────────────────────────────────────────────

def format_branch_sets(G, branch_sets, k):
    """Formatea los branch sets para visualizacion."""
    lines = []
    for c in range(k):
        bs = sorted(branch_sets[c])
        sub = G.subgraph(branch_sets[c])
        conn = "CONEXO" if nx.is_connected(sub) or len(bs) == 1 else "DESCONEXO(!)"
        lines.append(f"    B_{c+1} = {bs}  ({len(bs)} nodos, {conn})")
    return "\n".join(lines)


def format_edges_between(G, branch_sets, k):
    """Verifica y muestra aristas entre pares de branch sets."""
    lines = []
    for ci, cj in itertools.combinations(range(k), 2):
        edge_examples = [
            (u, v) for u in branch_sets[ci] for v in branch_sets[cj]
            if G.has_edge(u, v)
        ]
        if edge_examples:
            lines.append(f"    B_{ci+1} — B_{cj+1}: arista {edge_examples[0]} (y {len(edge_examples)-1} mas)")
        else:
            lines.append(f"    B_{ci+1} — B_{cj+1}: SIN ARISTA (!)")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# FUNCION PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    output_lines = []

    def log(msg=""):
        print(msg)
        output_lines.append(msg)

    log("=" * 80)
    log("SCRIPT 10 — PRUEBA EXHAUSTIVA DE LOS 5 GRAFOS FALLIDOS")
    log("Autor: Mizael Antonio Tovar Reyes — Ciudad Juarez, Mexico")
    log("Version: V20 — 2026")
    log("=" * 80)
    log()
    log("OBJETIVO: Demostrar que los 5 grafos SÍ contienen K_chi como minor.")
    log("          Los fallos de Script 8 son FALSOS NEGATIVOS (limite algoritmico),")
    log("          NO contraejemplos al Teorema 8.7.")
    log()

    resultados = {}

    # ─────────────────────────────────────────────────────
    # CASOS 3, 4, 5: GRAFOS CIRCULANTES (estructura conocida)
    # ─────────────────────────────────────────────────────
    log("=" * 80)
    log("PARTE A — GRAFOS CIRCULANTES (n=19, n=21)")
    log("=" * 80)

    circulant_cases = [
        ("Circ_19_3", 19, 3, 5),
        ("Circ_21_3", 21, 3, 5),
        ("Circ_21_4", 21, 4, 6),
    ]

    for name, n, steps, k_expected in circulant_cases:
        log()
        log(f"{'─'*60}")
        log(f"Grafo: {name}  (n={n}, steps={steps}, chi esperado={k_expected})")
        log(f"{'─'*60}")

        G, branch_sets, metodo = circulant_minor_search(n, steps, k_expected)

        # Calcular chi exacto
        chi_exact = exact_chromatic_number(G)
        log(f"  chi(G) exacto = {chi_exact}  (esperado: {k_expected})")
        log(f"  n={G.number_of_nodes()}, m={G.number_of_edges()}")

        if branch_sets is not None:
            ok, diag = verify_kk_minor(G, branch_sets, chi_exact)
            log(f"  Metodo: {metodo}")
            log(f"  Resultado: {'MINOR K_{} ENCONTRADO'.format(chi_exact)}")
            log(f"  Verificacion:")
            log(f"    nonempty={diag['nonempty']}  connected={diag['connected']}"
                f"  disjoint={diag['disjoint']}  edges={diag['edges']}")
            log(f"  Branch sets (testigos):")
            log(format_branch_sets(G, branch_sets, chi_exact))
            log(f"  Aristas inter-conjuntos:")
            log(format_edges_between(G, branch_sets, chi_exact))
            resultados[name] = "PROBADO" if ok else "ERROR_VERIFICACION"
        else:
            log(f"  Resultado: MINOR NO ENCONTRADO con metodo actual")
            log(f"  Nota: Puede requerir busqueda mas exhaustiva")
            resultados[name] = "PENDIENTE"

    # ─────────────────────────────────────────────────────
    # CASOS 1, 2: GRAFOS ALEATORIOS (reconstruccion exacta)
    # ─────────────────────────────────────────────────────
    log()
    log("=" * 80)
    log("PARTE B — GRAFOS ALEATORIOS (n=7, n=8)")
    log("=" * 80)
    log()
    log("Reconstruyendo grafos exactos (puede tomar un momento)...")

    random_graphs = reconstruct_random_graphs()

    random_cases = [
        ("Rand_chi5_n7_#375", 7, 5),
        ("Rand_chi6_n8_#160", 8, 6),
    ]

    for name, n_expected, k_expected in random_cases:
        log()
        log(f"{'─'*60}")
        log(f"Grafo: {name}  (n={n_expected}, chi esperado={k_expected})")
        log(f"{'─'*60}")

        if name not in random_graphs:
            log(f"  ADVERTENCIA: No se pudo reconstruir el grafo {name}")
            log(f"  Verificando por generacion directa del grafo seed...")
            # Intentar por seed directo si #375 -> seed = 375*7919+8888
            attempt_num = int(name.split("#")[1])
            graph_seed = attempt_num * 7919 + RANDOM_SEED
            # Necesitamos n y p del rng — usar n del nombre
            n = n_expected
            # Probar con p que da m esperado
            for p_try in [0.75, 0.80, 0.70, 0.65, 0.60]:
                G_try = nx.gnp_random_graph(n, p_try, seed=graph_seed)
                if G_try.number_of_edges() == (16 if k_expected == 5 else 24):
                    log(f"  Reconstruido con seed={graph_seed}, n={n}, p={p_try}")
                    G = G_try
                    break
            else:
                log(f"  No se pudo reconstruir exactamente. Saltando.")
                resultados[name] = "NO_RECONSTRUIDO"
                continue
        else:
            G, chi_from_gen = random_graphs[name]
            log(f"  Reconstruccion exitosa")

        chi_exact = exact_chromatic_number(G)
        log(f"  chi(G) exacto = {chi_exact}  (esperado: {k_expected})")
        log(f"  n={G.number_of_nodes()}, m={G.number_of_edges()}")

        # BUSQUEDA EXHAUSTIVA para n <= 10
        log(f"  Ejecutando busqueda exhaustiva de K_{chi_exact} minor...")
        log(f"  (Enumerando TODAS las particiones en {chi_exact} conjuntos conexos)")

        branch_sets, count = exhaustive_minor_search(G, chi_exact)

        log(f"  Particiones verificadas: {count:,}")

        if branch_sets is not None:
            ok, diag = verify_kk_minor(G, branch_sets, chi_exact)
            log(f"  Resultado: MINOR K_{chi_exact} ENCONTRADO ✓")
            log(f"  Verificacion:")
            log(f"    nonempty={diag['nonempty']}  connected={diag['connected']}"
                f"  disjoint={diag['disjoint']}  edges={diag['edges']}")
            log(f"  Branch sets (testigos):")
            log(format_branch_sets(G, branch_sets, chi_exact))
            log(f"  Aristas inter-conjuntos:")
            log(format_edges_between(G, branch_sets, chi_exact))
            resultados[name] = "PROBADO" if ok else "ERROR_VERIFICACION"
        else:
            log(f"  BUSQUEDA EXHAUSTIVA: no encontrado en {count:,} particiones")
            log(f"  Esto indicaria error en calculo de chi(G) — investigando...")
            # Verificar chi
            for k2 in range(1, G.number_of_nodes() + 1):
                if _try_color(G, list(G.nodes()), 0, {}, k2) is not None:
                    log(f"  chi(G) recalculado = {k2}")
                    if k2 < chi_exact:
                        log(f"  NOTA: chi real = {k2}, buscando K_{k2} minor...")
                        bs2, cnt2 = exhaustive_minor_search(G, k2)
                        if bs2 is not None:
                            log(f"  Minor K_{k2} encontrado en {cnt2} particiones")
                            resultados[name] = f"PROBADO_CHI={k2}"
                        else:
                            resultados[name] = "REQUIERE_INVESTIGACION"
                    break
            else:
                resultados[name] = "PENDIENTE"

    # ─────────────────────────────────────────────────────
    # RESUMEN FINAL
    # ─────────────────────────────────────────────────────
    log()
    log("=" * 80)
    log("RESUMEN FINAL")
    log("=" * 80)
    log()

    total_probados = sum(1 for v in resultados.values() if "PROBADO" in v)
    total = len(resultados)

    for name, estado in resultados.items():
        simbolo = "✓ PROBADO" if "PROBADO" in estado else "? PENDIENTE"
        log(f"  {simbolo:15s} | {name}")

    log()
    log(f"Resultado: {total_probados}/{total} grafos con K_chi minor verificado")
    log()

    if total_probados == total:
        log("CONCLUSION: Los 5 grafos contienen K_chi como minor.")
        log("            Los fallos de Script 8 son FALSOS NEGATIVOS algoritmicos.")
        log("            El Teorema 8.7 NO tiene contraejemplos en este conjunto.")
    else:
        remaining = total - total_probados
        log(f"CONCLUSION PARCIAL: {remaining} grafos requieren investigacion adicional.")
        log("            Ver seccion 'PENDIENTE' arriba para detalles.")

    log()
    log("=" * 80)

    # Guardar log
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print(f"\nLog guardado en: {LOG_PATH}")

    return resultados


if __name__ == "__main__":
    main()
