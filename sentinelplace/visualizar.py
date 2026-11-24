"""Figuras: la red con los sensores elegidos y la curva de cobertura vs presupuesto."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

COLUMNA_ZONA = {"externa": 0, "DMZ": 1, "usuarios": 2, "nucleo": 2.6,
                "servidores": 3.4, "critica": 4.6}


def posiciones(g: nx.DiGraph) -> dict:
    """Ubica los nodos en columnas por zona, de izquierda (externa) a derecha (critica)."""
    por_columna: dict[float, list] = {}
    for n, d in g.nodes(data=True):
        por_columna.setdefault(COLUMNA_ZONA[d["zona"]], []).append(n)
    pos = {}
    for x, nodos in por_columna.items():
        for i, n in enumerate(nodos):
            pos[n] = (x, (len(nodos) - 1) / 2 - i)
    return pos


def dibujar_red(g: nx.DiGraph, sensores: list[str], titulo: str, archivo: str) -> None:
    pos = posiciones(g)
    colores, bordes = [], []
    for n, d in g.nodes(data=True):
        if d["rol"] == "entrada":
            colores.append("#d9d9d9")
        elif d["rol"] == "objetivo":
            colores.append("#f4b6b6")
        elif n in sensores:
            colores.append("#7fb3e6")
        else:
            colores.append("white")
        bordes.append("#1f5fa8" if n in sensores else "#555555")

    fig, ax = plt.subplots(figsize=(11, 6))
    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#999999", arrowsize=14,
                           node_size=1500, connectionstyle="arc3,rad=0.05")
    nx.draw_networkx_edge_labels(g, pos, ax=ax, font_size=7,
                                 edge_labels={(u, v): f"{d['p']:.1f}" for u, v, d in g.edges(data=True)})
    nx.draw_networkx_nodes(g, pos, ax=ax, node_color=colores, edgecolors=bordes,
                           linewidths=[2.5 if n in sensores else 1 for n in g.nodes], node_size=1500)
    etiquetas = {}
    for n, d in g.nodes(data=True):
        extra = f"\nc={d['costo']}" if d["rol"] == "candidato" else (
            f"\ncrit={d['criticidad']}" if d["rol"] == "objetivo" else "")
        etiquetas[n] = n + extra
    nx.draw_networkx_labels(g, pos, labels=etiquetas, ax=ax, font_size=8)
    ax.set_title(titulo)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(archivo, dpi=150)
    plt.close(fig)


def dibujar_curva(presupuestos: list, z_valores: list, z_total: float, archivo: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.step(presupuestos, [100 * z / z_total for z in z_valores], where="post", marker="o")
    ax.set_xlabel("Presupuesto B (unidades de costo)")
    ax.set_ylabel("Riesgo cubierto (% del peso total de rutas)")
    ax.set_title("Cobertura optima frente a presupuesto")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(archivo, dpi=150)
    plt.close(fig)
