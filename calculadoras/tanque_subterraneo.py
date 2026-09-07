"""
Tanque subterraneo de agua: predimensionamiento y verificacion conceptual.

Cubre dos sistemas constructivos (Sec. 4 de la especificacion):
  - Tipo A: cajon de concreto armado (losas de piso/techo + muros, todo
    concreto armado).
  - Tipo B: sistema mixto (losas de piso/techo en concreto armado, muros en
    mamposteria armada y rellena, celdas 100% grouteadas).

Esta calculadora ensambla los modulos puros de `calculadoras/_tanque/`
(geometria, cargas, flotacion, muros, losa de techo, losa de piso, columnas)
en un unico formulario/reporte, siguiendo el mismo patron que el resto del
suite (ver motor/base.py). NO reemplaza un analisis de elementos finitos
(SAP2000, ETABS) ni el criterio del ingeniero responsable -- ver los avisos
en `res.notas`.
"""
from __future__ import annotations

import math

from motor.base import Calculadora, Campo, Chequeo, Resultado, Valor
from motor.dibujo import cota_h, cota_v, AZUL, GRIS, TINTA, RELLENO_ZAP, RELLENO_PED, ACERO

from calculadoras._tanque import norms
from calculadoras._tanque.geometry import geometria_derivada
from calculadoras._tanque.loads import envolvente_combinaciones
from calculadoras._tanque.flotation import chequeo_flotacion, resolver_ancho_ala
from calculadoras._tanque.walls import (
    momento_empotrado_trapezoidal, disenar_muro_concreto, verificar_muro_mamposteria,
    sugerir_armado_muro_mamposteria,
)
from calculadoras._tanque.roof_slab import disenar_losa_techo
from calculadoras._tanque.floor_slab import disenar_losa_piso
from calculadoras._tanque.columns import carga_axial_columna, momento_columna, verificar_axial_flexion
from datos.acero import sugerir_armado


