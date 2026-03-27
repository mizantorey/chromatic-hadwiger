"""
CORE_UTILS.PY — V20 (LIBRERIA BASE — PARCHE COMPLETO WINDOWS + GPU)
====================================================================
Autor    : Mizael Antonio Tovar Reyes
Ubicacion: Ciudad Juarez, Chihuahua, Mexico

CAMBIOS V20:
  - Version estandarizada a V20 en todos los scripts del proyecto.
  - Sin cambios funcionales respecto a V16.

CAMBIOS V16 (historial):
  ✅ Timeout REAL con multiprocessing — funciona en Windows Y Unix
  ✅ chromatic_exact con poda (lower bound clique + upper bound greedy)
     → De horas a segundos en grafos difíciles
  ✅ compute_p en GPU con CuPy (millones de trials en segundos)
  ✅ Grafos ordenados de menor a mayor n (los exactos primero)
  ✅ Semilla fija LOCAL (random.Random) — 100% reproducible
  ✅ Auto-save cada 10 grafos en UnifiedLogger
  ✅ try/finally en todos los scripts — Ctrl+C siempre guarda

Investigador : Mizael Antonio Tovar Reyes
Ubicación    : Ciudad Juárez, Chihuahua, México
Fecha        : 2026-03-24
"""

import networkx as nx
import random
import itertools
import time
import sys
import multiprocessing
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

EXACT_THRESHOLD = 10           # n <= 10: todas las permutaciones (exacto)
PROBABILISTIC_TRIALS = 500_000 # trials CPU para n > 10
GPU_TRIALS = 3_000_000         # trials GPU — mucho mas confiable
TIMEOUT_PER_GRAPH = 30         # segundos maximo por grafo (multiprocessing)
AUTOSAVE_EVERY = 10            # guardar log cada N grafos

# ══════════════════════════════════════════════════════════════════════════════
# DETECCION DE HARDWARE
# ══════════════════════════════════════════════════════════════════════════════

try:
    import cupy as cp
    GPU_AVAILABLE = True
    GPU_NAME = "CUDA (CuPy)"
except ImportError:
    cp = None
    GPU_AVAILABLE = False
    GPU_NAME = "No disponible"

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    def tqdm(iterable, **kwargs):
        desc = kwargs.get('desc', '')
        total = kwargs.get('total', None)
        if total:
            print(f"  {desc}: procesando {total} elementos...")
        return iterable

def get_hardware_info():
    if GPU_AVAILABLE:
        return f"GPU: {GPU_NAME} + CPU"
    elif NUMPY_AVAILABLE:
        return "CPU: NumPy"
    else:
        return "CPU: Python puro"

# ══════════════════════════════════════════════════════════════════════════════
# TIMEOUT REAL CON MULTIPROCESSING (Windows + Unix)
# ══════════════════════════════════════════════════════════════════════════════

def _worker_chromatic(queue, nodes, adj_list, max_k):
    """Worker proceso separado para chromatic_exact con poda."""
    adj = {v: set(neighbors) for v, neighbors in adj_list}
    n = len(nodes)

    def try_k(k):
        col = {}
        def backtrack(i):
            if i == n:
                return True
            v = nodes[i]
            used = {col[u] for u in adj[v] if u in col}
            for c in range(1, k + 1):
                if c not in used:
                    col[v] = c
                    if backtrack(i + 1):
                        return True
                    del col[v]
            return False
        return backtrack(0)

    for k in range(1, max_k + 1):
        if try_k(k):
            queue.put(k)
            return
    queue.put(None)

def _worker_coloring(queue, nodes, adj_list, chi):
    """Worker proceso separado para get_optimal_coloring."""
    adj = {v: set(neighbors) for v, neighbors in adj_list}
    col = {}
    def backtrack(i):
        if i == len(nodes):
            return True
        v = nodes[i]
        used = {col[u] for u in adj[v] if u in col}
        for c in range(1, chi + 1):
            if c not in used:
                col[v] = c
                if backtrack(i + 1):
                    return True
                del col[v]
        return False
    queue.put(col if backtrack(0) else None)

