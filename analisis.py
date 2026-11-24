"""Analisis complementarios del informe (seccion 5 y anexo).

1) Comparacion del optimo con dos heuristicas voraces (figura 2).
2) Precio sombra del presupuesto (dual de la relajacion) frente a la ganancia entera.
3) Sensibilidad al costo de los sensores (app y nucleo).
4) Perturbacion de probabilidades +-20 % (Monte Carlo, semilla fija).
5) Sensibilidad al numero de rutas k.
6) Escalabilidad en redes aleatorias (semillas fijas).

Probado con PuLP 4.2 + highspy. Resultados en resultados/analisis_*.csv
"""
import csv
import random
import statistics
import time

import networkx as nx
import pulp

from sentinelplace.modelo import resolver
from sentinelplace.red import construir_red
from sentinelplace.rutas import generar_rutas

B_BASE = 4


def datos(g: nx.DiGraph, k: int = 5):
    rutas = generar_rutas(g, k)
    costos = {n: d["costo"] for n, d in g.nodes(data=True) if d["rol"] == "candidato"}
    return rutas, costos


def cobertura(rutas, sensores) -> float:
    return sum(r["peso"] for r in rutas if set(r["candidatos"]) & set(sensores))


def voraz_centralidad(g, costos, b):
    """Recorre los nodos de mayor a menor centralidad y agrega los que caben."""
    bc = nx.betweenness_centrality(g)
    elegidos, gasto = [], 0
    for j in sorted(costos, key=lambda j: -bc[j]):
        if gasto + costos[j] <= b:
            elegidos.append(j)
            gasto += costos[j]
    return elegidos


def voraz_razon(rutas, costos, b):
    """Agrega en cada paso el sensor con mayor riesgo nuevo por unidad de costo."""
    elegidos, gasto = [], 0
    while True:
        mejor, mejor_razon = None, 0.0
        for j in costos:
            if j in elegidos or gasto + costos[j] > b:
                continue
            ganancia = cobertura(rutas, elegidos + [j]) - cobertura(rutas, elegidos)
            if ganancia / costos[j] > mejor_razon:
                mejor, mejor_razon = j, ganancia / costos[j]
        if mejor is None:
            return elegidos
        elegidos.append(mejor)
        gasto += costos[mejor]


def precio_sombra(rutas, costos, b) -> tuple[float, float]:
    """Resuelve la relajacion lineal y devuelve (Z_relajado, dual del presupuesto)."""
    m = pulp.LpProblem("relajacion", pulp.LpMaximize)
    x = {j: m.add_variable(f"x_{j}", lowBound=0, upBound=1) for j in costos}
    y = {r["id"]: m.add_variable(f"y_{r['id']}", lowBound=0, upBound=1) for r in rutas}
    m += pulp.lpSum(r["peso"] * y[r["id"]] for r in rutas)
    for r in rutas:
        m += y[r["id"]] <= pulp.lpSum(x[j] for j in r["candidatos"])
    m += pulp.lpSum(costos[j] * x[j] for j in costos) <= b, "presupuesto"
    m.solve(pulp.HiGHS(msg=False))
    return pulp.value(m.objective), m.get_constraint_by_name("presupuesto").pi


