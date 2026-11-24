"""SentinelPlace - instancia pequena del modelo de cobertura maxima con presupuesto.

Modelo (programacion lineal entera binaria):
    max  sum_p w_p * y_p
    s.a. y_p <= sum_{j en p} x_j      para cada ruta p   (cobertura)
         sum_j c_j * x_j <= B                            (presupuesto)
         x_j, y_p en {0, 1}
"""
from itertools import combinations

import pulp  # probado con PuLP 4.2 + highspy; las variables se crean con modelo.add_variable

# --- Datos de la instancia ---------------------------------------------------
COSTOS = {"W": 3, "V": 2, "S": 4, "A": 2, "T": 1}  # costo del sensor por nodo
RUTAS = {  # ruta: (nodos candidatos en la ruta, peso)
    "P1": (["W", "S"], 5),
    "P2": (["W", "A"], 4),
    "P3": (["V", "S"], 3),
    "P4": (["V", "T", "A"], 2),
    "P5": (["W", "S", "T"], 1),
}


def resolver(presupuesto: float, relajado: bool = False):
    """Resuelve el modelo con PuLP y el solver HiGHS. Si relajado=True, x e y son continuas en [0, 1]."""
    cat = pulp.LpContinuous if relajado else pulp.LpBinary
    modelo = pulp.LpProblem("SentinelPlace", pulp.LpMaximize)
    x = {j: modelo.add_variable(f"x_{j}", lowBound=0, upBound=1, cat=cat) for j in COSTOS}
    y = {p: modelo.add_variable(f"y_{p}", lowBound=0, upBound=1, cat=cat) for p in RUTAS}

    modelo += pulp.lpSum(peso * y[p] for p, (_, peso) in RUTAS.items()), "Z"
    for p, (nodos, _) in RUTAS.items():
        modelo += y[p] <= pulp.lpSum(x[j] for j in nodos), f"cobertura_{p}"
    modelo += pulp.lpSum(COSTOS[j] * x[j] for j in COSTOS) <= presupuesto, "presupuesto"

    resultado = modelo.solve(pulp.HiGHS(msg=False))
    return (
        resultado.status.name,
        pulp.value(modelo.objective),
        {j: x[j].value() for j in COSTOS},
        {p: y[p].value() for p in RUTAS},
    )


def fuerza_bruta(presupuesto: float):
    """Verificacion: prueba todas las combinaciones de sensores (2^5 = 32)."""
    mejor = (-1, ())
    for k in range(len(COSTOS) + 1):
        for conjunto in combinations(COSTOS, k):
            if sum(COSTOS[j] for j in conjunto) <= presupuesto:
                z = sum(w for nodos, w in RUTAS.values() if set(nodos) & set(conjunto))
                mejor = max(mejor, (z, conjunto))
    return mejor


if __name__ == "__main__":
    estado, z, x, y = resolver(4)
    print(f"Estado: {estado} | Z* = {z:g}")
    print("Sensores:", [j for j, v in x.items() if v > 0.5])
    print("Rutas cubiertas:", [p for p, v in y.items() if v > 0.5])
    print("Fuerza bruta:", fuerza_bruta(4))

    _, z_rel, x_rel, _ = resolver(4, relajado=True)
    print(f"\nRelajacion lineal (B=4): Z = {z_rel:g}, x = {x_rel}")

    print("\nSensibilidad del presupuesto:")
    print(" B | Z* | sensores")
    for b in range(0, 8):
        _, z, x, _ = resolver(b)
        print(f"{b:>2} | {z:>2g} | {[j for j, v in x.items() if v > 0.5]}")
