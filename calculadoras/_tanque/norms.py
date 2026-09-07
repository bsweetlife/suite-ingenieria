"""
Constantes normativas, EDITABLES, para el calculo del tanque subterraneo.

Instruccion de la especificacion (Sec. 0 y 2): no inventar coeficientes
normativos con apariencia de precision (valores exactos de tablas AASHTO,
ACI 530/TMS 402 para mamposteria, o COVENIN). Los valores de aqui son
PLACEHOLDERS razonables para predimensionar; cada uno esta marcado con
"TODO: verificar con norma vigente" y debe confirmarse contra la norma
aplicable al proyecto (COVENIN, ACI 318/350, ACI 530/TMS 402, AASHTO, segun
corresponda) antes de usarse en obra.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
#  Carga vehicular equivalente (Sec. 2, tabla de la especificacion)
# --------------------------------------------------------------------------- #
# TODO: verificar con norma vigente -- estos son valores PLACEHOLDER. En
# particular "camion_pesado_hs20" debe salir de la tabla real de AASHTO
# (tren de cargas HS-20 o el vigente), no de este numero redondeado.
CARGA_VEHICULAR_KG_M2 = {
    "suv_liviano": 500.0,
    "camion_mediano": 1000.0,
    "camion_pesado_hs20": 1750.0,   # TODO: tabla AASHTO real (rango citado: 1500-2000)
}

# Peso por rueda de referencia (kg), para el chequeo de punzonado cuando el
# usuario no da uno propio. TODO: verificar contra el tren de cargas de
# diseno realmente aplicable (AASHTO HS-20, HL-93, o norma local).
PESO_POR_RUEDA_KG = {
    "suv_liviano": 900.0,
    "camion_mediano": 3000.0,
    "camion_pesado_hs20": 7250.0,
}

# Area de contacto de rueda por defecto (cm x cm). Configurable en el
# formulario -- ver Sec. 3.7 ("input configurable, no fija").
ANCHO_RUEDA_CM_DEFECTO = 20.0
LARGO_RUEDA_CM_DEFECTO = 50.0

# --------------------------------------------------------------------------- #
#  Factores de mayoracion de carga (mismo criterio ya usado en el resto del
#  suite -- ver calculadoras/muro_contrafuertes.py, Mu = 1.7 . M). Es el
#  criterio de un codigo ACI anterior a la introduccion de las combinaciones
#  LRFD actuales (0.9/1.2/1.6); se mantiene por CONSISTENCIA con el resto del
#  suite. TODO: confirmar el factor de mayoracion segun la norma vigente del
#  proyecto (podria corresponder usar 1.2D+1.6L u otra combinacion).
# --------------------------------------------------------------------------- #
FACTOR_MAYORACION = 1.7
PHI_FLEXION = 0.90
PHI_CORTE = 0.85

# --------------------------------------------------------------------------- #
#  Cuantia minima de flexion en muros/losas de concreto (Sec. 3.5)
# --------------------------------------------------------------------------- #
# Termino de retraccion/temperatura, generico para losas/muros con barra
# corrugada grado 60 (ACI 318, cuantia 0.0018). Es SOLO el primer termino de
# "As_min = max(0.0018.b.h, formula_de_norma_vigente)" que pide la Sec. 3.5;
# no incluye ningun termino adicional especifico de norma.
# TODO IMPORTANTE: los tanques son estructuras de RETENCION DE LIQUIDOS. Las
# normas especificas para ese uso (p.ej. ACI 350, en vez de ACI 318 comun)
# suelen exigir cuantias minimas MAYORES y limitar el esfuerzo admisible del
# acero (fs) por control de fisuracion -- confirmar con la norma aplicable
# antes de dar por buena esta cuantia en un proyecto real.
CUANTIA_MIN_TEMPERATURA = 0.0018

# --------------------------------------------------------------------------- #
#  Punzonado (corte bidireccional) -- Sec. 3.7
# --------------------------------------------------------------------------- #
# Formula generica de 3 terminos (misma familia que el Vc=0.53.raiz(f'c) de
# corte unidireccional ya usado en el resto del suite, unidades kg/cm2).
# TODO: confirmar la version/edicion de la norma vigente (ACI 318 o COVENIN
# 1753) antes de usar en obra; alfa_s depende de si la columna/carga es
# interior (40), de borde (30) o de esquina (20).
ALFA_S_INTERIOR = 40.0
ALFA_S_BORDE = 30.0
ALFA_S_ESQUINA = 20.0

# --------------------------------------------------------------------------- #
#  Mamposteria armada y rellena (Tipo B) -- Sec. 3.5
# --------------------------------------------------------------------------- #
# Factor de reduccion de capacidad para el muro de bloque armado. Se deja
# como PARAMETRO configurable en el formulario (ver walls.py,
# verificar_muro_mamposteria) -- este es solo el valor por defecto sugerido,
# NO un valor tomado de una tabla de ACI 530/TMS 402 verificada.
# TODO: verificar con norma vigente (ACI 530/TMS 402 o COVENIN aplicable).
FACTOR_REDUCCION_MAMPOSTERIA_DEFECTO = 0.90

# Espaciamiento tipico de celdas grouteadas con acero vertical (modulo de
# bloque de 40 cm es lo mas comun en la practica local). TODO: ajustar al
# modulo del bloque realmente especificado.
ESPACIAMIENTO_CELDA_CM_DEFECTO = 40.0

# --------------------------------------------------------------------------- #
#  Flotacion (Sec. 3.6) -- umbrales de alerta
# --------------------------------------------------------------------------- #
FS_FLOTACION_MINIMO = 1.10     # por debajo: CRITICO (rojo)
FS_FLOTACION_RECOMENDADO = 1.25  # por debajo (hasta el minimo): advertencia (amarillo)

# --------------------------------------------------------------------------- #
#  Espesor minimo practico de losa de techo con transito vehicular
# --------------------------------------------------------------------------- #
# TODO: verificar con norma vigente / buena practica local.
ESPESOR_MINIMO_LOSA_TECHO_CM = 15.0
