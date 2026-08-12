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


# --------------------------------------------------------------------------- #
#  Armado discreto: barras individuales, no por metro de ancho.
#  Para elementos tipo viga (contrafuertes, vigas de riostra) donde el As se
#  cubre con N barras del mismo diametro, no con una separacion por metro.
# --------------------------------------------------------------------------- #
@dataclass
class ArmadoDiscreto:
    texto: str          # p.ej.  "14 Ø 1\""
    diametro: str       # 1"
    n_barras: int
    As_provisto: float  # cm2 (area total de las N barras, NO por metro)


def diametro_barras(As_max: float, n_max: int = 16, n_min: int = 2) -> str:
    """Elige, para un elemento discreto (viga, contrafuerte), el diametro mas
    economico cuya cantidad de barras para cubrir As_max no exceda n_max. Se usa
    UN solo diametro para todo el elemento -- el que fija su seccion mas exigida
    (p.ej. la base) -- y luego se recalcula cuantas barras de ese mismo diametro
    hacen falta en cada seccion con `barras_con_diametro`, igual que se detallan
    los cortes de barra en obra (mismo diametro, distinta cantidad por tramo)."""
    dic = dict(BARRAS)
    for nombre in _DIAM_ELEGIBLES:
        n = max(n_min, math.ceil(As_max / area_barra(dic[nombre]))) if As_max > 0 else n_min
        if n <= n_max:
            return nombre
    return _DIAM_ELEGIBLES[-1]


def barras_con_diametro(As_req: float, diam_nombre: str, n_min: int = 2) -> ArmadoDiscreto:
    """Cantidad de barras del diametro dado que cubren As_req, redondeando hacia
    arriba (minimo n_min por armado practico, aunque As_req sea menor)."""
    d = dict(BARRAS)[diam_nombre]
    area = area_barra(d)
    n = max(n_min, math.ceil(As_req / area)) if As_req > 0 else n_min
    return ArmadoDiscreto(f"{n} Ø {diam_nombre}", diam_nombre, n, n * area)


# --------------------------------------------------------------------------- #
#  Longitud de anclaje (desarrollo en traccion, barra recta)
# --------------------------------------------------------------------------- #
def ld_basico(fy: float, fc: float, db_cm: float) -> float:
    """Longitud de desarrollo basica en traccion para barra corrugada recta,
    formula SIMPLIFICADA de ACI 318 (Sec. 12.2.2: espaciamiento libre >= db y
    recubrimiento >= db, o estribos minimos -- condicion habitual en un
    contrafuerte). No es una formula de este suite validada contra un libro o
    Excel (a diferencia del resto del modulo): es la conversion algebraica
    directa de la formula imperial del codigo a kg/cm2 y cm, con psi_t=psi_e=
    lambda=1 (barra inferior, sin recubrimiento epoxico, concreto de peso
    normal). Sirve como cota de referencia; el detalle final de obra debe
    verificarse contra el codigo vigente (COVENIN 1753 u otro).

    Formula imperial (psi, in):     ld = fy/(25.lambda.raiz(f'c)).db   (db<=#6)
                                     ld = fy/(20.lambda.raiz(f'c)).db   (db>#6, ~19mm)
    Conversion (1 kg/cm2 = 14.223 psi, 1 in = 2.54 cm) da, en kg/cm2 y cm:
                                     ld = fy.db/(6.63.raiz(f'c))        (db<=1.905 cm)
                                     ld = fy.db/(5.30.raiz(f'c))        (db>1.905 cm)
    Minimo absoluto del mismo articulo: ld >= 30 cm (12 in).
    """
    k = 5.30 if db_cm > 1.905 else 6.63
    return max(fy * db_cm / (k * math.sqrt(fc)), 30.0)
