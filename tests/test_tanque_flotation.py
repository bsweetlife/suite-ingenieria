"""
Validacion de flotacion (Sec. 8, Casos 2 y 3 de la especificacion).

ADVERTENCIA IMPORTANTE (discrepancia detectada en la especificacion, no un
error de este modulo): el Caso 2 espera "volumen de concreto ~20.5 m3" y
"W ~49,200 kg" para la MISMA geometria del Caso 1 (5.10x3.10 m exterior,
4.70x2.70 m interior, altura exterior 2.80 m, muro/losas 0.20 m). Pero esa
geometria, por sustraccion de volumenes (exterior - cavidad interior, la
formula literal de la Sec. 3.1/3.6), da un volumen de concreto de ~13.8 m3
(comprobado en test_tanque_geometry.py), no 20.5 m3 -- una diferencia de ~48%,
muy por fuera de la tolerancia de redondeo (~2-3%) que la propia
especificacion admite para sus casos de prueba. Los numeros de E (~44,300 kg)
si son consistentes con la geometria del Caso 1.

Como NO se debe forzar una formula para que cuadre con un numero de
referencia que resulta geometricamente inconsistente, este test valida la
formula de la Sec. 3.6 tal como esta escrita (subprestacion literal), usando
el volumen de concreto que realmente sale de la geometria del Caso 1 (via
`geometria_derivada`), en vez de hardcodear el 20.5 m3 del enunciado. El FS
"sin ala" que resulta (~0.75, no ~1.11) es, de hecho, mas conservador y mas
plausible para un cascaron delgado sin ala -- justamente el caso que motiva
la funcion `resolver_ancho_ala`.

El aporte del ala (Caso 3) SI reproduce los numeros de la especificacion casi
exactos (11,500 kg de suelo, 1,400 kg netos de concreto): esos numeros son
internamente consistentes entre si, a diferencia del volumen de concreto del
Caso 2. Ver docstring de flotation.py para la formula exacta.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculadoras._tanque.geometry import geometria_derivada
from calculadoras._tanque.flotation import chequeo_flotacion, resolver_ancho_ala

ENTRADA_CASO_1 = dict(
    largo=4.70, ancho=2.70, alto_libre=2.40,
    espesor_muro=0.20, espesor_losa_piso=0.20, espesor_losa_techo=0.20,
    ancho_ala=0.0, convencion_dimensiones="cara_interior",
    num_camaras=1, division_orientacion="ninguna",
)
GAMMA_AGUA = 1000.0
GAMMA_CONCRETO = 2400.0
GAMMA_PRIMA = 900.0


def _geo():
    return geometria_derivada(ENTRADA_CASO_1)


def test_caso_2_E_consistente_con_geometria():
    geo = _geo()
    r = chequeo_flotacion(geo["volumen_exterior"], geo["volumen_concreto_estructura"],
                            GAMMA_CONCRETO, GAMMA_AGUA)
    assert abs(r["E"] - 44300) / 44300 < 0.01


def test_caso_2_FS_sin_ala_usa_volumen_de_concreto_real():
    geo = _geo()
    r = chequeo_flotacion(geo["volumen_exterior"], geo["volumen_concreto_estructura"],
                            GAMMA_CONCRETO, GAMMA_AGUA)
    # FS esperado con el volumen de concreto REAL de la geometria (~13.8 m3),
    # no con el ~20.5 m3 del enunciado (ver advertencia arriba).
    fs_esperado = geo["volumen_concreto_estructura"] * GAMMA_CONCRETO / r["E"]
    assert abs(r["FS"] - fs_esperado) < 1e-6
    assert r["FS"] < 1.0   # sin ala, este cascaron delgado NO cumple flotacion
    assert r["nivel"] == "critico"


def test_caso_3_aporte_ala_reproduce_la_especificacion():
    geo = _geo()
    r = chequeo_flotacion(geo["volumen_exterior"], geo["volumen_concreto_estructura"],
                            GAMMA_CONCRETO, GAMMA_AGUA,
                            perimetro_exterior=geo["perimetro_exterior"], ancho_ala=0.30,
                            espesor_losa_piso=0.20, altura_suelo_sobre_ala=2.60,
                            gamma_prima=GAMMA_PRIMA, gamma_concreto=GAMMA_CONCRETO)
    assert abs(r["aporte_suelo_ala"] - 11500) / 11500 < 0.02
    assert abs(r["aporte_concreto_ala"] - 1400) / 1400 < 0.05


def test_resolver_ancho_ala_alcanza_el_fs_objetivo():
    geo = _geo()
    sol = resolver_ancho_ala(
        fs_objetivo=1.25, volumen_exterior=geo["volumen_exterior"],
        volumen_concreto_estructura=geo["volumen_concreto_estructura"],
        peso_unitario_muro=GAMMA_CONCRETO, gamma_agua=GAMMA_AGUA,
        perimetro_exterior=geo["perimetro_exterior"], espesor_losa_piso=0.20,
        altura_suelo_sobre_ala=2.60, gamma_prima=GAMMA_PRIMA, gamma_concreto=GAMMA_CONCRETO,
    )
    assert sol["alcanzable"]
    ancho = sol["ancho_necesario"]
    r = chequeo_flotacion(geo["volumen_exterior"], geo["volumen_concreto_estructura"],
                            GAMMA_CONCRETO, GAMMA_AGUA, perimetro_exterior=geo["perimetro_exterior"],
                            ancho_ala=ancho, espesor_losa_piso=0.20, altura_suelo_sobre_ala=2.60,
                            gamma_prima=GAMMA_PRIMA, gamma_concreto=GAMMA_CONCRETO)
    assert abs(r["FS"] - 1.25) < 0.001


if __name__ == "__main__":
    test_caso_2_E_consistente_con_geometria()
    test_caso_2_FS_sin_ala_usa_volumen_de_concreto_real()
    test_caso_3_aporte_ala_reproduce_la_especificacion()
    test_resolver_ancho_ala_alcanza_el_fs_objetivo()
    print("OK - test_tanque_flotation.py")
