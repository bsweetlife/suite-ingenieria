"""
Validacion de la presion lateral exterior (Sec. 8, Caso 4 de la
especificacion): K0=0.5, gamma'=900, gamma_agua=1000, q=500 kg/m2, NF en
superficie (profundidad_nivel_freatico=0), z_tope=0.20 m, z_base=2.60 m.

gamma' = 900 kg/m3 se da directamente en el caso de prueba (equivale a un
gamma_saturado = gamma' + gamma_agua = 1900 kg/m3).

Ejecutar:   python -m pytest tests/test_tanque_loads.py -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculadoras._tanque.loads import presion_lateral_exterior, envolvente_muro

K0 = 0.5
GAMMA_PRIMA = 900.0
GAMMA_AGUA = 1000.0
GAMMA_SATURADO = GAMMA_PRIMA + GAMMA_AGUA
Q = 500.0


def test_presion_en_el_tope():
    p = presion_lateral_exterior(0.20, GAMMA_SATURADO, GAMMA_AGUA, K0, Q, profundidad_nivel_freatico=0.0)
    assert abs(p["p_total"] - 540.0) / 540.0 < 0.01


def test_presion_en_la_base():
    p = presion_lateral_exterior(2.60, GAMMA_SATURADO, GAMMA_AGUA, K0, Q, profundidad_nivel_freatico=0.0)
    assert abs(p["p_total"] - 4020.0) / 4020.0 < 0.01


def test_envolvente_muro_tope_base():
    e = envolvente_muro(0.20, 2.60, GAMMA_SATURADO, GAMMA_AGUA, K0, Q, profundidad_nivel_freatico=0.0)
    assert abs(e["w1"] - 540.0) / 540.0 < 0.01
    assert abs(e["w2"] - 4020.0) / 4020.0 < 0.01


if __name__ == "__main__":
    test_presion_en_el_tope()
    test_presion_en_la_base()
    test_envolvente_muro_tope_base()
    print("OK - test_tanque_loads.py")
