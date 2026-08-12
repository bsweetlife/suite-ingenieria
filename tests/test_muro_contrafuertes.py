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


def test_canto_contrafuerte_deriva_de_geometria():
    """A0: el canto del contrafuerte no es un dato suelto -- por geometria
    pura, canto_base = B' + puntera (la cuña va desde la cara posterior del
    fuste hasta el extremo de la puntera). Con B'=0.4 y puntera=2.0,
    canto_base debe dar 2.40 m, igual al h=2.40 del Ejemplo 15.3, y el
    contrafuerte queda exactamente apoyado sobre la losa (sin voladizo)."""
    r = _motor(ENTRADA)
    assert abs(r["canto_base_ctf"] - (ENTRADA["Bprima_adop"] + ENTRADA["puntera_adop"])) < 1e-9
    assert abs(r["canto_base_ctf"] - 2.40) < 0.01
    secciones = r["secciones_ctf"]
    Bp, puntera = ENTRADA["Bprima_adop"], ENTRADA["puntera_adop"]
    h_esperado = [Bp + puntera / 3, Bp + puntera * 2 / 3, Bp + puntera]
    for i, s in enumerate(secciones):
        assert abs(s["h"] - h_esperado[i]) < 0.01, f"seccion {i+1} canto"


def test_contrafuerte_3_secciones():
    """Las 3 secciones (y=Bpanel/3, 2Bpanel/3, Bpanel) usan el mismo recorte
    por traccion z0 que el empuje activo global. Con h1=1.07, h2=1.73,
    h3=2.40 (canto de cada seccion, derivado de B'+puntera), M/As/vu deben
    coincidir con el libro dentro de ~2%: seccion1 M=3358 As=1.78, seccion2
    M=56034 As=18.50, seccion3(base) M=233262 As=55.47, vu=2.9/11.73/17.51."""
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
    """As_min = 14/fy.b.d en la base (fondo de losa): b debe ser el espesor
    REAL de la base (t_ctf_base=0.50 m, el contrafuerte se ensancha ahi), no
    el espesor generico del resto del contrafuerte (t_adop=0.40 m) -- con
    b=50 cm y d=216 cm da 36.0 cm2 (14/4200*50*216); con el b generico daria
    28.8, que subestima el minimo real de la seccion que gobierna."""
    r = _motor(ENTRADA)
    assert abs(r["As_min_ctf"] - 36.0) < 1.0
    assert abs(r["fondo_losa_ctf"]["As_min"] - 36.0) < 1.0

    # Nivel 1: As=1.78 cm2 (momento chico) pero As_min=12.8 cm2 con el b y d
    # PROPIOS de ese nivel (b=t_adop=40 cm, d=96.0 cm) -- este es el numero
    # que el libro usa para justificar "As=1.78 (< As_min 12.8)" en la fila 1
    # de la tabla del Ejemplo 15.3 (Sec. 10).
    secciones = r["secciones_ctf"]
    assert abs(secciones[0]["As_min"] - 12.8) < 0.5
    assert secciones[0]["As_gob"] > secciones[0]["As"]   # rige el As minimo, no el momento


def test_armado_contrafuerte_reproduce_barras_del_libro():
    """La tabla del Ejemplo 15.3 (Sec. 10) arma cada nivel con el MISMO
    diametro (Ø1") y solo cambia la cantidad de barras: 3, 4, 11 y 14 en las
    4 filas (niveles 1-3 y fondo de losa). Eligiendo el diametro por la
    seccion mas exigida (fondo de losa) y recalculando la cantidad de barras
    de ese diametro en cada nivel (con As_gob = max(As, As_min)), el motor
    debe reproducir esos conteos dentro de +/-1 barra: el As continuo del
    motor difiere del As ya redondeado del libro por ~1-6% (mismo margen que
    test_contrafuerte_3_secciones), suficiente para mover ceil() al entero
    siguiente en un par de niveles (p.ej. nivel 3: As=56.14 vs 55.47 del
    libro, ambos a menos de 12,8 cm2/barra de diferencia con 1"=5,07 cm2)."""
    from datos.acero import diametro_barras, barras_con_diametro
    r = _motor(ENTRADA)
    fondo = r["fondo_losa_ctf"]
    diam = diametro_barras(fondo["As_gob"])
    assert diam == "1\""

    n_por_nivel = [barras_con_diametro(s["As_gob"], diam).n_barras for s in r["secciones_ctf"]]
    n_fondo = barras_con_diametro(fondo["As_gob"], diam).n_barras
    n_libro = [3, 4, 11]
    for i, (obtenido, esperado) in enumerate(zip(n_por_nivel, n_libro), start=1):
        assert abs(obtenido - esperado) <= 1, f"nivel {i}: {obtenido} barras vs libro {esperado}"
    assert abs(n_fondo - 14) <= 1, f"fondo de losa: {n_fondo} barras vs libro 14"

    # Cada conteo debe proveer al menos el As gobernante (nunca sub-armado).
    for s in r["secciones_ctf"]:
        assert barras_con_diametro(s["As_gob"], diam).As_provisto >= s["As_gob"]
    assert barras_con_diametro(fondo["As_gob"], diam).As_provisto >= fondo["As_gob"]


