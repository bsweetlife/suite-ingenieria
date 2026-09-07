"""
Propiedades de materiales (Sec. 2 de la especificacion).

Valores por defecto RAZONABLES, no normativos: el usuario los puede cambiar en
el formulario. Donde el valor SI proviene de una norma especifica (cuantias,
factores de reduccion de capacidad, cargas vehiculares), esos numeros viven en
`norms.py`, no aqui.
"""
from __future__ import annotations

GAMMA_CONCRETO = 2400.0     # kg/m3
GAMMA_AGUA = 1000.0         # kg/m3

# Bloque hueco portante, celdas 100% grouteadas (Tipo B). Rango orientativo
# 1900-2100 kg/m3 segun el bloque y el grout; se deja como parametro editable
# porque afecta directamente el chequeo de flotacion.
GAMMA_BLOQUE_ARMADO_RELLENO_MIN = 1900.0
GAMMA_BLOQUE_ARMADO_RELLENO_MAX = 2100.0
GAMMA_BLOQUE_ARMADO_RELLENO_DEFECTO = 2000.0

FY_DEFECTO = 4200.0         # kg/cm2
FC_CONCRETO_DEFECTO = 210.0  # kg/cm2
FC_GROUT_DEFECTO = 150.0     # kg/cm2 (resistencia tipica de grout/mortero de relleno, verificar con el proveedor)
RECUBRIMIENTO_DEFECTO = 0.03  # m

# Peso unitario por sistema constructivo (Sec. 4), clave = TipoMuro.sistema
PESO_UNITARIO_MURO_DEFECTO = {
    "concreto_armado": GAMMA_CONCRETO,
    "bloque_armado_relleno": GAMMA_BLOQUE_ARMADO_RELLENO_DEFECTO,
}

FC_DEFECTO_POR_SISTEMA = {
    "concreto_armado": FC_CONCRETO_DEFECTO,
    "bloque_armado_relleno": FC_GROUT_DEFECTO,
}
