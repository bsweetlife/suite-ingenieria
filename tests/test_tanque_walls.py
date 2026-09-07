"""
Validacion del momento empotrado trapezoidal (Sec. 8, Caso 6): tributario
1.5 m, presiones 540-4,020 kg/m2 (Caso 4), luz L = z_base - z_tope = 2.40 m.

La especificacion advierte que el metodo EXACTO (uniforme + triangular
superpuestos) puede dar un valor distinto a los ~1,640 kg.m calculados a mano
con el promedio simplificado de presion -- y en efecto: 1,640 es casi
exactamente el PROMEDIO de M_tope y M_base del metodo exacto (ver abajo), lo
que confirma que el numero a mano vino de promediar w1 y w2 en vez de
superponer los FEM. Se documenta la diferencia, no se fuerza la coincidencia
(tal como pide la especificacion).

Ejecutar:   python -m pytest tests/test_tanque_walls.py -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculadoras._tanque.walls import (
    momento_empotrado_trapezoidal, diseno_flexion_whitney, As_min_temperatura,
    verificar_muro_mamposteria,
)

TRIBUTARIO = 1.5
W1 = 540.0 * TRIBUTARIO   # 810 kg/m
W2 = 4020.0 * TRIBUTARIO  # 6030 kg/m
L = 2.40


def test_momento_base_gobierna_y_no_coincide_con_el_promedio_a_mano():
    m = momento_empotrado_trapezoidal(W1, W2, L)
    assert abs(m["M_base"] - 1892.16) / 1892.16 < 0.01
    assert abs(m["M_tope"] - 1391.04) / 1391.04 < 0.01
    assert m["M_base"] > m["M_tope"]
    promedio_a_mano = (m["M_base"] + m["M_tope"]) / 2
    assert abs(promedio_a_mano - 1640) / 1640 < 0.02   # explica el ~1,640 kg.m del calculo manual


def test_diseno_flexion_whitney_reduce_al_caso_simple_con_Ru_chico():
    # Con Ru pequeño (seccion generosa), rho.b.d debe acercarse a M/(0.9.fy.d)
    Mu = 1892.0
    b, d, fc, fy = 100.0, 15.0, 210.0, 4200.0
    r = diseno_flexion_whitney(Mu, b, d, fc, fy)
    assert r["ok"]
    aproximacion_simple = Mu * 100 / (0.9 * fy * d)
    assert abs(r["As"] - aproximacion_simple) / aproximacion_simple < 0.15


def test_As_min_temperatura():
    assert abs(As_min_temperatura(100.0, 20.0) - 3.6) < 1e-9


def test_verificar_muro_mamposteria_discretiza_por_celda():
    r = verificar_muro_mamposteria(Mu_kgm=1892.0, espesor_bloque_cm=20.0, recubrimiento_cm=3.0,
                                     diametro_barra_cm=1.27, espaciamiento_celda_cm=40.0, fy=4200.0)
    assert r["d_cm"] > 0
    assert r["As_por_metro"] > 0
    assert isinstance(r["ok"], bool)


if __name__ == "__main__":
    test_momento_base_gobierna_y_no_coincide_con_el_promedio_a_mano()
    test_diseno_flexion_whitney_reduce_al_caso_simple_con_Ru_chico()
    test_As_min_temperatura()
    test_verificar_muro_mamposteria_discretiza_por_celda()
    print("OK - test_tanque_walls.py")