# --------------------------------------------------------------------------- #
#  Motor de calculo puro: orquesta los modulos de calculadoras/_tanque/
# --------------------------------------------------------------------------- #
def _motor(d: dict) -> dict:
    r: dict = {}

    geo = geometria_derivada(d)
    r["geo"] = geo

    gamma_saturado = d["gamma_saturado"]
    gamma_agua = d["gamma_agua"]
    gamma_prima = gamma_saturado - gamma_agua
    k0 = d["k0"]
    r["gamma_prima"] = gamma_prima

    tipo_veh = d["tipo_vehicular"]
    q_vehicular = d["carga_uniforme_equivalente"] or norms.CARGA_VEHICULAR_KG_M2[tipo_veh]
    peso_rueda = d["peso_por_rueda"] or norms.PESO_POR_RUEDA_KG[tipo_veh]
    r["q_vehicular"], r["peso_rueda"] = q_vehicular, peso_rueda

    # z_tope/z_base: el tope del muro coincide con la cara inferior de la
    # losa de techo; la base, con la cara superior de la losa de piso.
    z_tope = d["espesor_losa_techo"]
    z_base = d["espesor_losa_techo"] + d["alto_libre"]
    r["z_tope"], r["z_base"] = z_tope, z_base

    env = envolvente_combinaciones(z_tope, z_base, gamma_saturado, gamma_agua, k0, q_vehicular,
                                     d["alto_libre"], d["profundidad_nivel_freatico"])
    r["env"] = env
    w1, w2 = env["combinacion_1_vacio"]["w1"], env["combinacion_1_vacio"]["w2"]
    r["w1"], r["w2"] = w1, w2

    # ---------------- Muro (franja de 1 m) ----------------
    mom_muro = momento_empotrado_trapezoidal(w1, w2, d["alto_libre"])
    r["mom_muro"] = mom_muro
    M_muro_servicio = max(mom_muro["M_tope"], mom_muro["M_base"])
    Mu_muro = norms.FACTOR_MAYORACION * M_muro_servicio
    r["M_muro_servicio"], r["Mu_muro"] = M_muro_servicio, Mu_muro

    sistema = d["sistema_muro"]
    r["sistema_muro"] = sistema
    if sistema == "concreto_armado":
        diseno_muro = disenar_muro_concreto(Mu_muro, d["espesor_muro"], d["recubrimiento"],
                                              d["fc"], d["fy"])
    else:
        diseno_muro = verificar_muro_mamposteria(
            Mu_muro, d["espesor_muro"] * 100.0, d["recubrimiento"] * 100.0,
            d["diametro_barra_vertical"], d["espaciamiento_celda"], d["fy"],
            d["factor_reduccion_mamposteria"],
        )
    r["diseno_muro"] = diseno_muro

    # ---------------- Flotacion ----------------
    # Sobrecimiento / viga de riostra (opcional, Sec. 8 de la memoria de
    # referencia): elemento corrido de concreto bajo todos los muros
    # (perimetral + divisorio), con seccion PROPIA (no la del muro que
    # levanta). 0 x 0 (defecto) = no modelar -- el resto del calculo no
    # cambia si se deja en cero.
    volumen_viga_base = geo["longitud_muros_centerline"] * d["ancho_viga_base"] * d["alto_viga_base"]
    peso_viga_base = volumen_viga_base * d["gamma_concreto"]
    r["volumen_viga_base"], r["peso_viga_base"] = volumen_viga_base, peso_viga_base

    W_estructura = geo["volumen_muros"] * d["peso_unitario_muro"] + \
        (geo["volumen_losa_piso"] + geo["volumen_losa_techo"]) * d["gamma_concreto"] + \
        peso_viga_base
    r["W_estructura"] = W_estructura
    flot = chequeo_flotacion(
        geo["volumen_exterior"], geo["volumen_concreto_estructura"], d["peso_unitario_muro"],
        gamma_agua, geo["perimetro_exterior"], d["ancho_ala"], d["espesor_losa_piso"],
        z_base, gamma_prima, d["gamma_concreto"], W_estructura_kg=W_estructura,
    )
    r["flot"] = flot

    sol_ala = resolver_ancho_ala(
        norms.FS_FLOTACION_RECOMENDADO, geo["volumen_exterior"], geo["volumen_concreto_estructura"],
        d["peso_unitario_muro"], gamma_agua, geo["perimetro_exterior"], d["espesor_losa_piso"],
        z_base, gamma_prima, d["gamma_concreto"], W_estructura_kg=W_estructura,
    )
    r["sol_ala"] = sol_ala

    # ---------------- Losa de techo ----------------
    losa_techo = disenar_losa_techo(
        q_vehicular, d["w_acabado"], d["espesor_losa_techo"], geo["int_x"], geo["int_y"],
        geo["num_camaras"], geo["division_orientacion"], peso_rueda, d["ancho_rueda_cm"],
        d["largo_rueda_cm"], d["fc"], d["fy"], d["recubrimiento"],
        d.get("espesor_muro_divisorio") or 0.0, d["gamma_concreto"],
    )
    r["losa_techo"] = losa_techo

    # ---------------- Losa de piso ----------------
    # Presion bajo la losa: aproximacion conceptual, presion de suelo/agua a
    # la profundidad de la losa de piso (z_base) menos la presion vertical
    # que ya "consume" el peso propio (Sec. 3.8): se usa la presion vertical
    # del agua+suelo saturado a esa profundidad como referencia de subrasante.
    presion_subrasante = gamma_saturado * z_base
    losa_piso = disenar_losa_piso(presion_subrasante, min(geo["int_x"], geo["int_y"]),
                                    d["espesor_losa_piso"], d["fc"], d["fy"], d["recubrimiento"])
    r["presion_subrasante"] = presion_subrasante
    r["losa_piso"] = losa_piso

    # ---------------- Columnas de amarre ----------------
    esp_col = d["espaciamiento_columnas_amarre"]
    mom_col = momento_columna(w1, w2, d["alto_libre"], esp_col)
    r["mom_col"] = mom_col
    # Area tributaria de la columna: ancho = espaciamiento entre columnas,
    # profundidad = mitad de la luz corta del techo (apoyo intermedio tipico
    # de una fila de columnas de amarre a media luz).
    reaccion_losa_trib = losa_techo["carga"]["w_servicio"] * esp_col * (min(geo["int_x"], geo["int_y"]) / 2)
    peso_muro_trib = d["espesor_muro"] * d["alto_libre"] * esp_col * d["peso_unitario_muro"]
    N_col = carga_axial_columna(reaccion_losa_trib, peso_muro_trib, d["peso_propio_columna"])
    r["reaccion_losa_trib"], r["peso_muro_trib"], r["N_col"] = reaccion_losa_trib, peso_muro_trib, N_col
    Mu_col = norms.FACTOR_MAYORACION * mom_col["M_diseno"]
    r["Mu_col"] = Mu_col
    # Excentricidad e=M/N contra el nucleo (h/6): chequeo de servicio (sin
    # mayorar), igual convencion que "Excentricidad" en muro_contrafuertes.py
    # -- mezclar un M mayorado con un N de servicio infla e artificialmente.
    ver_col = verificar_axial_flexion(N_col, mom_col["M_diseno"], d["dimension_columna_direccion_momento"])
    r["ver_col"] = ver_col

    return r


