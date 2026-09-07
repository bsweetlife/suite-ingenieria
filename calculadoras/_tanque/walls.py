"""
Muros: momento de diseno (Sec. 3.4) y verificacion a flexion, para ambos
sistemas constructivos (Sec. 3.5).
"""
from __future__ import annotations

import math

from . import norms
from datos.acero import BARRAS

# Diametros comerciales considerados para la barra vertical del muro de
# mamposteria (excluye 1/4", muy delgada para este uso).
_DIAMETROS_MAMPOSTERIA = ["3/8\"", "1/2\"", "5/8\"", "3/4\"", "7/8\"", "1\""]


def momento_empotrado_trapezoidal(w1: float, w2: float, L: float) -> dict:
    """Viga vertical empotrada-empotrada bajo carga trapezoidal (Sec. 3.4):
    w1 en un extremo (menor), w2 en el otro (mayor), luz libre L entre losas.
    Se descompone en uniforme (magnitud w1) + triangular (0 en el extremo de
    w1, w2-w1 en el extremo de w2) y se superponen los momentos de
    empotramiento perfecto (FEM):

        M_fem_uniforme      = w1.L^2/12                (igual en ambos extremos)
        M_fem_extremo_max   = (w2-w1).L^2/20            (extremo de mayor carga)
        M_fem_extremo_min   = (w2-w1).L^2/30            (extremo de menor carga)

    Reutilizable tanto para el muro (franja de 1 m) como para las columnas de
    amarre (franja tributaria = espaciamiento de columnas): basta con pasar
    w1, w2 ya multiplicados por el ancho de la franja."""
    dw = w2 - w1
    m_uniforme = w1 * L ** 2 / 12
    M_tope = m_uniforme + dw * L ** 2 / 30      # extremo de menor carga
    M_base = m_uniforme + dw * L ** 2 / 20      # extremo de mayor carga
    return dict(M_tope=M_tope, M_base=M_base)


def diseno_flexion_whitney(Mu_kgm: float, b_cm: float, d_cm: float, fc: float, fy: float,
                             phi: float = norms.PHI_FLEXION) -> dict:
    """Ecuacion COMPLETA de diseno a flexion (bloque rectangular de Whitney,
    Sec. 3.5), no la aproximacion simplificada As=M/(0.9.fy.d):

        Ru  = Mu/(phi.b.d^2)
        rho = (0.85.f'c/fy).(1 - raiz(1 - 2.Ru/(0.85.f'c)))
        As  = rho.b.d

    Mu en kg.m, b/d en cm, f'c/fy en kg/cm2 -> Ru en kg/cm2 (Mu se pasa a
    kg.cm multiplicando por 100, igual convencion que el resto del suite)."""
    Ru = Mu_kgm * 100.0 / (phi * b_cm * d_cm ** 2)
    discriminante = 1 - 2 * Ru / (0.85 * fc)
    if discriminante < 0:
        return dict(ok=False, Ru=Ru, rho=None, As=None,
                     motivo="Seccion insuficiente: el discriminante de Whitney es negativo "
                            "(aumentar b, d o f'c).")
    rho = (0.85 * fc / fy) * (1 - math.sqrt(discriminante))
    As = rho * b_cm * d_cm
    return dict(ok=True, Ru=Ru, rho=rho, As=As)


def As_min_temperatura(b_cm: float, h_cm: float) -> float:
    """Cuantia minima de retraccion/temperatura (Sec. 3.5): SOLO el primer
    termino de As_min = max(0.0018.b.h, formula_de_norma_vigente). Ver
    norms.CUANTIA_MIN_TEMPERATURA -- para tanques (retencion de liquidos)
    confirmar si la norma aplicable (p.ej. ACI 350) exige una cuantia mayor."""
    return norms.CUANTIA_MIN_TEMPERATURA * b_cm * h_cm