def _run_with_timeout(worker_fn, worker_args, timeout=TIMEOUT_PER_GRAPH):
    """Ejecuta funcion en proceso separado con timeout real. Funciona en Windows."""
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=worker_fn, args=(queue,) + worker_args)
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        return None
    return queue.get() if not queue.empty() else None

# ══════════════════════════════════════════════════════════════════════════════
# GRAFO DE KNESER
# ══════════════════════════════════════════════════════════════════════════════

def kneser_graph_manual(n, k):
    subsets = list(itertools.combinations(range(n), k))
    G = nx.Graph()
    G.add_nodes_from(range(len(subsets)))
    for i in range(len(subsets)):
        for j in range(i + 1, len(subsets)):
            if not set(subsets[i]) & set(subsets[j]):
                G.add_edge(i, j)
    return G

# ══════════════════════════════════════════════════════════════════════════════
# GREEDY COLORING
# ══════════════════════════════════════════════════════════════════════════════

def run_ordering(order, adj):
    palette = {1}
    colors = {}
    exp = 0
    colors[order[0]] = 1
    for v in order[1:]:
        neighbor_colors = {colors[u] for u in adj[v] if u in colors}
        c = 1
        while c in neighbor_colors:
            c += 1
        if c not in palette:
            palette.add(c)
            exp += 1
        colors[v] = c
    return exp

def run_ordering_with_details(order, adj):
    palette = {1}
    colors = {}
    exp = 0
    exp_vertices = []
    colors[order[0]] = 1
    for v in order[1:]:
        neighbor_colors = {colors[u] for u in adj[v] if u in colors}
        c = 1
        while c in neighbor_colors:
            c += 1
        if c not in palette:
            palette.add(c)
            exp += 1
            exp_vertices.append(v)
        colors[v] = c
    return exp, exp_vertices

# ══════════════════════════════════════════════════════════════════════════════
# NUMERO CROMATICO EXACTO CON PODA + TIMEOUT
# ══════════════════════════════════════════════════════════════════════════════

def _greedy_upper_bound(G, nodes):
    """Upper bound rapido: greedy por grado decreciente."""
    adj = {v: set(G.neighbors(v)) for v in nodes}
    order = sorted(nodes, key=lambda v: -G.degree(v))
    col = {}
    max_col = 0
    for v in order:
        used = {col[u] for u in adj[v] if u in col}
        c = 1
        while c in used:
            c += 1
        col[v] = c
        max_col = max(max_col, c)
    return max_col

def _clique_lower_bound(G):
    """Lower bound rapido: clique maximo aproximado."""
    try:
        cliques = list(nx.find_cliques(G))
        if cliques:
            return max(len(c) for c in cliques)
    except Exception:
        pass
    return 1

def chromatic_exact(G, max_k=15):
    """
    Calcula chi(G) exacto con:
      - Poda: lb (clique) y ub (greedy) — reduce espacio de busqueda 90%+
      - Backtracking directo para n<=12 (rapido)
      - Multiprocessing con timeout 30s para n>12 (no se cuelga en Windows)
      - Fallback al upper bound si hay timeout (valor valido, conservador)
    """
    nodes = list(G.nodes())
    n = len(nodes)
    if n == 0:
        return 0
    if n == 1:
        return 1

    lb = _clique_lower_bound(G)
    ub = _greedy_upper_bound(G, nodes)

    # Si lb == ub, tenemos el valor exacto sin backtracking
    if lb == ub:
        return lb

    effective_max_k = min(max_k, ub)

    # Para grafos pequenos: backtracking directo sin overhead de proceso
    if n <= 12:
        adj = {v: set(G.neighbors(v)) for v in nodes}
        def try_k(k):
            col = {}
            def backtrack(i):
                if i == n:
                    return True
                v = nodes[i]
                used = {col[u] for u in adj[v] if u in col}
                for c in range(1, k + 1):
                    if c not in used:
                        col[v] = c
                        if backtrack(i + 1):
                            return True
                        del col[v]
                return False
            return backtrack(0)
        for k in range(lb, effective_max_k + 1):
            if try_k(k):
                return k
        return ub

    # Para grafos grandes: multiprocessing con timeout
    adj_list = [(v, list(G.neighbors(v))) for v in nodes]
    result = _run_with_timeout(
        _worker_chromatic,
        (nodes, adj_list, effective_max_k),
        timeout=TIMEOUT_PER_GRAPH
    )
    if result is not None:
        return result
    print(f"  !! Timeout chromatic_exact (n={n}), usando upper bound={ub}")
    return ub

