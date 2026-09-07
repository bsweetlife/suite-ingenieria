"""
Validacion de la losa de techo (Sec. 8, Caso 5): carga vehicular equivalente
500 kg/m2, acabado 100 kg/m2, losa 0.20 m (peso propio esperado 480 kg/m2).
Carga de servicio esperada ~1,080 kg/m2.

Ejecutar:   python -m pytest tests/test_tanque_roof_slab.py -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculadoras._tanque.roof_slab import (
    carga_servicio_techo, luz_de_paño, verificar_punzonado, disenar_losa_techo,
)


def test_caso_5_carga_de_servicio():
    r = carga_servicio_techo(500.0, 100.0, 0.20, gamma_concreto=2400.0)
    assert abs(r["peso_propio"] - 480.0) < 0.01
    assert abs(r["w_servicio"] - 1080.0) < 0.01


def test_luz_de_paño_sin_division():
    r = luz_de_paño(4.70, 2.70, num_camaras=1, division_orientacion="ninguna")
    assert r["luz_menor"] == 2.70
    assert r["luz_mayor"] == 4.70


def test_luz_de_paño_con_division_transversal():
    # "transversal": el muro corre perpendicular al largo (se extiende todo
    # el ancho) y divide el largo (int_x) en dos -- ver geometry.py.
    r = luz_de_paño(4.70, 2.70, num_camaras=2, division_orientacion="transversal",
                      espesor_muro_divisorio=0.20)
    assert abs(r["luz_x"] - 2.25) < 1e-9   # (4.70-0.20)/2
    assert abs(r["luz_y"] - 2.70) < 1e-9


def test_luz_de_paño_con_division_longitudinal():
    # "longitudinal": el muro corre paralelo al largo (se extiende todo el
    # largo) y divide el ancho (int_y) en dos.
    r = luz_de_paño(4.70, 2.70, num_camaras=2, division_orientacion="longitudinal",
                      espesor_muro_divisorio=0.20)
    assert abs(r["luz_x"] - 4.70) < 1e-9
    assert abs(r["luz_y"] - 1.25) < 1e-9   # (2.70-0.20)/2


def test_punzonado_seccion_generosa_cumple():
    r = verificar_punzonado(peso_rueda_kg=900.0, ancho_rueda_cm=20.0, largo_rueda_cm=50.0,
                              d_cm=17.0, fc=210.0)
    assert r["ok"]


def test_disenar_losa_techo_ensambla_criterio_gobernante():
    r = disenar_losa_techo(
        w_vehicular_equiv=500.0, w_acabado=100.0, espesor_losa_m=0.20,
        int_x=4.70, int_y=2.70, num_camaras=1, division_orientacion="ninguna",
        peso_rueda_kg=900.0, ancho_rueda_cm=20.0, largo_rueda_cm=50.0,
        fc=210.0, fy=4200.0, recubrimiento_m=0.03,
    )
    assert r["criterio_gobernante"] in ("flexion", "punzonado", "espesor minimo practico")
    assert r["carga"]["w_servicio"] > 0
    assert r["As_gobierna"] > 0


if __name__ == "__main__":
    test_caso_5_carga_de_servicio()
    test_luz_de_paño_sin_division()
    test_luz_de_paño_con_division_transversal()
    test_luz_de_paño_con_division_longitudinal()
    test_punzonado_seccion_generosa_cumple()
    test_disenar_losa_techo_ensambla_criterio_gobernante()
    print("OK - test_tanque_roof_slab.py")
