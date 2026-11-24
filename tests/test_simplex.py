"""Pruebas del simplex de tabla implementado desde cero."""
from fractions import Fraction

import pytest

from simplex_tablas import construir, simplex, z_highs


@pytest.mark.parametrize("fijar_v, z_esperado, iteraciones", [
    (None, Fraction(25, 2), 9),   # nodo 0: relajacion lineal
    (0, Fraction(12), 10),        # nodo 1: x_V = 0 (solucion entera)
    (1, Fraction(35, 3), 6),      # nodo 2: x_V = 1 (se poda: 35/3 < 12)
])
def test_nodos_del_arbol(fijar_v, z_esperado, iteraciones):
    z, _, pasos = simplex(*construir(fijar_v), salida=[])
    assert z == z_esperado
    assert len(pasos) == iteraciones
    assert float(z) == pytest.approx(z_highs(fijar_v))


def test_solucion_fraccionaria_del_nodo_raiz():
    _, sol, _ = simplex(*construir(None), salida=[])
    assert sol["xW"] == 1 and sol["xV"] == Fraction(1, 2)


def test_rama_x_v_cero_es_entera():
    _, sol, _ = simplex(*construir(0), salida=[])
    assert all(v.denominator == 1 for v in sol.values())
    assert sol["xW"] == 1 and sol["xT"] == 1
