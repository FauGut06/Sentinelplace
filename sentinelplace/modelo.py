"""Modelo de cobertura maxima con presupuesto (PLE binaria), generico.

    max  sum_p w_p * y_p
    s.a. y_p <= sum_{j en p} x_j     para cada ruta p
         sum_j c_j * x_j <= B
         x_j, y_p en {0, 1}

Probado con PuLP 4.2 + highspy (las variables se crean con modelo.add_variable).
"""
from dataclasses import dataclass

import pulp


@dataclass
class Solucion:
    estado: str
    z: float
    sensores: list[str]
    rutas_cubiertas: list[str]
    costo: float


def resolver(costos: dict[str, float], rutas: list[dict], presupuesto: float,
             relajado: bool = False, desempate_costo: bool = True) -> Solucion:
    """costos: {nodo: costo}. rutas: lista de dicts con 'id', 'candidatos' y 'peso'.

    Con desempate_costo=True se resuelve en dos fases (optimizacion lexicografica):
    1) maximizar el riesgo cubierto Z;  2) entre las soluciones con Z = Z*, minimizar
    el costo. Asi no se instalan sensores que no aportan cobertura.
    """
    cat = "Continuous" if relajado else "Binary"
    m = pulp.LpProblem("SentinelPlace", pulp.LpMaximize)
    x = {j: m.add_variable(f"x_{j}", lowBound=0, upBound=1, cat=cat) for j in costos}
    y = {r["id"]: m.add_variable(f"y_{r['id']}", lowBound=0, upBound=1, cat=cat) for r in rutas}

    m += pulp.lpSum(r["peso"] * y[r["id"]] for r in rutas)
    for r in rutas:
        m += y[r["id"]] <= pulp.lpSum(x[j] for j in r["candidatos"]), f"cob_{r['id']}"
    m += pulp.lpSum(costos[j] * x[j] for j in costos) <= presupuesto, "presupuesto"

    res = m.solve(pulp.HiGHS(msg=False))
    z_opt = pulp.value(m.objective)

    if desempate_costo and not relajado and res.status.name == "Optimal":
        m += pulp.lpSum(r["peso"] * y[r["id"]] for r in rutas) >= z_opt - 1e-6, "fija_z"
        m.sense = pulp.LpMinimize
        m.setObjective(pulp.lpSum(costos[j] * x[j] for j in costos))
        res = m.solve(pulp.HiGHS(msg=False))

    sensores = [j for j in costos if (x[j].value() or 0) > 0.5]
    return Solucion(
        estado=res.status.name,
        z=sum(r["peso"] * (y[r["id"]].value() or 0) for r in rutas),
        sensores=sensores,
        rutas_cubiertas=[r["id"] for r in rutas if (y[r["id"]].value() or 0) > 0.5],
        costo=sum(costos[j] for j in sensores),
    )
