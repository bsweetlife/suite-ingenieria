"""
Chequeo de flotacion / subpresion (Sec. 3.6 de la especificacion).

Modelo:
  - El empuje ascensional E actua sobre la envolvente de la ESTRUCTURA (el
    cajon: volumen_exterior de geometry.py), sin incluir el ala -- por eso el
    aporte del ala se trata aparte, con pesos NETOS (sumergidos), en vez de
    calcularle un empuje ascensional propio (ver `aporte_ala`).
  - W_estructura es el peso TOTAL (no neto) del concreto/mamposteria del
    cajon: la subpresion sobre ese volumen ya esta descontada por separado
    en E, asi que aqui no se resta gamma_agua otra vez.
  - El ala (aparte del cajon) SI se trata con pesos sumergidos/netos, porque
    su empuje ascensional no esta incluido en E:
      * concreto del ala:  volumen . (gamma_concreto - gamma_agua)
      * suelo sobre el ala: area . altura_suelo . gamma_prima
    area_ala se aproxima como perimetro_exterior . ancho_ala (franja simple,
    sin sumar los 4 cuadrados de esquina -- subestima el area en
    4.ancho_ala^2, despreciable frente al perimetro para alas delgadas; es la
    misma simplificacion de un calculo a mano).
"""
from __future__ import annotations

from . import norms


def aporte_ala(perimetro_exterior: float, ancho_ala: float, espesor_losa_piso: float,
                 altura_suelo_sobre_ala: float, gamma_prima: float,
                 gamma_concreto: float, gamma_agua: float) -> dict:
    if ancho_ala <= 0:
        return dict(area_ala=0.0, aporte_concreto_ala=0.0, aporte_suelo_ala=0.0)
    area_ala = perimetro_exterior * ancho_ala
    volumen_concreto_ala = area_ala * espesor_losa_piso
    aporte_concreto_ala = volumen_concreto_ala * (gamma_concreto - gamma_agua)
    aporte_suelo_ala = area_ala * altura_suelo_sobre_ala * gamma_prima
    return dict(area_ala=area_ala, aporte_concreto_ala=aporte_concreto_ala, aporte_suelo_ala=aporte_suelo_ala)


def chequeo_flotacion(volumen_exterior: float, volumen_concreto_estructura: float,
                        peso_unitario_muro: float, gamma_agua: float,
                        perimetro_exterior: float = 0.0, ancho_ala: float = 0.0,
                        espesor_losa_piso: float = 0.0, altura_suelo_sobre_ala: float = 0.0,
                        gamma_prima: float = 0.0, gamma_concreto: float = 2400.0,
                        W_estructura_kg: float | None = None) -> dict:
    """Si se da `W_estructura_kg`, se usa tal cual como peso de la estructura
    (p.ej. calculado aparte sumando muros y losas con pesos unitarios
    distintos -- Tipo B, muros de mamposteria + losas de concreto, Sec. 4).
    Si no, se calcula como volumen_concreto_estructura . peso_unitario_muro
    (un solo material, la formula literal de la Sec. 3.6)."""
    E = gamma_agua * volumen_exterior
    W_estructura = (W_estructura_kg if W_estructura_kg is not None
                     else volumen_concreto_estructura * peso_unitario_muro)
    ala = aporte_ala(perimetro_exterior, ancho_ala, espesor_losa_piso, altura_suelo_sobre_ala,
                       gamma_prima, gamma_concreto, gamma_agua)
    W_total = W_estructura + ala["aporte_concreto_ala"] + ala["aporte_suelo_ala"]
    FS = W_total / E if E > 0 else float("inf")
    nivel = ("critico" if FS < norms.FS_FLOTACION_MINIMO
             else "advertencia" if FS < norms.FS_FLOTACION_RECOMENDADO
             else "ok")
    return dict(E=E, W_estructura=W_estructura, W_total=W_total, FS=FS, nivel=nivel, **ala)


def resolver_ancho_ala(fs_objetivo: float, volumen_exterior: float, volumen_concreto_estructura: float,
                         peso_unitario_muro: float, gamma_agua: float, perimetro_exterior: float,
                         espesor_losa_piso: float, altura_suelo_sobre_ala: float, gamma_prima: float,
                         gamma_concreto: float = 2400.0, ancho_max: float = 3.0, tol: float = 1e-5,
                         max_iter: int = 80, W_estructura_kg: float | None = None) -> dict:
    """Ancho de ala necesario para alcanzar `fs_objetivo`, por biseccion (el
    aporte del ala es lineal en su ancho, pero se resuelve por biseccion en
    vez de despejar algebraicamente para reutilizar exactamente la misma
    funcion `chequeo_flotacion` que reporta el resto del modulo -- una sola
    fuente de verdad para la formula, sin duplicarla en una version
    "despejada" que se podria desincronizar).
    """
    def fs_con_ala(ancho):
        r = chequeo_flotacion(volumen_exterior, volumen_concreto_estructura, peso_unitario_muro,
                                gamma_agua, perimetro_exterior, ancho, espesor_losa_piso,
                                altura_suelo_sobre_ala, gamma_prima, gamma_concreto,
                                W_estructura_kg=W_estructura_kg)
        return r["FS"]

    fs_sin_ala = fs_con_ala(0.0)
    if fs_sin_ala >= fs_objetivo:
        return dict(ancho_necesario=0.0, fs_sin_ala=fs_sin_ala, alcanzable=True,
                     nota="Ya cumple sin ala.")

    lo, hi = 0.0, ancho_max
    if fs_con_ala(hi) < fs_objetivo:
        return dict(ancho_necesario=None, fs_sin_ala=fs_sin_ala, alcanzable=False,
                     nota=f"Ni con ancho_max={ancho_max:.2f} m se alcanza FS={fs_objetivo:.2f} "
                          "(revisar peso propio, profundidad del NF o el espesor de losa de piso).")

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        if fs_con_ala(mid) < fs_objetivo:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return dict(ancho_necesario=hi, fs_sin_ala=fs_sin_ala, alcanzable=True, nota="")
