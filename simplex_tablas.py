"""Simplex de tabla implementado desde cero para la instancia pequena.

Resuelve las tres relajaciones lineales del arbol de ramificacion y acotamiento
(nodo 0: relajacion; nodo 1: x_V = 0; nodo 2: x_V = 1) con aritmetica exacta
(fracciones), imprime cada tabla y guarda:
  - resultados/tablas_simplex.txt   todas las tablas de las tres relajaciones
  - resultados/simplex_resumen.csv  una fila por iteracion: entra, sale, Z

Ademas compara cada resultado con HiGHS (via PuLP) y, si se indica, con una
resolucion manual:
    python simplex_tablas.py
    python simplex_tablas.py --comparar manual/nodo0.csv

Reglas de pivoteo (deben seguirse tambien a mano para que las tablas coincidan):
  1) Entra la variable con el coeficiente mas negativo en la fila Z;
     si hay empate, la de mas a la izquierda.
  2) Sale la fila con el menor cociente LD / columna pivote (solo valores > 0);
     si hay empate, la fila cuya variable basica esta mas a la izquierda.

Simplificacion: se omiten las cotas x_j <= 1. Instalar "mas de un sensor" en un
nodo no aporta cobertura, porque cada y_p ya esta acotada por 1; por eso esas
cotas no cambian el valor optimo. Se comprueba contra HiGHS con las cotas.
"""
import argparse
import csv
import sys
from fractions import Fraction

NODOS = ["W", "V", "S", "A", "T"]
COSTOS = {"W": 3, "V": 2, "S": 4, "A": 2, "T": 1}
RUTAS = [("P1", ["W", "S"], 5), ("P2", ["W", "A"], 4), ("P3", ["V", "S"], 3),
         ("P4", ["V", "T", "A"], 2), ("P5", ["W", "S", "T"], 1)]
PRESUPUESTO = 4


def fmt(v: Fraction) -> str:
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def construir(fijar_v=None):
    """Arma la relajacion en forma estandar max c.x, A x <= b, x >= 0.

    Filas: 5 de cobertura (y_p - sum x_j <= 0), 1 de presupuesto y 5 cotas y_p <= 1.
    Si fijar_v vale 0 o 1, x_V se reemplaza por esa constante (se mueve al lado derecho).
    """
    nodos = [n for n in NODOS if not (fijar_v is not None and n == "V")]
    variables = [f"x{n}" for n in nodos] + [f"y{i}" for i in range(1, 6)]
    c = [Fraction(0)] * len(nodos) + [Fraction(w) for _, _, w in RUTAS]
    filas, ld = [], []
    for p, (_, ruta, _) in enumerate(RUTAS):
        fila = [Fraction(0)] * len(variables)
        fila[len(nodos) + p] = Fraction(1)
        rhs = Fraction(0)
        for n in ruta:
            if n in nodos:
                fila[nodos.index(n)] = Fraction(-1)
            else:
                rhs += fijar_v  # -x_V pasa al lado derecho como +x_V
        filas.append(fila)
        ld.append(rhs)
    filas.append([Fraction(COSTOS[n]) for n in nodos] + [Fraction(0)] * 5)
    ld.append(Fraction(PRESUPUESTO) - (COSTOS["V"] * fijar_v if fijar_v is not None else 0))
    for p in range(5):
        fila = [Fraction(0)] * len(variables)
        fila[len(nodos) + p] = Fraction(1)
        filas.append(fila)
        ld.append(Fraction(1))
    return variables, c, filas, ld


def simplex(variables, c, filas, ld, salida):
    """Simplex de tabla (maximizacion). Devuelve (Z, solucion, iteraciones)."""
    m, n = len(filas), len(variables)
    holguras = [f"s{i + 1}" for i in range(m)]
    columnas = variables + holguras
    tabla = [filas[i] + [Fraction(int(i == k)) for k in range(m)] + [ld[i]] for i in range(m)]
    z = [-v for v in c] + [Fraction(0)] * m + [Fraction(0)]
    base = [n + i for i in range(m)]

    def imprimir(titulo):
        ancho = 6
        salida.append(titulo)
        salida.append("Base  | " + " ".join(f"{col:>{ancho}}" for col in columnas) + f" | {'LD':>{ancho}}")
        for i in range(m):
            salida.append(f"{columnas[base[i]]:<5} | " + " ".join(f"{fmt(v):>{ancho}}" for v in tabla[i][:-1])
                          + f" | {fmt(tabla[i][-1]):>{ancho}}")
        salida.append("Z     | " + " ".join(f"{fmt(v):>{ancho}}" for v in z[:-1]) + f" | {fmt(z[-1]):>{ancho}}")
        salida.append("")

    imprimir("Tabla inicial")
    pasos = []
    while True:
        entra = min(range(n + m), key=lambda j: (z[j], j))
        if z[entra] >= 0:
            break
        candidatas = [(tabla[i][-1] / tabla[i][entra], base[i], i) for i in range(m) if tabla[i][entra] > 0]
        if not candidatas:
            raise RuntimeError("Problema no acotado")
        _, _, r = min(candidatas)
        sale = base[r]
        piv = tabla[r][entra]
        tabla[r] = [v / piv for v in tabla[r]]
        for i in range(m):
            if i != r and tabla[i][entra] != 0:
                f = tabla[i][entra]
                tabla[i] = [a - f * b for a, b in zip(tabla[i], tabla[r])]
        f = z[entra]
        z = [a - f * b for a, b in zip(z, tabla[r])]
        base[r] = entra
        pasos.append((columnas[entra], columnas[sale], z[-1]))
        imprimir(f"Iteracion {len(pasos)}: entra {columnas[entra]}, sale {columnas[sale]}, Z = {fmt(z[-1])}")
    solucion = {columnas[base[i]]: tabla[i][-1] for i in range(m) if columnas[base[i]] in variables}
    return z[-1], solucion, pasos


