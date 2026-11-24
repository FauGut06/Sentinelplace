"""Paso 2: red como grafo, rutas generadas automaticamente y modelo PLE."""
import csv

from sentinelplace.modelo import resolver
from sentinelplace.red import construir_red
from sentinelplace.rutas import generar_rutas
from sentinelplace.visualizar import dibujar_curva, dibujar_red

K_RUTAS = 5
PRESUPUESTO = 4

g = construir_red()
rutas = generar_rutas(g, k=K_RUTAS)
costos = {n: d["costo"] for n, d in g.nodes(data=True) if d["rol"] == "candidato"}
peso_total = sum(r["peso"] for r in rutas)

print(f"Red: {g.number_of_nodes()} nodos, {g.number_of_edges()} aristas")
print(f"Rutas generadas: {len(rutas)} (k = {K_RUTAS} por par entrada-objetivo)\n")
print(f"{'Ruta':<5} {'Peso':>6}  Camino")
for r in sorted(rutas, key=lambda r: -r["peso"]):
    print(f"{r['id']:<5} {r['peso']:>6.3f}  {' -> '.join(r['camino'])}")

sol = resolver(costos, rutas, PRESUPUESTO)
rel = resolver(costos, rutas, PRESUPUESTO, relajado=True)
print(f"\nB = {PRESUPUESTO}: estado {sol.estado}, sensores {sol.sensores} (costo {sol.costo})")
print(f"Riesgo cubierto: {sol.z:.3f} de {peso_total:.3f} ({100 * sol.z / peso_total:.1f} %)")
print(f"Relajacion lineal: Z = {rel.z:.3f}")

presupuestos = list(range(0, sum(costos.values()) + 1))
filas = []
for b in presupuestos:
    s = resolver(costos, rutas, b)
    filas.append((b, s.z, 100 * s.z / peso_total, s.costo, " ".join(s.sensores)))
with open("resultados/sensibilidad.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["presupuesto", "z", "porcentaje", "costo_usado", "sensores"])
    w.writerows(filas)

print("\n B |   Z*   |   %   | sensores")
for b, z, pct, c, sens in filas:
    if b <= 14:
        print(f"{b:>2} | {z:6.3f} | {pct:5.1f} | {sens}")

dibujar_red(g, sol.sensores, f"Sensores optimos con B = {PRESUPUESTO} "
            f"({100 * sol.z / peso_total:.1f} % del riesgo cubierto)", "resultados/red_optima.png")
dibujar_curva(presupuestos, [f[1] for f in filas], peso_total, "resultados/curva_presupuesto.png")
print("\nFiguras en resultados/: red_optima.png, curva_presupuesto.png")