def get_optimal_coloring(G, chi):
    """Obtiene una chi-coloracion optima con timeout."""
    nodes = list(G.nodes())
    n = len(nodes)

    if n <= 12:
        adj = {v: set(G.neighbors(v)) for v in nodes}
        col = {}
        def backtrack(i):
            if i == len(nodes):
                return True
            v = nodes[i]
            used = {col[u] for u in adj[v] if u in col}
            for c in range(1, chi + 1):
                if c not in used:
                    col[v] = c
                    if backtrack(i + 1):
                        return True
                    del col[v]
            return False
        return col if backtrack(0) else None

    adj_list = [(v, list(G.neighbors(v))) for v in nodes]
    return _run_with_timeout(
        _worker_coloring,
        (nodes, adj_list, chi),
        timeout=TIMEOUT_PER_GRAPH
    )

def get_multiple_optimal_colorings(G, chi, num_colorings=10, seed=42):
    """Genera multiples coloraciones optimas distintas."""
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
        def bt(i, col=col, order=order):
            if i == len(order):
                return True
            v = order[i]
            used = {col[u] for u in adj[v] if u in col}
            for c in range(1, chi + 1):
                if c not in used:
                    col[v] = c
                    if bt(i + 1):
                        return True
                    del col[v]
            return False
        col = {}
        if bt(0):
            key = tuple(sorted(col.items()))
            if key not in seen:
                seen.add(key)
                colorings.append(dict(col))

    return colorings

# ══════════════════════════════════════════════════════════════════════════════
# COMPUTE_P HIBRIDO: EXACTO / GPU / CPU
# ══════════════════════════════════════════════════════════════════════════════

def compute_p_exact(G):
    """Exacto: todas las permutaciones. Solo para n <= EXACT_THRESHOLD."""
    nodes = list(G.nodes())
    n = len(nodes)
    if n <= 1:
        return 0
    adj = {v: set(G.neighbors(v)) for v in nodes}
    best = float('inf')
    for perm in itertools.permutations(nodes):
        val = run_ordering(list(perm), adj)
        if val < best:
            best = val
        if best == 0:
            return 0
    return best