# --------------------------------------------------------------------------- #
#  Ensamble del Resultado (Valores / Chequeos / resumen / armado / notas)
# --------------------------------------------------------------------------- #
def calcular(d: dict) -> Resultado:
    r = _motor(d)
    res = Resultado()
    geo, flot, env = r["geo"], r["flot"], r["env"]

    res.valores = [
        Valor("ext_x", "Dimension exterior X", geo["ext_x"], "m", "segun convencion elegida", 2),
        Valor("ext_y", "Dimension exterior Y", geo["ext_y"], "m", "segun convencion elegida", 2),
        Valor("altura_exterior", "Altura exterior total", geo["altura_exterior"], "m",
              "e_piso + alto_libre + e_techo", 2),
        Valor("volumen_exterior", "Volumen exterior (envolvente)", geo["volumen_exterior"], "m3",
              "ext_x . ext_y . altura_exterior", 2),
        Valor("volumen_muros", "Volumen de muros", geo["volumen_muros"], "m3",
              "perimetro_eje . espesor . alto_libre", 2),
        Valor("w1", "Presion lateral en el tope del muro", r["w1"], "kg/m2",
              "k0.gamma'.z + gamma_agua.z + k0.q", 0),
        Valor("w2", "Presion lateral en la base del muro", r["w2"], "kg/m2",
              "k0.gamma'.z + gamma_agua.z + k0.q", 0),
        Valor("M_muro_servicio", "Momento de servicio en el muro (gobierna)", r["M_muro_servicio"],
              "kg.m/m", "max(M_tope, M_base) trapezoidal exacto", 0),
        Valor("Mu_muro", "Momento ultimo en el muro", r["Mu_muro"], "kg.m/m",
              f"{norms.FACTOR_MAYORACION:g} . M_servicio", 0),
        Valor("E_flotacion", "Empuje ascensional E", flot["E"], "kg", "gamma_agua . volumen_exterior", 0),
        Valor("peso_viga_base", "Peso sobrecimiento / viga de riostra", r["peso_viga_base"], "kg",
              "longitud_muros . ancho_viga_base . alto_viga_base . gamma_concreto", 0),
        Valor("W_total_flotacion", "Peso total resistente W", flot["W_total"], "kg",
              "W_estructura (incl. sobrecimiento/riostra) + aporte_ala", 0),
        Valor("FS_flotacion", "Factor de seguridad a flotacion", flot["FS"], "",
              "W_total / E", 3),
        Valor("Mu_techo", "Momento ultimo en la losa de techo", r["losa_techo"]["flexion"]["Mu"],
              "kg.m/m", f"{norms.FACTOR_MAYORACION:g}.w.L_menor2/coef", 0),
        Valor("N_columna", "Carga axial de la columna de amarre", r["N_col"], "kg",
              "reaccion techo + peso muro trib. + peso propio", 0),
        Valor("Mu_columna", "Momento ultimo en la columna de amarre", r["Mu_col"], "kg.m",
              f"{norms.FACTOR_MAYORACION:g} . M_diseno (trapezoidal, franja=espaciamiento)", 0),
    ]

    # ---------------- Chequeos ----------------
    res.chequeos = [
        Chequeo("Flotacion / subpresion", f"FS = {flot['FS']:.2f}", ">=",
                f"{norms.FS_FLOTACION_RECOMENDADO:.2f} (min. absoluto {norms.FS_FLOTACION_MINIMO:.2f})",
                flot["FS"] >= norms.FS_FLOTACION_RECOMENDADO,
                ("CRITICO: por debajo del minimo absoluto." if flot["nivel"] == "critico" else
                 "Aceptable pero ajustado; sin margen amplio." if flot["nivel"] == "advertencia" else "")),
    ]

    diseno_muro = r["diseno_muro"]
    if r["sistema_muro"] == "concreto_armado":
        res.chequeos.append(Chequeo(
            "Flexion en el muro (concreto armado)",
            f"As req. = {diseno_muro.get('As_gobierna', 0):.2f} cm2/m" if diseno_muro.get("ok") else "seccion insuficiente",
            "<=", "As provisto (ver armado sugerido)", bool(diseno_muro.get("ok")),
            diseno_muro.get("motivo", ""),
        ))
    else:
        res.chequeos.append(Chequeo(
            "Flexion en el muro (mamposteria armada)",
            f"Mu = {r['Mu_muro']:.0f} kg.m/m", "<=",
            f"Mu_resistente = {diseno_muro['Mu_resistente']:.0f} kg.m/m "
            f"(capacidad/demanda = {diseno_muro['capacidad_demanda']:.2f})",
            diseno_muro["ok"],
        ))

    losa_techo = r["losa_techo"]
    res.chequeos.append(Chequeo(
        "Losa de techo - punzonado", f"vu = {losa_techo['punzonado']['vu']:.3f} kg/cm2", "<=",
        f"vc = {losa_techo['punzonado']['vc']:.3f} kg/cm2", losa_techo["punzonado"]["ok"],
    ))
    res.chequeos.append(Chequeo(
        "Losa de techo - espesor minimo practico", f"h = {d['espesor_losa_techo']*100:.0f} cm", ">=",
        f"{norms.ESPESOR_MINIMO_LOSA_TECHO_CM:.0f} cm", losa_techo["espesor_min_ok"],
    ))
    res.chequeos.append(Chequeo(
        "Losa de techo - flexion", f"As req. = {losa_techo['As_gobierna']:.2f} cm2/m",
        "<=", "As provisto (ver armado sugerido)", bool(losa_techo["diseno_flexion"].get("ok")),
        f"Criterio gobernante: {losa_techo['criterio_gobernante']}.",
    ))

    losa_piso = r["losa_piso"]
    res.chequeos.append(Chequeo(
        "Losa de piso - flexion", f"As req. = {losa_piso['As_gobierna']:.2f} cm2/m",
        "<=", "As provisto (ver armado sugerido)", bool(losa_piso["diseno_flexion"].get("ok")),
        "Modelo simplificado (losa empotrada/simplemente apoyada en los muros), no losa sobre "
        "apoyo elastico -- ver notas.",
    ))

    ver_col = r["ver_col"]
    res.chequeos.append(Chequeo(
        "Columna de amarre - excentricidad", f"e = {ver_col['e_cm']:.1f} cm", "<=",
        f"h/6 = {ver_col['e_max_cm']:.1f} cm", not ver_col["flexion_controla"],
        "Si no cumple, la flexion controla el diseno: verificar con un diagrama de interaccion "
        "completo, este chequeo es solo un indicador conceptual.",
    ))

    # ---------------- Resumen (tarjetas destacadas) ----------------
    res.resumen = [
        Valor("espesor_muro", "Espesor muro", d["espesor_muro"] * 100, "cm", "", 0),
        Valor("espesor_losa_piso", "Espesor losa piso", d["espesor_losa_piso"] * 100, "cm", "", 0),
        Valor("espesor_losa_techo", "Espesor losa techo", d["espesor_losa_techo"] * 100, "cm", "", 0),
        Valor("ancho_ala_sug", "Ala sugerida (FS>=1.25)",
              (r["sol_ala"]["ancho_necesario"] or 0.0), "m", "", 2),
        Valor("FS_flotacion_resumen", "FS flotacion (actual)", flot["FS"], "", "", 2),
    ]

    # ---------------- Armado sugerido ----------------
    armados = []
    if r["sistema_muro"] == "concreto_armado" and diseno_muro.get("ok"):
        a_muro = sugerir_armado(diseno_muro["As_gobierna"])
        if a_muro:
            armados.append(f"Muro (concreto armado, cara traccionada): {a_muro.texto} - "
                            f"provee {a_muro.As_provisto:.2f} cm2/m >= "
                            f"{diseno_muro['As_gobierna']:.2f} cm2/m requerido")
    elif r["sistema_muro"] == "bloque_armado_relleno":
        if diseno_muro["ok"]:
            armados.append(
                f"Muro (bloque armado y relleno): Ø{d['diametro_barra_vertical']*10:.1f} mm "
                f"cada {d['espaciamiento_celda']:.0f} cm (celda grouteada), "
                f"provee {diseno_muro['As_por_metro']:.2f} cm2/m."
            )
        else:
            sug_muro = sugerir_armado_muro_mamposteria(
                r["Mu_muro"], d["espesor_muro"] * 100.0, d["recubrimiento"] * 100.0, d["fy"],
                d["espaciamiento_celda"], d["factor_reduccion_mamposteria"],
            )
            if sug_muro:
                armados.append(
                    f"Muro (bloque armado y relleno): la barra/espaciamiento actual "
                    f"(Ø{d['diametro_barra_vertical']*10:.1f} mm cada "
                    f"{d['espaciamiento_celda']:.0f} cm) NO alcanza -- usar "
                    f"Ø {sug_muro['nombre']} cada {sug_muro['espaciamiento_cm']:g} cm "
                    f"(celda grouteada), provee {sug_muro['As_por_metro']:.2f} cm2/m "
                    f"(capacidad/demanda = {sug_muro['capacidad_demanda']:.2f})."
                )
            else:
                armados.append(
                    "Muro (bloque armado y relleno): ninguna combinacion practica de barra y "
                    "espaciamiento (grouteando cada celda) alcanza el momento requerido -- "
                    "aumentar el espesor del muro o cambiar a concreto armado."
                )
    if losa_techo["diseno_flexion"].get("ok"):
        a_techo = sugerir_armado(losa_techo["As_gobierna"])
        if a_techo:
            armados.append(f"Losa de techo: {a_techo.texto} - provee {a_techo.As_provisto:.2f} cm2/m "
                            f">= {losa_techo['As_gobierna']:.2f} cm2/m requerido")
    if losa_piso["diseno_flexion"].get("ok"):
        a_piso = sugerir_armado(losa_piso["As_gobierna"])
        if a_piso:
            armados.append(f"Losa de piso: {a_piso.texto} - provee {a_piso.As_provisto:.2f} cm2/m "
                            f">= {losa_piso['As_gobierna']:.2f} cm2/m requerido")
    res.armado_texto = "<br/>".join(armados) if armados else ""

    # ---------------- Notas y advertencias (Sec. 10, siempre visibles) ----------------
    res.notas.append(
        "Herramienta de predimensionamiento conceptual. No sustituye el analisis estructural "
        "detallado (SAP2000, ETABS u otro) ni el juicio del ingeniero responsable."
    )
    if d["tiene_estudio_suelos"] != "Si":
        res.notas.append(
            "PRELIMINAR - SIN ESTUDIO DE SUELOS: se usan valores geotecnicos conservadores por "
            f"defecto (gamma_saturado={d['gamma_saturado']:.0f} kg/m3, K0={d['k0']:.2f}). "
            "Verificar con un estudio de suelos real antes de construccion."
        )
    res.notas.append(
        "Coeficientes normativos (punzonado, cuantias minimas, factor de reduccion de "
        "mamposteria, cargas vehiculares) son valores editables de predimensionamiento -- "
        "confirmar contra la norma vigente aplicable al proyecto (COVENIN, ACI 318/350, "
        "ACI 530/TMS 402, AASHTO segun corresponda) antes de uso en obra."
    )
    res.notas.append(
        "Tanques = estructuras de retencion de liquidos: normas especificas para ese uso (p.ej. "
        "ACI 350, distinta de ACI 318 comun) suelen exigir cuantias minimas mayores y limitar el "
        "esfuerzo admisible del acero por control de fisuracion. No implementado aqui -- "
        "confirmar antes de dar por buena la cuantia calculada."
    )
    if r["sol_ala"]["ancho_necesario"]:
        res.notas.append(
            f"Ancho de ala sugerido para FS >= {norms.FS_FLOTACION_RECOMENDADO:.2f}: "
            f"{r['sol_ala']['ancho_necesario']:.2f} m (perimetral)."
        )
    elif not r["sol_ala"]["alcanzable"]:
        res.notas.append(f"ADVERTENCIA: {r['sol_ala']['nota']}")
    if d["ancho_viga_base"] > 0 and d["alto_viga_base"] > 0:
        res.notas.append(
            f"Se credita el peso del sobrecimiento/viga de riostra a la flotacion: "
            f"{r['peso_viga_base']:.0f} kg ({d['ancho_viga_base']*100:.0f}x"
            f"{d['alto_viga_base']*100:.0f} cm, corrido bajo todos los muros)."
        )
    else:
        res.notas.append(
            "No se modela sobrecimiento ni viga de riostra/corona (ancho/alto = 0): si el "
            "proyecto los incluye, su peso adicional NO esta credito en el FS de flotacion "
            "mostrado -- ver 'Sobrecimiento / viga de riostra (opcional)'."
        )
    res.notas.append(
        "Diagnostico de flotacion (Sec. 8 de la especificacion original): con las dimensiones y "
        "espesores de muro/losa tipicos de un cascaron delgado (sin ala), el FS de flotacion "
        "suele quedar por debajo de 1.0 -- de ahi la importancia practica del ala perimetral "
        "(ver 'Dimensionamiento asistido')."
    )
    res.notas.append(
        f"Losa de piso: modelo simplificado (losa empotrada/simplemente apoyada en los muros), "
        "NO losa sobre apoyo elastico (Winkler) -- limitacion aceptada para esta etapa "
        "conceptual (Sec. 3.8)."
    )
    if r["sistema_muro"] == "bloque_armado_relleno":
        res.notas.append(
            "Tipo B (mamposteria): detalle critico adicional -- celdas 100% grouteadas, dovelas "
            "ancladas desde la losa de piso, y friso impermeabilizante en ambas caras del muro."
        )
    else:
        res.notas.append("Tipo A (concreto): detalle critico adicional -- juntas de construccion con waterstop.")
    if losa_techo["luces"]["relacion_luces"] > 2.0:
        res.notas.append(
            f"Losa de techo: relacion de luces = {losa_techo['luces']['relacion_luces']:.2f} > 2 "
            "-- el modelo de losa maciza simplificado se vuelve menos representativo; considerar "
            "un analisis de placa/EF."
        )

    return res


