"""
Acero de refuerzo: Tabla 7.4 (áreas de barras por metro de ancho) y sugerencia
automatica del armado.

La Tabla 7.4 da, para cada diametro comercial y separacion, el area de acero
que se provee por metro de ancho, As (cm²/m). Aqui se reconstruye a partir del
area real de cada barra:

    As(cm²/m) = area_barra(cm²) · (100 / separacion_cm)

y se ofrece `sugerir_armado(As_requerido)` que elige el diametro y la separacion
mas economicos que cubren el As requerido, entrando en la misma tabla.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Diametros comerciales: nombre -> diametro (cm)
BARRAS = [
    ("1/4\"", 0.635),
    ("3/8\"", 0.9525),
    ("1/2\"", 1.27),
    ("5/8\"", 1.5875),
    ("3/4\"", 1.905),
    ("7/8\"", 2.2225),
    ("1\"",   2.54),
]

# Separaciones de la Tabla 7.4 (cm)
SEPARACIONES = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 25, 30, 35, 40, 45, 50]


def area_barra(diam_cm: float) -> float:
    return math.pi / 4 * diam_cm ** 2


def As_por_metro(diam_cm: float, sep_cm: float) -> float:
    return area_barra(diam_cm) * (100.0 / sep_cm)


# --------------------------------------------------------------------------- #
#  Tabla 7.4 como tabla de referencia (para mostrar en la app / PDF)
# --------------------------------------------------------------------------- #
def _construir_tabla_74() -> dict:
    columnas = ["Espac. (cm)"] + [f"Ø{n}" for n, _ in BARRAS]
    filas = []
    for s in SEPARACIONES:
        fila = [str(s)] + [f"{As_por_metro(d, s):.1f}" for _, d in BARRAS]
        filas.append(fila)
    return {
        "titulo": "Áreas de acero — As (cm²/m) por diámetro y separación",
        "nota": "Área de acero provista por metro de ancho. Entrar con el As requerido.",
        "columnas": columnas,
        "filas": filas,
    }


TABLA_7_4 = _construir_tabla_74()


# --------------------------------------------------------------------------- #
#  Sugerencia de armado
# --------------------------------------------------------------------------- #
@dataclass
class Armado:
    texto: str          # p.ej.  φ 1/2" @ 15 cm
    diametro: str       # 1/2"
    separacion: float   # cm
    As_provisto: float  # cm²/m


# separaciones practicas para elegir (subconjunto comodo, todas estan en la tabla)
_SEP_PRACTICAS = [10, 12, 15, 17, 20, 25]
# diametros que se consideran para zapatas (de menor a mayor)
_DIAM_ELEGIBLES = ["3/8\"", "1/2\"", "5/8\"", "3/4\"", "7/8\"", "1\""]


def sugerir_armado(As_req: float, sep_max: float = 25.0) -> Armado | None:
    """Elige el diametro mas pequeño (mas economico) cuya separacion, dentro de
    valores practicos, provee un As >= As_req. Devuelve None si ni la barra mayor
    a la minima separacion alcanza (caso muy raro)."""
    dic = dict(BARRAS)
    for nombre in _DIAM_ELEGIBLES:
        d = dic[nombre]
        area = area_barra(d)
        s_max = area * 100.0 / As_req if As_req > 0 else sep_max
        opciones = [s for s in _SEP_PRACTICAS if s <= s_max and s <= sep_max]
        if opciones:
            s = max(opciones)          # la mayor separacion que aun cumple
            return Armado(f"Ø {nombre} @ {s:g} cm", nombre, s, As_por_metro(d, s))
    # Si nada alcanza, usar la barra mayor a la minima separacion practica
    nombre = _DIAM_ELEGIBLES[-1]
    d = dic[nombre]
    s = _SEP_PRACTICAS[0]
    return Armado(f"Ø {nombre} @ {s:g} cm", nombre, s, As_por_metro(d, s))