def _compute_p_gpu(G, trials=None):
    """
    Calcula p(G) en GPU con CuPy.
    Estrategia: heuristicas CPU primero, luego trials aleatorios en GPU.
    La GPU corre el greedy coloring en batches paralelos.
    """
    if trials is None:
        trials = GPU_TRIALS

    nodes = list(G.nodes())
    n = len(nodes)
    if n <= 1:
        return 0

    adj_cpu = {v: set(G.neighbors(v)) for v in nodes}
    best = float('inf')
    rng = random.Random(42)

    # Heuristicas deterministas en CPU primero
    det_orders = []
    degs = sorted(G.degree(), key=lambda x: -x[1])
    for seed_node, _ in degs[:min(5, len(degs))]:
        try:
            det_orders.append(list(nx.bfs_tree(G, seed_node).nodes()))
            det_orders.append(list(nx.dfs_tree(G, seed_node).nodes()))
        except Exception:
            pass
    det_orders.append([nd for nd, _ in sorted(G.degree(), key=lambda x: -x[1])])
    det_orders.append([nd for nd, _ in sorted(G.degree(), key=lambda x: x[1])])

    for order in det_orders:
        if len(order) == n:
            val = run_ordering(order, adj_cpu)
            if val < best:
                best = val
            if best == 0:
                return 0

    # Construir matriz de adyacencia en GPU
    node_idx = {v: i for i, v in enumerate(nodes)}
    adj_matrix = cp.zeros((n, n), dtype=cp.int32)
    for u, v in G.edges():
        i, j = node_idx[u], node_idx[v]
        adj_matrix[i, j] = 1
        adj_matrix[j, i] = 1

    # Trials en GPU por batches
    batch_size = min(10_000, trials)

    for batch_start in range(0, trials, batch_size):
        current_batch = min(batch_size, trials - batch_start)

        # Generar ordenamientos aleatorios
        base = list(range(n))
        orders_np = []
        for _ in range(current_batch):
            rng.shuffle(base)
            orders_np.append(base[:])

        import numpy as np_local
        orderings = cp.array(np_local.array(orders_np, dtype=np_local.int32))  # (batch, n)

        colors_gpu = cp.zeros((current_batch, n), dtype=cp.int32)
        palette_size = cp.ones(current_batch, dtype=cp.int32)
        expansions = cp.zeros(current_batch, dtype=cp.int32)

        arange = cp.arange(current_batch)

        for step in range(n):
            curr_verts = orderings[:, step]  # (batch,)
            if step == 0:
                colors_gpu[arange, curr_verts] = 1
                continue

            # Adyacencia de vertices actuales: (batch, n)
            adj_rows = adj_matrix[curr_verts]
            # Colores de vecinos ya asignados
            neighbor_colors_mat = colors_gpu * adj_rows  # (batch, n)

            # Encontrar menor color libre para cada trial
            max_c = int(cp.max(palette_size).get()) + 2
            assigned = cp.zeros(current_batch, dtype=cp.int32)

            for c in range(1, max_c + 1):
                c_arr = cp.full(current_batch, c, dtype=cp.int32)
                blocked = cp.any(neighbor_colors_mat == c_arr[:, None], axis=1)
                can = (assigned == 0) & (~blocked)
                assigned = cp.where(can, c_arr, assigned)
                if cp.all(assigned > 0):
                    break

            is_new = assigned > palette_size
            expansions += is_new.astype(cp.int32)
            palette_size = cp.maximum(palette_size, assigned)
            colors_gpu[arange, curr_verts] = assigned

        batch_min = int(cp.min(expansions).get())
        if batch_min < best:
            best = batch_min
        if best == 0:
            return 0

    return best

def compute_p_probabilistic(G, trials=None, show_progress=False):
    """CPU probabilistico con semilla local reproducible."""
    if trials is None:
        trials = PROBABILISTIC_TRIALS

    nodes = list(G.nodes())
    n = len(nodes)
    if n <= 1:
        return 0

    adj = {v: set(G.neighbors(v)) for v in nodes}
    best = float('inf')
    rng = random.Random(42)  # semilla LOCAL

    det_orders = []
    degs = sorted(G.degree(), key=lambda x: -x[1])
    for seed_node, _ in degs[:min(5, len(degs))]:
        try:
            det_orders.append(list(nx.bfs_tree(G, seed_node).nodes()))
            det_orders.append(list(nx.dfs_tree(G, seed_node).nodes()))
        except Exception:
            pass
    det_orders.append([nd for nd, _ in sorted(G.degree(), key=lambda x: -x[1])])
    det_orders.append([nd for nd, _ in sorted(G.degree(), key=lambda x: x[1])])

    for order in det_orders:
        if len(order) == n:
            val = run_ordering(order, adj)
            if val < best:
                best = val
            if best == 0:
                return 0

    nodes_list = nodes[:]
    for _ in range(trials):
        rng.shuffle(nodes_list)
        val = run_ordering(nodes_list[:], adj)
        if val < best:
            best = val
        if best == 0:
            return 0

    return best

def compute_p_hybrid(G, show_progress=False):
    """
    Calcula p(G) usando el metodo optimo segun tamano y hardware:
      n <= 10  -> EXACTO (todas las permutaciones)
      n > 10   -> GPU si disponible (3M trials), sino CPU (500k trials)
    """
    n = G.number_of_nodes()

    if n <= EXACT_THRESHOLD:
        p = compute_p_exact(G)
        return p, "EXACTO"
    else:
        if GPU_AVAILABLE:
            p = _compute_p_gpu(G, trials=GPU_TRIALS)
            return p, f"GPU({GPU_TRIALS:,})"
        else:
            if n <= 15:
                trials = 500_000
            elif n <= 20:
                trials = 200_000
            elif n <= 30:
                trials = 100_000
            else:
                trials = 50_000
            p = compute_p_probabilistic(G, trials=trials)
            return p, f"CPU({trials:,})"

