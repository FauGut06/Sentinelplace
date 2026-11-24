"""Pruebas: el modelo generico debe reproducir la instancia pequena y la fuerza bruta."""
from itertools import combinations

import pytest

from sentinelplace.modelo import resolver
from sentinelplace.red import construir_red
from sentinelplace.rutas import generar_rutas

COSTOS = {"W": 3, "V": 2, "S": 4, "A": 2, "T": 1}
RUTAS = [
    {"id": "P1", "candidatos": ["W", "S"], "peso": 5},
    {"id": "P2", "candidatos": ["W", "A"], "peso": 4},
    {"id": "P3", "candidatos": ["V", "S"], "peso": 3},
    {"id": "P4", "candidatos": ["V", "T", "A"], "peso": 2},
    {"id": "P5", "candidatos": ["W", "S", "T"], "peso": 1},
]


def fuerza_bruta(costos, rutas, b):
    mejor = 0.0
    for k in range(len(costos) + 1):
        for conj in combinations(costos, k):
            if sum(costos[j] for j in conj) <= b:
                mejor = max(mejor, sum(r["peso"] for r in rutas if set(r["candidatos"]) & set(conj)))
    return mejor


def test_instancia_pequena():
    sol = resolver(COSTOS, RUTAS, 4)
    assert sol.estado == "Optimal"
    assert sol.z == pytest.approx(12)
    assert sorted(sol.sensores) == ["T", "W"]


@pytest.mark.parametrize("b", range(0, 13))
def test_red_contra_fuerza_bruta(b):
    g = construir_red()
    rutas = generar_rutas(g, k=5)
    costos = {n: d["costo"] for n, d in g.nodes(data=True) if d["rol"] == "candidato"}
    sol = resolver(costos, rutas, b)
    assert sol.costo <= b
    assert sol.z == pytest.approx(fuerza_bruta(costos, rutas, b))


def test_relajacion_es_cota_superior():
    assert resolver(COSTOS, RUTAS, 4, relajado=True).z >= resolver(COSTOS, RUTAS, 4).z