def disenar_muro_concreto(Mu_kgm: float, espesor_muro_m: float, recubrimiento_m: float,
                            fc: float, fy: float, phi: float = norms.PHI_FLEXION) -> dict:
    """Diseno a flexion del muro de concreto armado, franja de 1 m de ancho
    (b=100 cm). d se calcula a partir del espesor y el recubrimiento (con un
    diametro de barra tipico de 1.6 cm / 5/8" para la estimacion de d, ya que
    el diametro final depende del propio resultado)."""
    diam_barra_estimado_cm = 1.6
    h_cm = espesor_muro_m * 100.0
    d_cm = h_cm - recubrimiento_m * 100.0 - diam_barra_estimado_cm / 2
    diseno = diseno_flexion_whitney(Mu_kgm, 100.0, d_cm, fc, fy, phi)
    As_min = As_min_temperatura(100.0, h_cm)
    if diseno["ok"]:
        As_gobierna = max(diseno["As"], As_min)
    else:
        As_gobierna = As_min
    return dict(**diseno, d_cm=d_cm, As_min=As_min, As_gobierna=As_gobierna)


def verificar_muro_mamposteria(Mu_kgm: float, espesor_bloque_cm: float, recubrimiento_cm: float,
                                  diametro_barra_cm: float, espaciamiento_celda_cm: float, fy: float,
                                  factor_reduccion: float = norms.FACTOR_REDUCCION_MAMPOSTERIA_DEFECTO) -> dict:
    """Verificacion del muro de bloque armado y relleno (Tipo B, Sec. 3.5):
    el acero vertical esta DISCRETIZADO por celda (una barra cada
    `espaciamiento_celda_cm`, tipicamente el modulo del bloque, p.ej. 40 cm),
    NO es una cuantia continua como en concreto.

    Momento resistente aproximado (predimensionamiento conceptual, brazo de
    palanca ~0.9d, sin tabla de interaccion completa de ACI 530/TMS 402):
        As/m  = area_barra . (100/espaciamiento_celda_cm)
        Mn/m  = As/m . fy . 0.9.d
        Mu_resistente = factor_reduccion . Mn/m

    `factor_reduccion` es un PARAMETRO configurable (no un valor de norma
    hardcodeado, ver norms.FACTOR_REDUCCION_MAMPOSTERIA_DEFECTO)."""
    d_cm = espesor_bloque_cm - recubrimiento_cm - diametro_barra_cm / 2
    area_barra = math.pi / 4 * diametro_barra_cm ** 2
    As_por_metro = area_barra * (100.0 / espaciamiento_celda_cm)
    Mn_por_metro = As_por_metro * fy * 0.9 * d_cm / 100.0   # kg.cm -> kg.m (/100)
    Mu_resistente = factor_reduccion * Mn_por_metro
    ok = Mu_resistente >= Mu_kgm
    capacidad_demanda = Mu_resistente / Mu_kgm if Mu_kgm > 0 else float("inf")
    return dict(d_cm=d_cm, As_por_metro=As_por_metro, Mn_por_metro=Mn_por_metro,
                 Mu_resistente=Mu_resistente, ok=ok, capacidad_demanda=capacidad_demanda)


def sugerir_armado_muro_mamposteria(
    Mu_kgm: float, espesor_bloque_cm: float, recubrimiento_cm: float, fy: float,
    espaciamiento_celda_cm: float,
    factor_reduccion: float = norms.FACTOR_REDUCCION_MAMPOSTERIA_DEFECTO,
) -> dict | None:
    """Elige el diametro de barra vertical mas economico que, grouteando una
    celda cada `espaciamiento_celda_cm` (el modulo del bloque, sin tocar el
    espaciamiento), cubre Mu_kgm segun `verificar_muro_mamposteria`. Si ni la
    barra mayor alcanza a ese espaciamiento, reintenta grouteando cada celda
    (mitad del espaciamiento) antes de rendirse -- ver esa funcion para la
    formula de capacidad. Devuelve None si ninguna combinacion alcanza."""
    dic = dict(BARRAS)
    for espaciamiento in (espaciamiento_celda_cm, espaciamiento_celda_cm / 2.0):
        for nombre in _DIAMETROS_MAMPOSTERIA:
            r = verificar_muro_mamposteria(Mu_kgm, espesor_bloque_cm, recubrimiento_cm,
                                             dic[nombre], espaciamiento, fy, factor_reduccion)
            if r["ok"]:
                return dict(nombre=nombre, diametro_cm=dic[nombre],
                             espaciamiento_cm=espaciamiento, **r)
    return None
