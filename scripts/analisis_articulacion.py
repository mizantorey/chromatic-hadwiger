"""
ANALISIS: ¿Cuándo todos los vecinos son puntos de articulación?
Mizael Antonio Tovar Reyes — Ciudad Juárez, 2026
CON PROGRESO EN VIVO para PowerShell
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from collections import deque
import networkx as nx

try:
    from core_utils import chromatic_exact, get_optimal_coloring, get_all_graphs
except ImportError:
    print("ERROR: Necesita core_utils.py en el mismo directorio.")
    sys.exit(1)


def build_branch_sets_fase1_2(G, coloring, chi):
    classes = {}
    for v, c in coloring.items():
        classes.setdefault(c, set()).add(v)
    colors = sorted(classes.keys())
    branch_sets = {c: set(classes[c]) for c in colors}

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

    return branch_sets, colors


def analyze_articulation_trap(G, branch_sets, colors):
    node_to_bs = {}
    for c, bs in branch_sets.items():
        for v in bs:
            node_to_bs[v] = c

    traps = []

    for ci in colors:
        subg = G.subgraph(branch_sets[ci])
        if nx.is_connected(subg):
            continue

        all_frontier = []
        for v in branch_sets[ci]:
            for nb in G.neighbors(v):
                cj = node_to_bs.get(nb)
                if cj and cj != ci:
                    remaining = branch_sets[cj] - {nb}
                    if not remaining:
                        continue
                    is_articulation = not nx.is_connected(G.subgraph(remaining))
                    all_frontier.append({
                        "nb": nb,
                        "donor_group": cj,
                        "donor_size": len(branch_sets[cj]),
                        "is_articulation": is_articulation,
                    })

        if not all_frontier:
            traps.append({"group": ci, "reason": "sin vecinos frontera", "frontier": []})
            continue

        robable = [f for f in all_frontier if not f["is_articulation"]]
        articulations = [f for f in all_frontier if f["is_articulation"]]

        if not robable:
            traps.append({
                "group": ci,
                "reason": "TODOS los vecinos son puntos de articulacion",
                "frontier": all_frontier,
                "donor_sizes": [f["donor_size"] for f in articulations]
            })

    return traps


def main():
    print("=" * 60)
    print("  ANALISIS: Trampa de puntos de articulacion?")
    print("=" * 60)
    print("  Cargando grafos...")
    sys.stdout.flush()

    graphs = get_all_graphs(num_random=300, random_seed=2026)
    graphs = [(G, n, f) for G, n, f in graphs if nx.is_connected(G)]
    print(f"  Total grafos cargados: {len(graphs)}")
    print("  Procesando...\n")
    sys.stdout.flush()

    total = 0
    traps_found = 0
    disconnected_groups = 0

    for i, (G, name, familia) in enumerate(graphs):
        n = G.number_of_nodes()
        chi = chromatic_exact(G, max_k=15 if n <= 20 else 10)
        if chi is None or chi < 3:
            continue
        coloring = get_optimal_coloring(G, chi)
        if coloring is None:
            continue

        branch_sets, colors = build_branch_sets_fase1_2(G, coloring, chi)
        total += 1

        for c in colors:
            if not nx.is_connected(G.subgraph(branch_sets[c])):
                disconnected_groups += 1

        traps = analyze_articulation_trap(G, branch_sets, colors)

        if traps:
            traps_found += 1
            for trap in traps:
                print(f"  TRAMPA en [{familia}] {name}  chi={chi}")
                print(f"     Grupo {trap['group']} desconectado")
                print(f"     Razon: {trap['reason']}")
                if trap.get("donor_sizes"):
                    print(f"     Tamanos donantes: {trap['donor_sizes']}")
                sys.stdout.flush()

        # Progreso cada 10 grafos
        if total % 10 == 0:
            print(f"  [{total}/{len(graphs)}] procesados... trampas: {traps_found}")
            sys.stdout.flush()

    print()
    print("=" * 60)
    print(f"  Grafos analizados        : {total}")
    print(f"  Grupos desconectados     : {disconnected_groups}")
    print(f"  Trampas encontradas      : {traps_found}")
    print()
    if traps_found == 0:
        print("  RESULTADO: NINGUNA TRAMPA ENCONTRADA")
        print()
        print("  En todos los grafos probados, cuando un grupo")
        print("  esta desconectado, SIEMPRE existe al menos un")
        print("  vecino frontera que NO es punto de articulacion.")
        print()
        print("  Esto sugiere que la trampa es IMPOSIBLE.")
        print("  Si puedes probar por que, Hadwiger esta resuelto.")
    else:
        print(f"  Se encontraron {traps_found} trampas — revisar arriba.")
    print("=" * 60)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
