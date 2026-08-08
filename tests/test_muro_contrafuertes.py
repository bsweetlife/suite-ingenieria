"""
Validacion del motor del muro con contrafuertes contra el Ejemplo 15.3 del libro
(Maria Fratelli - Suelos, Fundaciones y Muros, Cap. 15, H = 9 m).

Los valores del libro estan redondeados en cada paso intermedio (calculo a mano);
el motor calcula todo con precision completa, por eso la tolerancia es relativa
(no exacta), salvo en los pocos valores que coinciden exactamente (R, Fr, pesos).

Terminologia: "puntera" = lado con tierra + sobrecarga + contrafuerte (C=2.0 m,
C/L=0.357); "talon" = lado sin tierra, junto al punto de momentos por vuelco
(~1.2 m). Ver docstring de calculadoras/muro_contrafuertes.py.

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
    B_adop=3.6, Bprima_adop=0.4, D_adop=0.6, puntera_adop=2.0, L_adop=5.6,
    t_adop=0.4, t_ctf_base=0.50,
    talon_d_adop=50, puntera_d_adop=50, fuste_d_adop=30,
    h_ctf_1=1.07, h_ctf_2=1.73, h_ctf_3=2.40,
    mu=0.1448, ju=0.90, phi_corte=0.85, phi_flexion=0.90,
    coef_tanphi_p=0.67, coef_c_p=0.6,
    s_max_estribo=30.0, diam_estribo=1.5875, ramas_estribo=2,
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
    # Talon (sin tierra) = numeros que el libro rotula "Talon" en la sec. 6.
    "V1_talon": (25320, 0.02),
    "M1_talon": (16200, 0.03),
    "Mu_talon": (27540, 0.03),
    # Puntera (con tierra) = numeros que el libro rotula "Puntera" en la sec. 6.
    "Mu_punt": (44700, 0.03),
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


def test_fuste_gobierna_My0():
    r = _motor(ENTRADA)
    assert r["clave_fuste_gob"] == "My0"
    assert abs(r["Mu_fuste"] - 7078) < 7078 * 0.02
    assert abs(r["d_min_fuste"] - 16) < 1.0


def test_contrafuerte_3_secciones():
    """Las 3 secciones (y=Bpanel/3, 2Bpanel/3, Bpanel) usan el mismo recorte
    por traccion z0 que el empuje activo global. Con h1=1.07, h2=1.73,
    h3=2.40 (canto de cada seccion, del ejemplo), M/As/vu deben coincidir con
    el libro dentro de ~2%: seccion1 M=3358 As=1.78, seccion2 M=56034
    As=18.50, seccion3(base) M=233262 As=55.47, vu=2.9/11.73/17.51."""
    r = _motor(ENTRADA)
    secciones = r["secciones_ctf"]
    assert len(secciones) == 3

    M_libro = [3358, 56034, 233262]
    As_libro = [1.78, 18.50, 55.47]
    vu_libro = [2.9, 11.73, 17.51]
    for i, s in enumerate(secciones):
        assert abs(s["M"] - M_libro[i]) < M_libro[i] * 0.03, f"seccion {i+1} M"
        assert abs(s["As"] - As_libro[i]) < max(0.3, As_libro[i] * 0.06), f"seccion {i+1} As"
        assert abs(s["vu"] - vu_libro[i]) < max(0.05, vu_libro[i] * 0.02), f"seccion {i+1} vu"

    # Nivel 1: sin estribos. Niveles 2 y 3: con estribos, s=30cm (capado por
    # la separacion maxima practica adoptada, igual que en el libro).
    assert not secciones[0]["estribos"]["necesita"]
    assert secciones[1]["estribos"]["necesita"] and secciones[1]["estribos"]["s"] == 30.0
    assert secciones[2]["estribos"]["necesita"] and secciones[2]["estribos"]["s"] == 30.0


def test_contrafuerte_fondo_de_losa_fila_4():
    """El contrafuerte continua como voladizo hasta el FONDO DE LA LOSA
    (H=Bpanel+D), no solo hasta la base del fuste. Ahi el canto ya no crece
    (h=2.40, igual a la seccion 3) pero el momento si: M4 = M3 + V3.D. Esto
    reproduce la 4ta fila del Ejemplo 15.3 (M=290 tm, Mu=493 tm, As=68.96 cm2),
    que es la que gobierna el armado principal del contrafuerte."""
    r = _motor(ENTRADA)
    fondo = r["fondo_losa_ctf"]
    assert abs(fondo["M"] - 290000) < 290000 * 0.02
    assert abs(fondo["Mu"] - 493000) < 493000 * 0.02
    assert abs(fondo["As"] - 68.96) < 68.96 * 0.03
    # As_ctf (el que gobierna el armado) debe ser el del fondo de losa, no el
    # de la seccion 3 (base del fuste, que solo llega a ~55-56 cm2).
    assert abs(r["As_ctf"] - fondo["As"]) < 1e-6
    assert r["As_ctf"] > r["secciones_ctf"][-1]["As"]


def test_corte_viga_vs_losa():
    """El contrafuerte es una viga (puede llevar estribos, con limite superior
    vc+2.1.sqrt(f'c)); talon y puntera son losas (NUNCA llevan estribos, se
    corrigen aumentando d). Con el corte tomado en la seccion critica (a d de
    la cara, no en la cara), el talon cumple con d=50 sin necesitar mas
    espesor (vu=6.35<vc=7.50), igual que en el ejemplo del libro.

    Para la puntera, la integracion rigurosa del corte en la seccion critica
    (con la misma presion de contacto trapezoidal usada para el momento, que
    ya valida Mu contra el libro dentro de 3%) da vu=8.41 con d=45 -- no
    cumple, a diferencia de lo que sugiere el documento de correccion (d=40
    cumple). Por eso el default de puntera_d_adop se subio a 50 cm (con eso
    si cumple, vu=7.43<vc=7.50): la formula simplificada V_critico=V_cara-q.d
    del documento (con q constante) no coincide exactamente con integrar la
    presion de contacto real, que varia a lo largo del voladizo."""
    r = _motor(ENTRADA)
    assert r["corte_talon"]["ok"]
    assert r["corte_punt"]["ok"]

    # Con d=45 en la puntera, la seccion critica NO cumple (y no debe intentar
    # resolverse con estribos: la losa se corrige con mas peralte).
    entrada_d45 = dict(ENTRADA, puntera_d_adop=45)
    r45 = _motor(entrada_d45)
    assert not r45["corte_punt"]["ok"]
    assert r45["corte_punt"]["d_necesario"] is not None

    # Contrafuerte nivel 1: sin estribos (vu<vc). Niveles 2 y 3: con estribos
    # (vc < vu <= vc+2.1.sqrt(f'c)), nunca "excede" en el ejemplo.
    for s in r["secciones_ctf"]:
        assert not s["estribos"]["excede"]


def test_As_min_contrafuerte():
    r = _motor(ENTRADA)
    assert abs(r["As_min_ctf"] - 28.8) < 1.0


if __name__ == "__main__":
    test_pesos_y_reaccion_exactos()
    test_valores_aproximan_al_libro()
    test_sigma_max_kgcm2()
    test_verificaciones_de_estabilidad_cumplen()
    test_fuste_gobierna_My0()
    test_contrafuerte_3_secciones()
    test_contrafuerte_fondo_de_losa_fila_4()
    test_corte_viga_vs_losa()
    test_As_min_contrafuerte()
    print("OK - el motor reproduce el Ejemplo 15.3 dentro de tolerancia.")