def z_highs(fijar_v=None) -> float:
    """Valor de la misma relajacion con HiGHS, incluyendo las cotas x_j <= 1."""
    import pulp
    mdl = pulp.LpProblem("relajacion", pulp.LpMaximize)
    x = {n: mdl.add_variable(f"x_{n}", lowBound=0, upBound=1) for n in NODOS}
    y = {p: mdl.add_variable(f"y_{p}", lowBound=0, upBound=1) for p, _, _ in RUTAS}
    mdl += pulp.lpSum(w * y[p] for p, _, w in RUTAS)
    for p, ruta, _ in RUTAS:
        mdl += y[p] <= pulp.lpSum(x[n] for n in ruta)
    mdl += pulp.lpSum(COSTOS[n] * x[n] for n in NODOS) <= PRESUPUESTO
    if fijar_v is not None:
        mdl += x["V"] == fijar_v
    mdl.solve(pulp.HiGHS(msg=False))
    return pulp.value(mdl.objective)


def comparar(archivo, pasos):
    """Compara una resolucion manual (CSV: iteracion,entra,sale,z) con el codigo."""
    with open(archivo, newline="", encoding="utf-8-sig") as f:
        contenido = f.read()
    # Excel en espanol suele guardar los CSV con ";" como separador.
    separador = ";" if contenido.splitlines()[0].count(";") > contenido.splitlines()[0].count(",") else ","
    manual = [fila for fila in csv.DictReader(contenido.splitlines(), delimiter=separador)
              if (fila.get("entra") or "").strip()]
    print(f"\nComparacion con {archivo}:")
    for k, (entra, sale, z) in enumerate(pasos, start=1):
        if k > len(manual):
            print(f"  Iteracion {k}: falta en el archivo manual (codigo: entra {entra}, sale {sale}, Z = {fmt(z)})")
            return False
        fila = manual[k - 1]
        z_manual = Fraction(fila["z"].strip().replace(",", "."))
        ok = fila["entra"].strip() == entra and fila["sale"].strip() == sale and z_manual == z
        estado = "OK" if ok else "DIFERENTE"
        print(f"  Iteracion {k}: manual entra {fila['entra'].strip()}, sale {fila['sale'].strip()}, "
              f"Z = {fila['z'].strip()} | codigo entra {entra}, sale {sale}, Z = {fmt(z)} -> {estado}")
        if not ok:
            print(f"  Primer error en la iteracion {k}: revisa la tabla de la iteracion {k - 1} "
                  "en resultados/tablas_simplex.txt y repite el pivoteo.")
            return False
    if len(manual) > len(pasos):
        print(f"  El archivo manual tiene {len(manual) - len(pasos)} iteraciones de mas: "
              "la tabla ya era optima (ningun coeficiente negativo en la fila Z).")
        return False
    print("  La resolucion manual coincide con el codigo en todas las iteraciones.")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--comparar", help="CSV con la resolucion manual del nodo 0 (iteracion,entra,sale,z)")
    args = parser.parse_args()

    nodos = [("Nodo 0: relajacion lineal", None), ("Nodo 1: x_V = 0", 0), ("Nodo 2: x_V = 1", 1)]
    texto, resumen, pasos_nodo0 = [], [], None
    print(f"{'Nodo':<28} {'Iter.':>5} {'Z simplex':>10} {'Z HiGHS':>9}  Solucion")
    for nombre, fijar in nodos:
        texto += ["=" * 60, nombre, "=" * 60, ""]
        variables, c, filas, ld = construir(fijar)
        z, sol, pasos = simplex(variables, c, filas, ld, texto)
        if fijar is None:
            pasos_nodo0 = pasos
        zh = z_highs(fijar)
        if abs(float(z) - zh) > 1e-9:
            print(f"ERROR: el simplex y HiGHS no coinciden en {nombre}")
            sys.exit(1)
        valores = ", ".join(f"{k} = {fmt(v)}" for k, v in sol.items() if v != 0)
        print(f"{nombre:<28} {len(pasos):>5} {fmt(z):>10} {zh:>9.4f}  {valores}")
        for k, (entra, sale, zk) in enumerate(pasos, start=1):
            resumen.append((nombre, k, entra, sale, fmt(zk)))

    with open("resultados/tablas_simplex.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(texto))
    with open("resultados/simplex_resumen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nodo", "iteracion", "entra", "sale", "z"])
        w.writerows(resumen)
    print("\nTablas en resultados/tablas_simplex.txt; resumen en resultados/simplex_resumen.csv")

    if args.comparar:
        comparar(args.comparar, pasos_nodo0)


if __name__ == "__main__":
    main()
