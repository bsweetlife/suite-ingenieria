"""
Losa de techo: carga vehicular, flexion y punzonado (Sec. 3.7).
"""
from __future__ import annotations

import math

from . import norms


def carga_servicio_techo(w_vehicular_equiv: float, w_acabado: float, espesor_losa_m: float,
                           gamma_concreto: float = 2400.0) -> dict:
    """w_servicio = w_vehicular_equiv + w_acabado + peso_propio_losa (Sec. 3.7)."""
    peso_propio = espesor_losa_m * gamma_concreto
    w_servicio = w_vehicular_equiv + w_acabado + peso_propio
    return dict(peso_propio=peso_propio, w_servicio=w_servicio)


def luz_de_paño(int_x: float, int_y: float, num_camaras: int, division_orientacion: str,
                  espesor_muro_divisorio: float = 0.0) -> dict:
    """Luces reales de cada paño de techo (no se asume cuadrado): si hay 2
    camaras, el muro divisorio parte la luz en la direccion correspondiente
    ("longitudinal" divide el ancho int_y; "transversal" divide el largo
    int_x -- misma convencion que geometry.geometria_derivada)."""
    if num_camaras >= 2 and division_orientacion == "longitudinal":
        luz_x = int_x
        luz_y = (int_y - espesor_muro_divisorio) / 2
    elif num_camaras >= 2 and division_orientacion == "transversal":
        luz_x = (int_x - espesor_muro_divisorio) / 2
        luz_y = int_y
    else:
        luz_x, luz_y = int_x, int_y
    luz_menor, luz_mayor = min(luz_x, luz_y), max(luz_x, luz_y)
    return dict(luz_x=luz_x, luz_y=luz_y, luz_menor=luz_menor, luz_mayor=luz_mayor,
                 relacion_luces=luz_mayor / luz_menor if luz_menor > 0 else float("inf"))


def flexion_losa_maciza(w_servicio: float, luz_menor: float, condicion: str = "empotrada") -> dict:
    """Momento aproximado por metro de ancho en la direccion de la luz menor
    (Sec. 3.7): modelo SIMPLIFICADO de losa continua/empotrada en los muros
    perimetrales (coeficiente unico tipo viga ancha), NO una tabla biaxial
    completa de placa en 2 direcciones. LIMITACION explicita: para relaciones
    de luces pronunciadas o paños muy distintos entre camaras, verificar con
    un modelo de placa/EF."""
    coef = 10.0 if condicion == "empotrada" else 8.0
    Mu = norms.FACTOR_MAYORACION * w_servicio * luz_menor ** 2 / coef
    return dict(Mu=Mu, coef=coef, condicion=condicion)


def perimetro_critico_punzonado(ancho_rueda_cm: float, largo_rueda_cm: float, d_cm: float) -> float:
    """Perimetro critico a d/2 del area de contacto de la rueda (Sec. 3.7)."""
    return 2 * (ancho_rueda_cm + d_cm) + 2 * (largo_rueda_cm + d_cm)


def vc_punzonado(fc: float, beta_c: float, alfa_s: float, bo_cm: float, d_cm: float) -> float:
    """Corte resistente por punzonado, formula ACI 318 de 3 terminos (misma
    familia y unidades -- kg/cm2 -- que el Vc=0.53.raiz(f'c) de corte
    unidireccional ya usado en el resto del suite). Ver TODO de norms.py:
    confirmar version/edicion de la norma vigente antes de usar en obra."""
    v1 = 0.53 * (1 + 2 / beta_c) * math.sqrt(fc)
    v2 = 0.27 * (alfa_s * d_cm / bo_cm + 2) * math.sqrt(fc)
    v3 = 1.06 * math.sqrt(fc)
    return min(v1, v2, v3)


def verificar_punzonado(peso_rueda_kg: float, ancho_rueda_cm: float, largo_rueda_cm: float,
                          d_cm: float, fc: float, beta_c: float = 1.0,
                          alfa_s: float = norms.ALFA_S_INTERIOR) -> dict:
    bo = perimetro_critico_punzonado(ancho_rueda_cm, largo_rueda_cm, d_cm)
    vc = vc_punzonado(fc, beta_c, alfa_s, bo, d_cm)
    vu = norms.FACTOR_MAYORACION * peso_rueda_kg / (bo * d_cm)
    return dict(bo=bo, vc=vc, vu=vu, ok=vu <= vc)


def disenar_losa_techo(w_vehicular_equiv: float, w_acabado: float, espesor_losa_m: float,
                         int_x: float, int_y: float, num_camaras: int, division_orientacion: str,
                         peso_rueda_kg: float, ancho_rueda_cm: float, largo_rueda_cm: float,
                         fc: float, fy: float, recubrimiento_m: float,
                         espesor_muro_divisorio: float = 0.0,
                         gamma_concreto: float = 2400.0,
                         phi: float = norms.PHI_FLEXION) -> dict:
    """Ensambla carga de servicio + luz de paño + flexion + punzonado, y
    reporta cual criterio gobierna (Sec. 3.7)."""
    carga = carga_servicio_techo(w_vehicular_equiv, w_acabado, espesor_losa_m, gamma_concreto)
    luces = luz_de_paño(int_x, int_y, num_camaras, division_orientacion, espesor_muro_divisorio)
    flex = flexion_losa_maciza(carga["w_servicio"], luces["luz_menor"])

    diam_barra_estimado_cm = 1.6
    h_cm = espesor_losa_m * 100.0
    d_cm = h_cm - recubrimiento_m * 100.0 - diam_barra_estimado_cm / 2

    from .walls import diseno_flexion_whitney, As_min_temperatura
    diseno = diseno_flexion_whitney(flex["Mu"], 100.0, d_cm, fc, fy, phi)
    As_min = As_min_temperatura(100.0, h_cm)
    As_gobierna = max(diseno["As"], As_min) if diseno["ok"] else As_min

    punz = verificar_punzonado(peso_rueda_kg, ancho_rueda_cm, largo_rueda_cm, d_cm, fc)

    espesor_min_ok = h_cm >= norms.ESPESOR_MINIMO_LOSA_TECHO_CM

    if not punz["ok"]:
        criterio_gobernante = "punzonado"
    elif not espesor_min_ok:
        criterio_gobernante = "espesor minimo practico"
    else:
        criterio_gobernante = "flexion"

    return dict(carga=carga, luces=luces, flexion=flex, diseno_flexion=diseno, As_min=As_min,
                 As_gobierna=As_gobierna, d_cm=d_cm, punzonado=punz, espesor_min_ok=espesor_min_ok,
                 criterio_gobernante=criterio_gobernante,
                 ok=diseno.get("ok", False) and punz["ok"] and espesor_min_ok)
