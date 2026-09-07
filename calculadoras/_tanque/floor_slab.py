"""
Losa de piso (Sec. 3.8): flexion bajo presion neta de subrasante, modelo
simplificado tipo losa empotrada/simplemente apoyada en los muros. La ala
perimetral (si existe) se dimensiona con `flotation.resolver_ancho_ala`, no
aqui -- este modulo solo verifica la losa de piso propiamente dicha.

LIMITACION explicita (Sec. 3.8): un modelo de losa sobre apoyo elastico
(Winkler) representaria mejor el suelo de fundacion; para esta etapa
conceptual se usa el mismo modelo simplificado de losa continua/empotrada de
`roof_slab.flexion_losa_maciza`, documentando la limitacion en el reporte.
"""
from __future__ import annotations

from .roof_slab import flexion_losa_maciza
from .walls import diseno_flexion_whitney, As_min_temperatura
from . import norms


def presion_neta_subrasante(presion_admisible_o_reaccion: float, peso_propio_losa: float) -> float:
    """Presion neta hacia arriba sobre la losa de piso: reaccion de la
    subrasante menos el peso propio de la losa (que ya "consume" parte de esa
    reaccion). Puede dar negativo si el peso propio domina -- se reporta tal
    cual, sin forzar un minimo, para que quede visible en el reporte."""
    return presion_admisible_o_reaccion - peso_propio_losa


def disenar_losa_piso(presion_bajo_losa: float, luz_menor: float, espesor_losa_m: float,
                        fc: float, fy: float, recubrimiento_m: float,
                        condicion: str = "empotrada", phi: float = norms.PHI_FLEXION) -> dict:
    peso_propio = espesor_losa_m * 2400.0
    p_neta = presion_neta_subrasante(presion_bajo_losa, peso_propio)
    flex = flexion_losa_maciza(abs(p_neta), luz_menor, condicion)

    diam_barra_estimado_cm = 1.6
    h_cm = espesor_losa_m * 100.0
    d_cm = h_cm - recubrimiento_m * 100.0 - diam_barra_estimado_cm / 2

    diseno = diseno_flexion_whitney(flex["Mu"], 100.0, d_cm, fc, fy, phi)
    As_min = As_min_temperatura(100.0, h_cm)
    As_gobierna = max(diseno["As"], As_min) if diseno["ok"] else As_min

    return dict(peso_propio=peso_propio, p_neta=p_neta, flexion=flex, diseno_flexion=diseno,
                 As_min=As_min, As_gobierna=As_gobierna, d_cm=d_cm,
                 ok=diseno.get("ok", False))