def test_ld_basico():
    """Formula simplificada ACI 318 Sec. 12.2.2 en kg/cm2 y cm (ver docstring de
    datos.acero.ld_basico para la conversion desde la formula imperial en psi/in).
    Con fy=4200, f'c=200 y db=2.54 cm (1", > el umbral de #6/1.905 cm por lo que
    usa la constante 5.30): ld = 4200*2.54/(5.30*raiz(200)) = 142.3 cm -- del
    orden de 40-60 diametros de barra, el rango tipico citado para barras Grado
    60 sin recubrimiento en concreto de resistencia normal (142.3/2.54 = 56 db)."""
    from datos.acero import ld_basico
    ld = ld_basico(4200, 200, 2.54)
    assert abs(ld - 142.3) < 1.0
    assert 40 * 2.54 <= ld <= 60 * 2.54
    # Piso absoluto de 30 cm (12 in) del mismo articulo, con una barra chica.
    assert ld_basico(2800, 250, 0.9525) >= 30.0


def test_armado_contrafuerte_explica_continuidad_y_anclaje():
    """El texto de armado debe explicar que las barras principales del
    contrafuerte NO son grupos independientes por nivel: deben leerse los
    cortes (14->12->5->3, ver test_armado_contrafuerte_reproduce_barras_del_libro)
    y la longitud de anclaje mas alla de cada corte teorico."""
    from calculadoras.muro_contrafuertes import calcular, CALCULADORA
    d = CALCULADORA.valores_defecto()
    d.update(ENTRADA)
    res = calcular(d)
    assert "Continuidad" in res.armado_texto
    assert "se cortan 2 (quedan 12)" in res.armado_texto
    assert "se cortan 7 (quedan 5)" in res.armado_texto
    assert "se cortan 2 (quedan 3)" in res.armado_texto
    assert "continuan hasta la punta del panel" in res.armado_texto
    assert any("Longitud de anclaje" in n and "ACI 318" in n for n in res.notas)


def test_esquema_dibuja_armado_del_contrafuerte():
    """El corte debe dibujar el acero principal (linea + marcas de corte con
    Ø1" en cada nivel) ademas de la geometria; usa el mismo diametro y los
    mismos conteos por nivel que el texto de armado, para que nunca queden
    desincronizados (ver _armado_principal_ctf, usado por calcular() y
    esquema()). Ademas valida que ambos renderizadores (SVG para la app,
    Drawing de reportlab para el PDF) no truenen con las primitivas nuevas."""
    from calculadoras.muro_contrafuertes import CALCULADORA
    from motor.dibujo import primitivas_a_svg, primitivas_a_drawing
    d = CALCULADORA.valores_defecto()
    d.update(ENTRADA)
    res = CALCULADORA.funcion(d)
    corte = CALCULADORA.esquema(d, res)[0]
    textos = [p["s"] for p in corte["primitivas"] if p["k"] == "text"]
    assert any('3Ø1"' in t for t in textos)
    assert any('5Ø1"' in t for t in textos)
    assert any('12Ø1"' in t for t in textos)
    assert any('14Ø1"' in t for t in textos)
    # No debe reventar ninguno de los dos renderizadores con las primitivas nuevas.
    assert "<svg" in primitivas_a_svg(corte)
    primitivas_a_drawing(corte)


def test_geometrias_extremas_no_rompen():
    """Con H muy chico, el neto de carga en talon/puntera puede invertir de
    signo (bearing < peso propio+tierra), volviendo Mu_talon/Mu_punt negativo.
    d_min/As usan abs(Mu) (igual que el fuste) para no romper en sqrt()."""
    r = _motor(dict(ENTRADA, H=1.5))
    assert r["d_min_talon"] >= 0
    assert r["d_min_punt"] >= 0

    r = _motor(dict(ENTRADA, H=1.0))
    assert r["d_min_talon"] >= 0
    assert r["d_min_punt"] >= 0


def test_advertencia_CL_mayor_a_0_5():
    """Cuando C/L >= 0.5, la Sec. 6 pide analizar la puntera como placa; este
    modulo solo implementa el voladizo, asi que debe advertirlo en las notas
    en vez de reportar un As silenciosamente no conservador."""
    from calculadoras.muro_contrafuertes import calcular, CALCULADORA
    entrada = dict(ENTRADA, puntera_adop=3.0, L_adop=5.0)  # C/L = 0.6
    d = CALCULADORA.valores_defecto()
    d.update(entrada)
    res = calcular(d)
    assert any("C/L" in n and "0.5" in n for n in res.notas)

    # Con C/L < 0.5 (el caso validado del ejemplo) no debe aparecer.
    d2 = CALCULADORA.valores_defecto()
    d2.update(ENTRADA)
    res2 = calcular(d2)
    assert not any("ADVERTENCIA" in n for n in res2.notas)


if __name__ == "__main__":
    test_pesos_y_reaccion_exactos()
    test_valores_aproximan_al_libro()
    test_sigma_max_kgcm2()
    test_verificaciones_de_estabilidad_cumplen()
    test_fuste_gobierna_My0()
    test_canto_contrafuerte_deriva_de_geometria()
    test_contrafuerte_3_secciones()
    test_contrafuerte_fondo_de_losa_fila_4()
    test_corte_viga_vs_losa()
    test_As_min_contrafuerte()
    test_armado_contrafuerte_reproduce_barras_del_libro()
    test_ld_basico()
    test_armado_contrafuerte_explica_continuidad_y_anclaje()
    test_esquema_dibuja_armado_del_contrafuerte()
    test_geometrias_extremas_no_rompen()
    test_advertencia_CL_mayor_a_0_5()
    print("OK - el motor reproduce el Ejemplo 15.3 dentro de tolerancia.")