def guardar(nombre, encabezado, filas):
    with open(f"resultados/{nombre}", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(encabezado)
        w.writerows(filas)


def main():
    g = construir_red()
    rutas, costos = datos(g)
    total = sum(r["peso"] for r in rutas)

    print("1) Optimo frente a heuristicas (% del riesgo total)")
    filas = []
    for b in range(1, 9):
        opt = resolver(costos, rutas, b).z
        cen = cobertura(rutas, voraz_centralidad(g, costos, b))
        raz = cobertura(rutas, voraz_razon(rutas, costos, b))
        filas.append((b, *(round(100 * v / total, 1) for v in (opt, raz, cen))))
        print("  B={} optimo {} | voraz razon {} | voraz centralidad {}".format(*filas[-1]))
    guardar("analisis_heuristicas.csv", ["B", "optimo", "voraz_razon", "voraz_centralidad"], filas)

    print("2) Precio sombra frente a ganancia entera")
    filas = []
    for b in range(1, 7):
        z_rel, pi = precio_sombra(rutas, costos, b)
        ganancia = resolver(costos, rutas, b + 1).z - resolver(costos, rutas, b).z
        filas.append((b, round(z_rel, 3), round(pi, 3), round(ganancia, 3)))
        print("  B={} Z_relajado {} precio_sombra {} ganancia_entera {}".format(*filas[-1]))
    guardar("analisis_precio_sombra.csv", ["B", "z_relajado", "precio_sombra", "ganancia_entera"], filas)

    print(f"3) Costo de los sensores (B = {B_BASE})")
    filas = []
    for nodo, valores in (("app", [1, 2, 3, 4]), ("nucleo", [5, 4, 3, 2, 1])):
        for c in valores:
            cc = dict(costos, **{nodo: c})
            s = resolver(cc, rutas, B_BASE)
            filas.append((nodo, c, round(100 * s.z / total, 1), " ".join(s.sensores)))
            print("  costo {}={}: {} % con {}".format(*filas[-1]))
    guardar("analisis_costos.csv", ["nodo", "costo", "porcentaje", "sensores"], filas)

    print("4) Perturbacion de probabilidades +-20 % (300 escenarios, semilla 42)")
    random.seed(42)
    conteo, perdidas = {}, []
    for _ in range(300):
        h = construir_red()
        for _, _, d in h.edges(data=True):
            d["p"] = min(0.95, d["p"] * random.uniform(0.8, 1.2))
        rr, cc = datos(h)
        s = resolver(cc, rr, B_BASE)
        clave = " ".join(sorted(s.sensores))
        conteo[clave] = conteo.get(clave, 0) + 1
        perdidas.append(1 - cobertura(rr, ["app", "salto"]) / s.z)
    for clave, n in sorted(conteo.items(), key=lambda t: -t[1]):
        print(f"  {clave}: {n}")
    print(f"  perdida de app+salto: media {100 * statistics.mean(perdidas):.2f} %, "
          f"peor {100 * max(perdidas):.2f} %")
    guardar("analisis_perturbaciones.csv", ["sensores", "escenarios"], sorted(conteo.items(), key=lambda t: -t[1]))

    print(f"5) Numero de rutas k (B = {B_BASE})")
    filas = []
    for k in (1, 3, 5, 10, 20):
        rr, cc = datos(construir_red(), k)
        s = resolver(cc, rr, B_BASE)
        filas.append((k, len(rr), " ".join(s.sensores), round(100 * s.z / sum(r["peso"] for r in rr), 1)))
        print("  k={} rutas {} sensores {} cobertura {} %".format(*filas[-1]))
    guardar("analisis_rutas_k.csv", ["k", "rutas", "sensores", "porcentaje"], filas)

    print("6) Escalabilidad en redes aleatorias (k = 10, B = 15)")
    random.seed(1)
    filas = []
    for n in (50, 100, 200, 400):
        base = nx.gnp_random_graph(n, 4 / n, seed=n, directed=True)
        red = nx.DiGraph()
        entradas, objetivos = {0, 1}, {n - 1, n - 2, n - 3}
        for v in base.nodes:
            if v in entradas:
                red.add_node(v, rol="entrada", zona="externa", costo=None, criticidad=None)
            elif v in objetivos:
                red.add_node(v, rol="objetivo", zona="critica", costo=None, criticidad=10)
            else:
                red.add_node(v, rol="candidato", zona="interna", costo=random.randint(1, 5), criticidad=None)
        for u, v in base.edges:
            if u not in objetivos and v not in entradas:
                red.add_edge(u, v, p=random.uniform(0.1, 0.9))
        t0 = time.perf_counter()
        rr, cc = datos(red, 10)
        t1 = time.perf_counter()
        s = resolver(cc, rr, 15)
        t2 = time.perf_counter()
        filas.append((n, len(cc), len(rr), len(cc) + len(rr), round(t1 - t0, 3), round(t2 - t1, 3), s.estado))
        print("  nodos {} candidatos {} rutas {} variables {} t_rutas {} s t_modelo {} s {}".format(*filas[-1]))
    guardar("analisis_escalabilidad.csv",
            ["nodos", "candidatos", "rutas", "variables", "t_rutas_s", "t_modelo_s", "estado"], filas)


if __name__ == "__main__":
    main()
