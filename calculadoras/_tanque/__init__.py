"""
Motor de calculo del tanque subterraneo (predimensionamiento conceptual).

Paquete con guion bajo inicial: `motor/registro.py` ignora los nombres que
empiezan con "_", por lo que estos modulos NUNCA aparecen como calculadoras
sueltas en el menu. Son piezas puras (sin nada de interfaz) que se ensamblan
en `calculadoras/tanque_subterraneo.py`, que es la unica que expone
`CALCULADORA`.

Cada submodulo corresponde a una seccion de la especificacion tecnica:
  - geometry.py    -> Sec. 3.1 (geometria derivada)
  - loads.py       -> Sec. 3.2 / 3.3 (presion hidrostatica y empuje de suelo)
  - flotation.py   -> Sec. 3.6 (flotacion / subpresion)
  - walls.py       -> Sec. 3.4 / 3.5 (momento en muro + diseno a flexion)
  - roof_slab.py   -> Sec. 3.7 (losa de techo, carga vehicular, punzonado)
  - floor_slab.py  -> Sec. 3.8 (losa de piso)
  - columns.py     -> Sec. 3.9 (columnas de amarre)
  - materials.py   -> Sec. 2 (propiedades de materiales)
  - norms.py       -> constantes normativas, editables, marcadas con
                       "TODO: verificar con norma vigente" (ver Sec. 0/2 de la
                       especificacion: no se inventan coeficientes con
                       apariencia de precision).
"""
