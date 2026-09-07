"""
Cargas laterales sobre el tanque (Sec. 3.2 / 3.3 de la especificacion):
presion hidrostatica interior y empuje de suelo + agua + sobrecarga exterior.

Caso critico modelado: tanque VACIO, nivel freatico (NF) posiblemente sobre la
base, empuje exterior total (gobierna muros y flotacion). K0 (empuje en
reposo), NO Ka: el cajon es rigido y enterrado, no se admite el giro/
deformacion que moviliza el empuje activo.
"""
from __future__ import annotations


def presion_hidrostatica_interior(z: float, gamma_agua: float) -> float:
    """z medido desde la superficie del agua hacia abajo (Sec. 3.2)."""
    return gamma_agua * max(z, 0.0)


def presion_lateral_exterior(z: float, gamma_saturado: float, gamma_agua: float, k0: float,
                               q_vehicular: float, profundidad_nivel_freatico: float = 0.0) -> dict:
    """Presion lateral exterior total a la profundidad z (desde la rasante):
    suelo efectivo + agua + sobrecarga vehicular (Sec. 3.3).

    - Si z esta por encima del NF (z <= profundidad_nivel_freatico): tramo
      seco, se usa el peso total del suelo (gamma_saturado, sin descontar
      subpresion) y no hay presion de agua.
    - Si z esta bajo el NF: tramo sumergido, se usa gamma_prima = gamma_sat -
      gamma_agua (peso unitario SUMERGIDO, obligatorio bajo el NF) mas la
      presion hidrostatica exterior, sumando el aporte constante del tramo
      seco de arriba.

    Con profundidad_nivel_freatico=0 (NF en superficie, el caso critico por
    defecto que pide la especificacion), todo z esta sumergido:
        p_total(z) = k0.(gamma_sat-gamma_agua).z + gamma_agua.z + k0.q
    """
    z = max(z, 0.0)
    p_sobrecarga = k0 * q_vehicular
    if z <= profundidad_nivel_freatico:
        p_suelo = k0 * gamma_saturado * z
        p_agua = 0.0
    else:
        gamma_prima = gamma_saturado - gamma_agua
        z_sumergido = z - profundidad_nivel_freatico
        p_suelo = k0 * gamma_saturado * profundidad_nivel_freatico + k0 * gamma_prima * z_sumergido
        p_agua = gamma_agua * z_sumergido
    p_total = p_suelo + p_agua + p_sobrecarga
    return dict(p_suelo=p_suelo, p_agua=p_agua, p_sobrecarga=p_sobrecarga, p_total=p_total)


def envolvente_muro(z_tope: float, z_base: float, gamma_saturado: float, gamma_agua: float,
                      k0: float, q_vehicular: float, profundidad_nivel_freatico: float = 0.0) -> dict:
    """Presiones en el tope y la base del muro para la combinacion 1 (tanque
    vacio + empuje exterior total, Sec. 3.3) -- la que gobierna el diseno de
    muros y la flotacion."""
    p_tope = presion_lateral_exterior(z_tope, gamma_saturado, gamma_agua, k0, q_vehicular,
                                        profundidad_nivel_freatico)
    p_base = presion_lateral_exterior(z_base, gamma_saturado, gamma_agua, k0, q_vehicular,
                                        profundidad_nivel_freatico)
    return dict(w1=p_tope["p_total"], w2=p_base["p_total"], detalle_tope=p_tope, detalle_base=p_base)


def envolvente_combinaciones(z_tope: float, z_base: float, gamma_saturado: float, gamma_agua: float,
                                k0: float, q_vehicular: float, alto_libre: float,
                                profundidad_nivel_freatico: float = 0.0) -> dict:
    """Ambas combinaciones de carga que pide la Sec. 3.3, reportadas como
    envolvente (nunca una sola):

      1. Tanque vacio + empuje exterior total (gobierna muros y flotacion).
      2. Tanque lleno + empuje exterior nulo/parcial (gobierna la losa de
         piso por carga interior, y el muro divisorio si las camaras pudieran
         operar independientemente): el empuje exterior se toma en su valor
         MINIMO razonable (solo sobrecarga, suelo sumergido pero sin la
         presion de agua exterior si se asume napa abatida durante el
         llenado) mientras que hacia adentro actua la presion hidrostatica
         del agua contenida, w2_interior = gamma_agua.alto_libre en la base.
    """
    vacio = envolvente_muro(z_tope, z_base, gamma_saturado, gamma_agua, k0, q_vehicular,
                              profundidad_nivel_freatico)
    lleno_interior_base = presion_hidrostatica_interior(alto_libre, gamma_agua)
    lleno_exterior = envolvente_muro(z_tope, z_base, gamma_saturado, 0.0, k0, q_vehicular,
                                       profundidad_nivel_freatico)
    return dict(
        combinacion_1_vacio=vacio,
        combinacion_2_lleno=dict(
            p_interior_base=lleno_interior_base,
            p_exterior_min=lleno_exterior,
        ),
    )
