"""
Registro central de calculadoras.

Descubre automaticamente cualquier modulo dentro del paquete `calculadoras`
que exponga una variable de nivel de modulo llamada `CALCULADORA`
(instancia de motor.base.Calculadora).

Para agregar una calculadora nueva: crea un archivo en `calculadoras/` que
defina `CALCULADORA = Calculadora(...)`. No hay que registrar nada a mano.
"""
from __future__ import annotations

import importlib
import pkgutil

import calculadoras
from motor.base import Calculadora


def cargar_calculadoras() -> list[Calculadora]:
    encontradas: list[Calculadora] = []
    for info in pkgutil.iter_modules(calculadoras.__path__):
        if info.name.startswith("_"):
            continue
        modulo = importlib.import_module(f"calculadoras.{info.name}")
        calc = getattr(modulo, "CALCULADORA", None)
        if isinstance(calc, Calculadora):
            encontradas.append(calc)
    encontradas.sort(key=lambda c: (c.categoria, c.nombre))
    return encontradas


def por_categoria() -> dict[str, list[Calculadora]]:
    agrupadas: dict[str, list[Calculadora]] = {}
    for calc in cargar_calculadoras():
        agrupadas.setdefault(calc.categoria, []).append(calc)
    return agrupadas
