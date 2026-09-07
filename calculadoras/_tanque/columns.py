"""
Columnas de amarre / pilastras (Sec. 3.9).
"""
from __future__ import annotations

from .walls import momento_empotrado_trapezoidal


def carga_axial_columna(reaccion_losa_tributaria: float, peso_muro_tributario: float,
                          peso_propio_columna: float) -> float:
    return reaccion_losa_tributaria + peso_muro_tributario + peso_propio_columna


def momento_columna(w1: float, w2: float, L: float, espaciamiento_columnas: float) -> dict:
    """Momento de diseno de la columna: mismo `momento_empotrado_trapezoidal`
    de walls.py, con la franja tributaria = espaciamiento de columnas (Sec.
    3.9)."""
    m = momento_empotrado_trapezoidal(w1 * espaciamiento_columnas, w2 * espaciamiento_columnas, L)
    return dict(**m, M_diseno=max(m["M_tope"], m["M_base"]))


def verificar_axial_flexion(N_kg: float, M_kgm: float, dimension_en_direccion_momento_cm: float) -> dict:
    """Verificacion combinada axial + flexion SIMPLIFICADA (Sec. 3.9): como
    minimo conceptual, se compara la excentricidad e=M/N contra el nucleo
    central aproximado de la seccion (h/6, el limite clasico de compresion
    pura sin traccion). Si e excede ese limite, la flexion empieza a
    controlar el diseno -- NO reemplaza un diagrama de interaccion completo.

    N_kg y M_kgm deben ser AMBOS de servicio (sin mayorar): e<=h/6 es un
    chequeo de nucleo/estabilidad, igual convencion que "Excentricidad" en
    muro_contrafuertes.py (e<=B/6 con cargas de servicio). Mezclar un M
    mayorado (Mu) con un N de servicio infla e artificialmente."""
    if N_kg <= 0:
        return dict(e_cm=float("inf"), e_max_cm=dimension_en_direccion_momento_cm / 6,
                     flexion_controla=True, motivo="Carga axial nula o negativa.")
    e_cm = M_kgm * 100.0 / N_kg
    e_max_cm = dimension_en_direccion_momento_cm / 6
    return dict(e_cm=e_cm, e_max_cm=e_max_cm, flexion_controla=e_cm > e_max_cm)
