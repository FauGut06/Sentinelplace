"""Generacion automatica de rutas de ataque.

Una ruta es mas probable cuanto mayor es el producto de las probabilidades de
sus aristas. Como log(a*b) = log a + log b, maximizar ese producto equivale a
minimizar la suma de -log(p): asi se pueden usar algoritmos de camino minimo.
"""
import math
from itertools import islice

import networkx as nx


def generar_rutas(g: nx.DiGraph, k: int = 5) -> list[dict]:
    """Devuelve las k rutas mas probables de cada entrada a cada objetivo.

    Peso de cada ruta: w = criticidad del objetivo x probabilidad de la ruta.
    """
    for u, v, datos in g.edges(data=True):
        datos["costo_log"] = -math.log(datos["p"])

    entradas = [n for n, d in g.nodes(data=True) if d["rol"] == "entrada"]
    objetivos = [n for n, d in g.nodes(data=True) if d["rol"] == "objetivo"]

    rutas = []
    for origen in entradas:
        for destino in objetivos:
            if not nx.has_path(g, origen, destino):
                continue
            caminos = nx.shortest_simple_paths(g, origen, destino, weight="costo_log")
            for camino in islice(caminos, k):
                prob = math.prod(g[a][b]["p"] for a, b in zip(camino, camino[1:]))
                rutas.append({
                    "id": f"R{len(rutas) + 1}",
                    "camino": camino,
                    "candidatos": [n for n in camino if g.nodes[n]["rol"] == "candidato"],
                    "probabilidad": prob,
                    "peso": g.nodes[destino]["criticidad"] * prob,
                })
    return rutas