# --------------------------------------------------------------------------- #
#  Dimensionamiento asistido: ancho de ala para FS objetivo
# --------------------------------------------------------------------------- #
def sugerir(d: dict) -> dict:
    r = _motor(d)
    sug = dict(d)
    ancho_necesario = r["sol_ala"]["ancho_necesario"]
    # Redondear hacia arriba (al cm): redondear al mas cercano puede quedar
    # por debajo del ancho_necesario exacto y no alcanzar el FS objetivo.
    sug["ancho_ala"] = math.ceil(ancho_necesario * 100) / 100 if ancho_necesario else d["ancho_ala"]

    if d["sistema_muro"] == "bloque_armado_relleno" and not r["diseno_muro"]["ok"]:
        sug_muro = sugerir_armado_muro_mamposteria(
            r["Mu_muro"], d["espesor_muro"] * 100.0, d["recubrimiento"] * 100.0, d["fy"],
            d["espaciamiento_celda"], d["factor_reduccion_mamposteria"],
        )
        if sug_muro:
            sug["diametro_barra_vertical"] = sug_muro["diametro_cm"]
            sug["espaciamiento_celda"] = sug_muro["espaciamiento_cm"]

    return sug


# --------------------------------------------------------------------------- #
#  Esquema: planta + corte con diagrama de presiones
# --------------------------------------------------------------------------- #
def _corte(d: dict, r: dict):
    geo = r["geo"]
    H = geo["altura_exterior"]
    ext_x = geo["ext_x"]
    ancho_ala = d["ancho_ala"]
    losa_x = geo["losa_x"]

    W, Hpx = 340, 250
    mL, mR, mT, mB = 30, 70, 20, 34
    scx = (W - mL - mR) / losa_x
    scy = (Hpx - mT - mB) / H
    x0 = mL
    ytop = mT
    ybase = ytop + H * scy

    p = []
    ala_px = ancho_ala * scx
    ext_x_px = ext_x * scx
    e_piso_px = d["espesor_losa_piso"] * scy
    e_techo_px = d["espesor_losa_techo"] * scy
    alto_libre_px = d["alto_libre"] * scy
    e_muro_px = max(d["espesor_muro"] * scx, 2.5)

    x_ext0 = x0 + ala_px
    x_ext1 = x_ext0 + ext_x_px

    if ancho_ala > 0:
        p.append({"k": "rect", "x": x0, "y": ybase - e_piso_px, "w": ala_px, "h": e_piso_px,
                  "fill": RELLENO_ZAP, "stroke": AZUL, "sw": 1.0})
        p.append({"k": "rect", "x": x_ext1, "y": ybase - e_piso_px, "w": ala_px, "h": e_piso_px,
                  "fill": RELLENO_ZAP, "stroke": AZUL, "sw": 1.0})

    # losa de piso y techo
    p.append({"k": "rect", "x": x_ext0, "y": ybase - e_piso_px, "w": ext_x_px, "h": e_piso_px,
              "fill": RELLENO_ZAP, "stroke": AZUL, "sw": 1.4})
    p.append({"k": "rect", "x": x_ext0, "y": ytop, "w": ext_x_px, "h": e_techo_px,
              "fill": RELLENO_ZAP, "stroke": AZUL, "sw": 1.4})
    # muros
    y_muro0 = ytop + e_techo_px
    p.append({"k": "rect", "x": x_ext0, "y": y_muro0, "w": e_muro_px, "h": alto_libre_px,
              "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.4})
    p.append({"k": "rect", "x": x_ext1 - e_muro_px, "y": y_muro0, "w": e_muro_px, "h": alto_libre_px,
              "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.4})

    # diagrama de presiones (lado izquierdo), triangular/trapezoidal
    w_max = max(r["w1"], r["w2"], 1.0)
    esc_p = 30.0 / w_max
    x_muro_ext = x_ext0
    p.append({"k": "line", "x1": x_muro_ext, "y1": y_muro0, "x2": x_muro_ext - r["w1"] * esc_p,
              "y2": y_muro0, "stroke": ACERO, "sw": 1.0})
    y_base_muro = y_muro0 + alto_libre_px
    p.append({"k": "line", "x1": x_muro_ext, "y1": y_base_muro, "x2": x_muro_ext - r["w2"] * esc_p,
              "y2": y_base_muro, "stroke": ACERO, "sw": 1.0})
    p.append({"k": "line", "x1": x_muro_ext - r["w1"] * esc_p, "y1": y_muro0,
              "x2": x_muro_ext - r["w2"] * esc_p, "y2": y_base_muro, "stroke": ACERO, "sw": 1.4})
    p.append({"k": "text", "x": x_muro_ext - r["w2"] * esc_p - 4, "y": y_base_muro,
              "s": f"w2={r['w2']:.0f}", "size": 7, "anchor": "end", "fill": ACERO})
    p.append({"k": "text", "x": x_muro_ext - r["w1"] * esc_p - 4, "y": y_muro0 - 2,
              "s": f"w1={r['w1']:.0f}", "size": 7, "anchor": "end", "fill": ACERO})

    p += cota_h(x_ext0, x_ext1, ybase + 14, f"ext {geo['ext_x']:.2f} m")
    p += cota_v(x_ext1 + 14, ytop, ybase, f"H = {H:.2f} m")
    if ancho_ala > 0:
        p += cota_h(x0, x_ext0, ybase + 28, f"ala {ancho_ala:.2f}")

    return {"titulo": "Corte con diagrama de presiones", "ancho": W, "alto": Hpx, "primitivas": p}


def _planta(d: dict, r: dict):
    geo = r["geo"]
    losa_x, losa_y = geo["losa_x"], geo["losa_y"]
    W, H = 320, 220
    mL, mR, mT, mB = 24, 24, 20, 24
    sc = min((W - mL - mR) / losa_x, (H - mT - mB) / losa_y)
    x0, y0 = mL, mT
    ala_px = d["ancho_ala"] * sc
    ext_x_px, ext_y_px = geo["ext_x"] * sc, geo["ext_y"] * sc
    e_muro_px = max(d["espesor_muro"] * sc, 2.0)

    p = []
    if d["ancho_ala"] > 0:
        p.append({"k": "rect", "x": x0, "y": y0, "w": losa_x * sc, "h": losa_y * sc,
                  "fill": RELLENO_ZAP, "stroke": AZUL, "sw": 1.0})
    x_ext0, y_ext0 = x0 + ala_px, y0 + ala_px
    p.append({"k": "rect", "x": x_ext0, "y": y_ext0, "w": ext_x_px, "h": ext_y_px,
              "fill": "none", "stroke": AZUL, "sw": 1.6})
    p.append({"k": "rect", "x": x_ext0 + e_muro_px, "y": y_ext0 + e_muro_px,
              "w": max(ext_x_px - 2 * e_muro_px, 1.0), "h": max(ext_y_px - 2 * e_muro_px, 1.0),
              "fill": "#eaf2ff", "stroke": AZUL, "sw": 1.0})

    if geo["num_camaras"] >= 2 and geo["division_orientacion"] != "ninguna":
        e_div_px = max((d.get("espesor_muro_divisorio") or d["espesor_muro"]) * sc, 1.5)
        if geo["division_orientacion"] == "transversal":
            xc = x_ext0 + ext_x_px / 2
            p.append({"k": "rect", "x": xc - e_div_px / 2, "y": y_ext0 + e_muro_px,
                      "w": e_div_px, "h": max(ext_y_px - 2 * e_muro_px, 1.0),
                      "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.0})
        else:
            yc = y_ext0 + ext_y_px / 2
            p.append({"k": "rect", "x": x_ext0 + e_muro_px, "y": yc - e_div_px / 2,
                      "w": max(ext_x_px - 2 * e_muro_px, 1.0), "h": e_div_px,
                      "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.0})

    p += cota_h(x_ext0, x_ext0 + ext_x_px, y_ext0 + ext_y_px + 14, f"{geo['ext_x']:.2f} m")
    p += cota_v(x_ext0 - 14, y_ext0, y_ext0 + ext_y_px, f"{geo['ext_y']:.2f} m")
    return {"titulo": "Planta", "ancho": W, "alto": H, "primitivas": p}


def esquema(entradas: dict, resultado: Resultado) -> list[dict]:
    r = _motor(entradas)
    return [_planta(entradas, r), _corte(entradas, r)]


# --------------------------------------------------------------------------- #
#  Metadata / campos de entrada
# --------------------------------------------------------------------------- #
CALCULADORA = Calculadora(
    id="tanque_subterraneo",
    nombre="Tanque subterráneo de agua",
    categoria="Fundaciones y contención",
    icono="💧",
    descripcion="Predimensionamiento conceptual de un tanque de agua subterráneo: cajón de "
                "concreto armado (Tipo A) o sistema mixto con muros de bloque armado y relleno "
                "(Tipo B). No sustituye un análisis de elementos finitos.",
    referencia="Especificación técnica interna del suite (predimensionamiento conceptual).",
    funcion=calcular,
    campos=[
        # ---- Geometría ----
        Campo("convencion_dimensiones", "Convención de dimensiones", "", "cara_interior",
              grupo="Geometría", tipo="opcion",
              opciones=["cara_interior", "cara_exterior", "eje_a_eje"],
              ayuda="cara_interior = luz libre interior (lo que ocupa el agua); "
                    "cara_exterior = dimensión exterior total; "
                    "eje_a_eje = distancia entre ejes de muros opuestos."),
        Campo("largo", "Largo", "m", 4.70, grupo="Geometría",
              ayuda="Según la convención elegida arriba."),
        Campo("ancho", "Ancho", "m", 2.70, grupo="Geometría",
              ayuda="Según la convención elegida arriba."),
        Campo("alto_libre", "Alto libre (agua)", "m", 2.40, grupo="Geometría",
              ayuda="Altura interior libre, muro a muro (losa de piso a losa de techo)."),
        Campo("espesor_muro", "Espesor de muro", "m", 0.20, grupo="Geometría"),
        Campo("espesor_losa_piso", "Espesor losa de piso", "m", 0.20, grupo="Geometría"),
        Campo("espesor_losa_techo", "Espesor losa de techo", "m", 0.20, grupo="Geometría"),
        Campo("ancho_ala", "Ancho de ala perimetral", "m", 0.0, grupo="Geometría",
              ayuda="0 = sin ala. Ver 'Dimensionamiento asistido' para el ancho sugerido."),
        Campo("num_camaras", "Número de cámaras", "", 1, grupo="Cámaras", tipo="opcion",
              opciones=[1, 2], avanzado=True),
        Campo("division_orientacion", "Orientación del muro divisorio", "", "ninguna",
              grupo="Cámaras", tipo="opcion", opciones=["ninguna", "longitudinal", "transversal"],
              avanzado=True, ayuda="Solo aplica con 2 cámaras."),
        Campo("espesor_muro_divisorio", "Espesor muro divisorio", "m", 0.20, grupo="Cámaras",
              avanzado=True),

        # ---- Suelo ----
        Campo("tiene_estudio_suelos", "¿Hay estudio de suelos?", "", "No", grupo="Suelo",
              tipo="opcion", opciones=["No", "Si"]),
        Campo("gamma_saturado", "Peso unitario saturado del suelo", "kg/m3", 1800.0, grupo="Suelo",
              ayuda="Valor conservador si no hay estudio de suelos real."),
        Campo("k0", "Coeficiente de empuje en reposo K0", "", 0.5, grupo="Suelo",
              ayuda="NO usar Ka: el cajón es rígido y enterrado, no se moviliza el empuje activo."),
        Campo("profundidad_nivel_freatico", "Profundidad del nivel freático", "m", 0.0,
              grupo="Suelo", avanzado=True, ayuda="0 = caso crítico, NF en la superficie."),

        # ---- Cargas ----
        Campo("tipo_vehicular", "Carga vehicular", "", "suv_liviano", grupo="Cargas", tipo="opcion",
              opciones=["suv_liviano", "camion_mediano", "camion_pesado_hs20"]),
        Campo("carga_uniforme_equivalente", "Carga uniforme equivalente (override)", "kg/m2", 0.0,
              grupo="Cargas", avanzado=True,
              ayuda="0 = usar el valor por defecto según 'tipo' (ver tabla de referencia; "
                    "TODO verificar con norma vigente)."),
        Campo("peso_por_rueda", "Peso por rueda (override)", "kg", 0.0, grupo="Cargas", avanzado=True,
              ayuda="0 = usar el valor por defecto según 'tipo'."),
        Campo("ancho_rueda_cm", "Ancho área de contacto de rueda", "cm", 20.0, grupo="Cargas",
              avanzado=True),
        Campo("largo_rueda_cm", "Largo área de contacto de rueda", "cm", 50.0, grupo="Cargas",
              avanzado=True),
        Campo("w_acabado", "Peso del acabado (losa de techo)", "kg/m2", 100.0, grupo="Cargas"),

        # ---- Muro ----
        Campo("sistema_muro", "Sistema del muro", "", "concreto_armado", grupo="Muro", tipo="opcion",
              opciones=["concreto_armado", "bloque_armado_relleno"]),
        Campo("peso_unitario_muro", "Peso unitario del muro", "kg/m3", 2400.0, grupo="Muro",
              ayuda="Concreto armado: 2400. Bloque armado y relleno: 1900-2100 (editable, "
                    "afecta directamente la flotación)."),
        Campo("fc", "f'c (concreto) / resistencia del grout", "kg/cm2", 210.0, grupo="Muro"),
        Campo("fy", "fy (acero)", "kg/cm2", 4200.0, grupo="Muro", avanzado=True),
        Campo("recubrimiento", "Recubrimiento", "m", 0.03, grupo="Muro", avanzado=True),
        Campo("diametro_barra_vertical", "Diámetro barra vertical (mampostería)", "cm", 1.27,
              grupo="Muro", avanzado=True, ayuda="Solo aplica al sistema de bloque armado y relleno."),
        Campo("espaciamiento_celda", "Espaciamiento de celda grouteada", "cm", 40.0, grupo="Muro",
              avanzado=True, ayuda="Típicamente el módulo del bloque (40 cm es lo más común)."),
        Campo("factor_reduccion_mamposteria", "Factor de reducción de capacidad (mampostería)", "",
              0.90, grupo="Muro", avanzado=True,
              ayuda="Parámetro configurable, no un valor de norma hardcodeado; TODO verificar."),

        # ---- Sobrecimiento / viga de riostra (opcional) ----
        Campo("ancho_viga_base", "Ancho sobrecimiento / viga de riostra", "m", 0.0,
              grupo="Sobrecimiento / riostra (opcional)", avanzado=True,
              ayuda="Elemento corrido de concreto bajo TODOS los muros (perimetral + divisorio), "
                    "con seccion propia (no la del muro). 0 = no modelar (no aporta peso a la "
                    "flotacion). P.ej. un sobrecimiento/kicker tipico es 0.20 x 0.20 m; una viga "
                    "de riostra tipica 0.30 x 0.20 m."),
        Campo("alto_viga_base", "Alto sobrecimiento / viga de riostra", "m", 0.0,
              grupo="Sobrecimiento / riostra (opcional)", avanzado=True,
              ayuda="0 = no modelar."),

        # ---- Columnas de amarre ----
        Campo("espaciamiento_columnas_amarre", "Espaciamiento de columnas de amarre", "m", 2.75,
              grupo="Columnas de amarre", ayuda="Rango recomendado 2.5-3.0 m."),
        Campo("peso_propio_columna", "Peso propio de la columna", "kg", 0.0,
              grupo="Columnas de amarre", avanzado=True),
        Campo("dimension_columna_direccion_momento", "Dimensión de la columna (dir. del momento)",
              "cm", 30.0, grupo="Columnas de amarre", avanzado=True),

        # ---- Materiales generales ----
        Campo("gamma_concreto", "Peso unitario del concreto", "kg/m3", 2400.0,
              grupo="Materiales generales", avanzado=True),
        Campo("gamma_agua", "Peso unitario del agua", "kg/m3", 1000.0,
              grupo="Materiales generales", avanzado=True),
    ],
    tablas_referencia=[
        {
            "titulo": "Carga vehicular equivalente por tipo (placeholder, TODO verificar norma)",
            "nota": "Usada cuando 'Carga uniforme equivalente (override)' = 0.",
            "columnas": ["Tipo", "kg/m2", "Peso por rueda (kg)"],
            "filas": [[k, f"{v:.0f}", f"{norms.PESO_POR_RUEDA_KG[k]:.0f}"]
                      for k, v in norms.CARGA_VEHICULAR_KG_M2.items()],
        },
    ],
    esquema=esquema,
    sugerir=sugerir,
)
