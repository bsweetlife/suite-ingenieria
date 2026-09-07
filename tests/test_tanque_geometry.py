"""
Validacion de la geometria derivada del tanque subterraneo (Sec. 8, Caso 1 de
la especificacion tecnica).

NOTA: el caso de prueba de la especificacion rotula su entrada como "eje a
eje", pero sus numeros solo se reproducen con convencion_dimensiones=
"cara_interior" (ver docstring de calculadoras/_tanque/geometry.py). Se usa
esa convencion aqui porque es la que la especificacion realmente valido a
mano, documentando la discrepancia de nombre.

Espesores de losa de piso/techo: el Caso 1 no los da explicitamente, solo
la altura exterior esperada (2.80 m) con alto_libre=2.40 m. Se deduce
espesor_losa_piso = espesor_losa_techo = 0.20 m (igual al muro), unico valor
que reproduce 0.20+2.40+0.20 = 2.80.

Ejecutar:   python -m pytest tests/test_tanque_geometry.py -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculadoras._tanque.geometry import geometria_derivada, dimensiones_ext_int

ENTRADA_CASO_1 = dict(
    largo=4.70, ancho=2.70, alto_libre=2.40,
    espesor_muro=0.20, espesor_losa_piso=0.20, espesor_losa_techo=0.20,
    ancho_ala=0.0, convencion_dimensiones="cara_interior",
    num_camaras=1, division_orientacion="ninguna",
)


def test_caso_1_exterior():
    r = geometria_derivada(ENTRADA_CASO_1)
    assert abs(r["ext_x"] - 5.10) < 0.01
    assert abs(r["ext_y"] - 3.10) < 0.01
    assert abs(r["altura_exterior"] - 2.80) < 0.01


def test_caso_1_volumen_exterior():
    r = geometria_derivada(ENTRADA_CASO_1)
    assert abs(r["volumen_exterior"] - 44.3) / 44.3 < 0.01


def test_convencion_eje_a_eje_suma_un_espesor():
    # Definicion estandar: eje a eje + 1 espesor = exterior (no 2, a
    # diferencia de "cara_interior"). Se prueba por separado, sin atarlo al
    # Caso 1 (que usa "cara_interior").
    d = dimensiones_ext_int(4.70, 2.70, 0.20, "eje_a_eje")
    assert abs(d["ext_x"] - 4.90) < 1e-9
    assert abs(d["int_x"] - 4.50) < 1e-9


def test_convencion_cara_exterior_es_directa():
    d = dimensiones_ext_int(5.10, 3.10, 0.20, "cara_exterior")
    assert abs(d["int_x"] - 4.70) < 1e-9
    assert abs(d["int_y"] - 2.70) < 1e-9


def test_descomposicion_por_elemento_coincide_con_la_envolvente():
    r = geometria_derivada(ENTRADA_CASO_1)
    suma = r["volumen_losa_piso"] + r["volumen_losa_techo"] + r["volumen_muros"]
    assert abs(suma - r["volumen_concreto_estructura"]) / r["volumen_concreto_estructura"] < 0.01


def test_geometria_fisicamente_inconsistente_lanza_error():
    malo = dict(ENTRADA_CASO_1, espesor_muro=3.0, convencion_dimensiones="cara_exterior", largo=5.10, ancho=3.10)
    try:
        geometria_derivada(malo)
        assert False, "debia lanzar ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    test_caso_1_exterior()
    test_caso_1_volumen_exterior()
    test_convencion_eje_a_eje_suma_un_espesor()
    test_convencion_cara_exterior_es_directa()
    test_descomposicion_por_elemento_coincide_con_la_envolvente()
    test_geometria_fisicamente_inconsistente_lanza_error()
    print("OK - test_tanque_geometry.py")