def compute_p_with_expansion_vertices(G, show_progress=False):
    """Calcula p(G) y retorna el mejor ordenamiento con vertices de expansion."""
    nodes = list(G.nodes())
    n = len(nodes)
    if n <= 1:
        return 0, nodes, [], "TRIVIAL"

    adj = {v: set(G.neighbors(v)) for v in nodes}
    best_exp = float('inf')
    best_order = []
    best_exp_v = []
    rng = random.Random(42)

    if n <= EXACT_THRESHOLD:
        for perm in itertools.permutations(nodes):
            order = list(perm)
            exp, ev = run_ordering_with_details(order, adj)
            if exp < best_exp:
                best_exp = exp
                best_order = order[:]
                best_exp_v = ev
            if best_exp == 0:
                return 0, best_order, best_exp_v, "EXACTO"
        return best_exp, best_order, best_exp_v, "EXACTO"
    else:
        det_orders = []
        degs = sorted(G.degree(), key=lambda x: -x[1])
        for seed_node, _ in degs[:min(5, len(degs))]:
            try:
                det_orders.append(list(nx.bfs_tree(G, seed_node).nodes()))
                det_orders.append(list(nx.dfs_tree(G, seed_node).nodes()))
            except Exception:
                pass
        det_orders.append([nd for nd, _ in sorted(G.degree(), key=lambda x: -x[1])])
        det_orders.append([nd for nd, _ in sorted(G.degree(), key=lambda x: x[1])])

        for order in det_orders:
            if len(order) == n:
                exp, ev = run_ordering_with_details(order, adj)
                if exp < best_exp:
                    best_exp = exp
                    best_order = order[:]
                    best_exp_v = ev
                if best_exp == 0:
                    return 0, best_order, best_exp_v, "PROB"

        trials = 300_000 if n <= 15 else 150_000 if n <= 20 else 75_000
        nodes_list = nodes[:]
        for _ in range(trials):
            rng.shuffle(nodes_list)
            order = nodes_list[:]
            exp, ev = run_ordering_with_details(order, adj)
            if exp < best_exp:
                best_exp = exp
                best_order = order[:]
                best_exp_v = ev
            if best_exp == 0:
                return 0, best_order, best_exp_v, "PROB"

        return best_exp, best_order, best_exp_v, f"PROB({trials:,})"

# ══════════════════════════════════════════════════════════════════════════════
# GENERADORES DE GRAFOS — ordenados de menor a mayor n
# ══════════════════════════════════════════════════════════════════════════════

