"""
Validacion de columnas de amarre (Sec. 8, Caso 6 via columns.momento_columna,
reusando el mismo momento_empotrado_trapezoidal ya probado en
test_tanque_walls.py) y de la verificacion axial+flexion simplificada.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculadoras._tanque.columns import (
    carga_axial_columna, momento_columna, verificar_axial_flexion,
)


def test_momento_columna_usa_franja_tributaria():
    r = momento_columna(w1=540.0, w2=4020.0, L=2.40, espaciamiento_columnas=1.5)
    assert abs(r["M_base"] - 1892.16) / 1892.16 < 0.01
    assert r["M_diseno"] == r["M_base"]


def test_carga_axial_suma_componentes():
    N = carga_axial_columna(reaccion_losa_tributaria=2000.0, peso_muro_tributario=1500.0,
                              peso_propio_columna=300.0)
    assert N == 3800.0


def test_excentricidad_pequeña_no_hace_controlar_flexion():
    r = verificar_axial_flexion(N_kg=10000.0, M_kgm=200.0, dimension_en_direccion_momento_cm=40.0)
    assert not r["flexion_controla"]


def test_excentricidad_grande_hace_controlar_flexion():
    r = verificar_axial_flexion(N_kg=1000.0, M_kgm=800.0, dimension_en_direccion_momento_cm=30.0)
    assert r["flexion_controla"]


if __name__ == "__main__":
    test_momento_columna_usa_franja_tributaria()
    test_carga_axial_suma_componentes()
    test_excentricidad_pequeña_no_hace_controlar_flexion()
    test_excentricidad_grande_hace_controlar_flexion()
    print("OK - test_tanque_columns.py")
