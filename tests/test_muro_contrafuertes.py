"""
Validacion del motor del muro con contrafuertes contra el Ejemplo 15.3 del libro
(Maria Fratelli - Suelos, Fundaciones y Muros, Cap. 15, H = 9 m).

Los valores del libro estan redondeados en cada paso intermedio (calculo a mano);
el motor calcula todo con precision completa, por eso la tolerancia es relativa
(no exacta), salvo en los pocos valores que coinciden exactamente (R, Fr, pesos).

Ejecutar:   python -m pytest tests/ -v      (o)     python tests/test_muro_contrafuertes.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculadoras.muro_contrafuertes import _motor

ENTRADA = dict(
    H=9.0,
    gs=1850, phi=30, c=0.088, beta=0, q=1200,
    gs2=2000, phi2=34, c2=0.4, sigma_adm=2.8, Dp_adop=1.2,
    fc=200, fy=4200, gc=2500,
    B_adop=3.6, Bprima_adop=0.4, D_adop=0.6, puntera_adop=1.2, L_adop=5.6, t_adop=0.4,
    talon_d_adop=50, puntera_d_adop=45, fuste_d_adop=30, h_ctf_base=2.40,
    mu=0.1448, ju=0.90, phi_corte=0.85, phi_flexion=0.90,
    coef_tanphi_p=0.67, coef_c_p=0.6,
)

# Valores del libro (algunos exactos, otros redondeados por el calculo a mano)
LIBRO_EXACTOS = {
    "W1": 8400, "W2": 5400, "W3": 31080, "Wq": 2400, "W4": 1500, "R": 48780,
    "Fr": 30684,
}

LIBRO_APROX = {
    # clave: (esperado, tolerancia_relativa)
    "Ea": (19736, 0.005),
    "Ep": (23147, 0.01),
    "M_estab": (111933, 0.01),
    "M_volc": (52695, 0.02),
    "FS_volc_sin": (2.12, 0.02),
    "FS_volc_con": (2.37, 0.02),
    "FS_desliz_sin": (1.55, 0.02),
    "FS_desliz_con": (2.72, 0.02),
    "e": (0.6, 0.05),
    # NOTA: en el libro, los numeros de la seccion titulada "Talon" (V1=25320,
    # M1=16.2tm, Mu=27.54tm) coinciden con la losa SIN tierra encima (la
    # adyacente al punto I de momentos, que aqui se modela como "puntera" con
    # terminologia estandar), y los de "Puntera" (Mu=44.7tm) coinciden con la
    # losa que carga tierra+sobrecarga+contrafuerte (aqui "talon"). Ver
    # resumen de la conversacion: el modulo usa terminologia estandar
    # (puntera = lado sin tierra, talon = lado con tierra retenida).
    "V1_punt": (25320, 0.02),
    "M1_punt": (16200, 0.03),
    "Mu_punt": (27540, 0.03),
    "Mu_talon": (44700, 0.03),
    "CL": (0.357, 0.01),
    "q0": (4563, 0.01),
    "q0L2": (143096, 0.01),
    "Mx1": (930, 0.02), "Mx2": (2733, 0.02), "My2": (1073, 0.02),
    "Mx3": (-1245, 0.02), "Mx4": (-5208, 0.02), "My0": (-4164, 0.02),
}


def test_pesos_y_reaccion_exactos():
    r = _motor(ENTRADA)
    for clave, esperado in LIBRO_EXACTOS.items():
        obtenido = r[clave]
        assert abs(obtenido - esperado) < max(1.0, abs(esperado) * 0.002), (
            f"{clave}: obtenido {obtenido:.2f} != libro {esperado}")


def test_valores_aproximan_al_libro():
    r = _motor(ENTRADA)
    for clave, (esperado, tol_rel) in LIBRO_APROX.items():
        obtenido = r[clave]
        tol = max(0.5, abs(esperado) * tol_rel)
        assert abs(obtenido - esperado) < tol, (
            f"{clave}: obtenido {obtenido:.3f} != libro {esperado} (tol {tol:.3f})")


def test_sigma_max_kgcm2():
    r = _motor(ENTRADA)
    sigma_max_kgcm2 = r["sigma_max"] / 10000
    assert abs(sigma_max_kgcm2 - 2.71) < 0.05
    assert r["sigma_min"] >= -1.0   # ~0, puede quedar levemente negativo por redondeo


def test_verificaciones_de_estabilidad_cumplen():
    r = _motor(ENTRADA)
    assert r["volc_ok"]
    assert r["desliz_ok"]
    assert r["exc_ok"]
    assert r["contacto_ok"]


def test_contrafuerte_seccion_base():
    """
    La 'seccion 4' del libro (h=2.40 m, la mas cargada de las 4 que tabula)
    da M=290 tm, Mu=493 tm, As=68.96 cm2 -- pero a una altura ligeramente
    por debajo de la cima real de la cuna (no exactamente en la base, y=Bpanel).
    Aqui se evalua la seccion en la base exacta (y=Bpanel), que es mas
    conservadora (mayor momento) por construccion: se verifica que el As
    resultante sea mayor que el del libro pero del mismo orden de magnitud
    (no un valor arbitrario), y que la relacion As/cos(theta) este bien
    aplicada comparando contra el As del libro evaluado con el Mu del libro.
    """
    r = _motor(ENTRADA)
    # As usando el Mu *del libro* (493 tm) con el mismo theta/d que aca: debe
    # reproducir el As del libro (68.96) dentro de tolerancia -- valida que
    # la formula (As = Mu/(phi.fy.ju.d)/cos(theta)) esta bien planteada.
    Mu_libro = 493000.0 * 100  # kg.m -> kg.cm
    As_libro_recalc = Mu_libro / (0.90 * 4200 * 0.90 * r["d_ctf"]) / math.cos(r["theta_ctf"])
    assert abs(As_libro_recalc - 68.96) < 1.5

    # El As en la base exacta debe ser mayor (mas conservador) pero del mismo
    # orden que el del libro (no mas del doble).
    assert r["As_ctf"] > 68.96
    assert r["As_ctf"] < 2 * 68.96


if __name__ == "__main__":
    test_pesos_y_reaccion_exactos()
    test_valores_aproximan_al_libro()
    test_sigma_max_kgcm2()
    test_verificaciones_de_estabilidad_cumplen()
    test_contrafuerte_seccion_base()
    print("OK - el motor reproduce el Ejemplo 15.3 dentro de tolerancia.")