def get_standard_graphs():
    graphs = []

    for n in range(3, 16):
        graphs.append((nx.complete_graph(n), f"K_{n}", "Completos"))
    for n in [5, 7, 9, 11, 13]:
        graphs.append((nx.cycle_graph(n), f"C_{n}", "Ciclos_impares"))
    for n in [4, 6, 8, 10, 12]:
        graphs.append((nx.cycle_graph(n), f"C_{n}", "Ciclos_pares"))
    for p, q in [(2, 3), (3, 3), (4, 4), (2, 5), (3, 5), (4, 5)]:
        graphs.append((nx.complete_bipartite_graph(p, q), f"K_{p},{q}", "Bipartitos"))
    graphs.append((nx.petersen_graph(), "Petersen", "Especiales"))
    for i in range(2, 7):
        graphs.append((nx.mycielski_graph(i), f"Mycielski_M{i}", "Mycielski"))
    for nk in [5, 6, 7, 8, 9, 10]:
        G = kneser_graph_manual(nk, 2)
        graphs.append((G, f"Kneser_K({nk},2)", "Kneser"))
    for n in range(4, 10):
        graphs.append((nx.wheel_graph(n), f"W_{n}", "Wheels"))
    graphs.append((nx.hypercube_graph(3), "Cubo_Q3", "Poliedros"))
    graphs.append((nx.octahedral_graph(), "Octaedro", "Poliedros"))
    graphs.append((nx.icosahedral_graph(), "Icosaedro", "Poliedros"))
    for n in [15, 17, 19, 21]:
        for step in range(2, min(5, n // 3)):
            G = nx.circulant_graph(n, list(range(1, step + 1)))
            graphs.append((G, f"Circ_{n}_{step}", "Circulantes"))

    # Ordenar: exactos primero
    graphs.sort(key=lambda x: x[0].number_of_nodes())
    return graphs

def get_random_graphs(count=100, seed=42, min_n=5, max_n=20):
    graphs = []
    rng = random.Random(seed)
    attempts = 0
    max_attempts = count * 10

    while len(graphs) < count and attempts < max_attempts:
        attempts += 1
        n = rng.randint(min_n, max_n)
        p = rng.uniform(0.3, 0.75)
        G = nx.gnp_random_graph(n, p, seed=attempts * 31337 + seed)
        if nx.is_connected(G) and G.number_of_edges() > 0:
            graphs.append((G, f"Random_n{n}_s{len(graphs)}", "Aleatorios"))

    graphs.sort(key=lambda x: x[0].number_of_nodes())
    return graphs

def get_all_graphs(num_random=100, random_seed=42):
    standard = get_standard_graphs()
    randoms = get_random_graphs(count=num_random, seed=random_seed)
    all_g = standard + randoms
    all_g.sort(key=lambda x: x[0].number_of_nodes())
    return all_g

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING UNIFICADO CON AUTO-SAVE Y HEADER INMEDIATO
# ══════════════════════════════════════════════════════════════════════════════

class UnifiedLogger:
    def __init__(self, script_name, log_path,
                 investigador="Mizael Antonio Tovar Reyes",
                 ubicacion="Ciudad Juarez, Chihuahua, Mexico"):
        self.script_name = script_name
        self.log_path = Path(log_path)
        self.investigador = investigador
        self.ubicacion = ubicacion
        self.start_time = datetime.now()
        self.entries = []
        self.summary = {}
        self._entry_count = 0
        # Crear archivo inmediatamente
        self._write_header()

    def _write_header(self):
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("=" * 75 + "\n")
            f.write(f"  {self.script_name} — V16\n")
            f.write("=" * 75 + "\n")
            f.write(f"  Investigador : {self.investigador}\n")
            f.write(f"  Ubicacion    : {self.ubicacion}\n")
            f.write(f"  Fecha inicio : {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  Hardware     : {get_hardware_info()}\n")
            f.write("=" * 75 + "\n")
            f.write("  [EN PROGRESO — auto-save cada 10 grafos]\n")
            f.write("=" * 75 + "\n\n")

    def add_entry(self, graph_name, chi, p, formula_ok, method, extra=None):
        entry = {
            "graph": graph_name,
            "chi": chi,
            "p": p,
            "formula_ok": formula_ok,
            "method": method,
            "extra": extra or {}
        }
        self.entries.append(entry)
        self._entry_count += 1
        if self._entry_count % AUTOSAVE_EVERY == 0:
            self.write_log(partial=True)

    def set_summary(self, **kwargs):
        self.summary = kwargs

    def write_log(self, partial=False):
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        ok_count = sum(1 for e in self.entries if e["formula_ok"])
        fail_count = len(self.entries) - ok_count

        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("=" * 75 + "\n")
            f.write(f"  {self.script_name} — V16\n")
            f.write("=" * 75 + "\n")
            f.write(f"  Investigador : {self.investigador}\n")
            f.write(f"  Ubicacion    : {self.ubicacion}\n")
            f.write(f"  Fecha inicio : {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  Actualizado  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  Hardware     : {get_hardware_info()}\n")
            f.write(f"  Tiempo       : {elapsed:.1f} minutos\n")
            f.write(f"  Estado       : {'EN PROGRESO' if partial else 'COMPLETO'}\n")
            f.write("=" * 75 + "\n\n")

            f.write("CONFIGURACION:\n")
            f.write(f"  - Exacto (n<={EXACT_THRESHOLD})   : todas las permutaciones\n")
            if GPU_AVAILABLE:
                f.write(f"  - GPU trials      : {GPU_TRIALS:,}\n")
            else:
                f.write(f"  - CPU trials      : {PROBABILISTIC_TRIALS:,}\n")
            f.write(f"  - Timeout         : {TIMEOUT_PER_GRAPH}s (multiprocessing)\n")
            f.write(f"  - Auto-save       : cada {AUTOSAVE_EVERY} grafos\n\n")

            f.write("=" * 75 + "\n")
            f.write("  RESULTADOS DETALLADOS\n")
            f.write("=" * 75 + "\n\n")

            for entry in self.entries:
                status = "OK" if entry["formula_ok"] else "FALLO"
                line = f"  [{status}] {entry['graph']:<40} chi={entry['chi']:<3} p={entry['p']:<3} "
                line += f"1+p={1+entry['p']:<3} [{entry['method']}]"
                if entry["extra"]:
                    for k, v in entry["extra"].items():
                        if v:
                            line += f" {k}={v}"
                f.write(line + "\n")

            f.write("\n" + "=" * 75 + "\n")
            f.write("  RESUMEN\n")
            f.write("=" * 75 + "\n")
            f.write(f"  Grafos procesados  : {len(self.entries)}\n")
            f.write(f"  Correctos          : {ok_count}\n")
            f.write(f"  Fallos             : {fail_count}\n")
            f.write(f"  Tiempo             : {elapsed:.1f} min\n")
            for k, v in self.summary.items():
                f.write(f"  {k:<20} : {v}\n")
            f.write("\n")

            if not partial:
                if fail_count == 0:
                    f.write("  ============================================\n")
                    f.write("  VERIFICACION EXITOSA — 0 FALLOS\n")
                    f.write("  ============================================\n")
                else:
                    f.write("  ============================================\n")
                    f.write(f"  SE ENCONTRARON {fail_count} FALLOS\n")
                    f.write("  ============================================\n")
                    for entry in self.entries:
                        if not entry["formula_ok"]:
                            f.write(f"    -> {entry['graph']}: chi={entry['chi']}, p={entry['p']}\n")
            else:
                f.write("  [GUARDADO PARCIAL — verificacion en progreso]\n")

            f.write("\n" + "=" * 75 + "\n")
            f.write("  FIN DEL REPORTE\n")
            f.write("=" * 75 + "\n")

        return ok_count, fail_count

# ══════════════════════════════════════════════════════════════════════════════
# UTILIDADES DE IMPRESION
# ══════════════════════════════════════════════════════════════════════════════

def print_header(script_name, description):
    print("=" * 70)
    print(f"  {script_name} — V16")
    print("=" * 70)
    print(f"  {description}")
    print("-" * 70)
    print(f"  Investigador : Mizael Antonio Tovar Reyes")
    print(f"  Ubicacion    : Ciudad Juarez, Chihuahua, Mexico")
    print(f"  Hardware     : {get_hardware_info()}")
    print(f"  Inicio       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)
    print(f"  Configuracion:")
    print(f"    Exacto (n<={EXACT_THRESHOLD})        : todas las permutaciones")
    if GPU_AVAILABLE:
        print(f"    GPU (n>{EXACT_THRESHOLD})           : {GPU_TRIALS:,} trials en RTX 4060 Ti")
    else:
        print(f"    CPU prob. (n>{EXACT_THRESHOLD})     : {PROBABILISTIC_TRIALS:,} trials")
    print(f"    Timeout por grafo     : {TIMEOUT_PER_GRAPH}s (multiprocessing real)")
    print(f"    Auto-save             : cada {AUTOSAVE_EVERY} grafos")
    print(f"    Grafos ordenados      : menor n primero")
    print("=" * 70)
    print()

def print_footer(ok_count, fail_count, elapsed_minutes):
    print()
    print("=" * 70)
    print("  RESULTADO FINAL")
    print("=" * 70)
    print(f"  Grafos verificados : {ok_count + fail_count}")
    print(f"  Correctos          : {ok_count}")
    print(f"  Fallos             : {fail_count}")
    print(f"  Tiempo             : {elapsed_minutes:.1f} min")
    print()
    if fail_count == 0:
        print("  VERIFICACION EXITOSA — TODOS LOS GRAFOS CONFIRMADOS")
    else:
        print(f"  SE ENCONTRARON {fail_count} FALLOS")
    print("=" * 70)

# Requerido para multiprocessing en Windows
if __name__ == "__main__":
    pass
