"""
Zapata cuadrada con pedestal.

Diseno de zapata aislada cuadrada sometida a carga axial y momento, con
verificacion de corte, punzonado, aplastamiento, factor gamma y diseno del acero.

Referencia:  Enrique Araujo - "Suelos, Fundaciones y Muros".
Este modulo reproduce, celda por celda, la hoja de calculo original
(validado en tests/test_zapata.py contra los 24 valores del Excel).
"""
from __future__ import annotations

import math

from motor.base import Calculadora, Campo, Chequeo, Resultado, Valor
from motor.dibujo import cota_h, cota_v, AZUL, GRIS, RELLENO_ZAP, RELLENO_PED, ACERO
from datos.suelos import TABLAS_SUELO, GUIA_SIGMA_ADM
from datos.acero import sugerir_armado, TABLA_7_4


# --------------------------------------------------------------------------- #
#  Motor de calculo puro  (sin dependencias de interfaz)
# --------------------------------------------------------------------------- #
def _motor(d: dict) -> dict:
    Pu          = d["Pu"]
    M           = d["M"]
    sigma_adm   = d["sigma_adm"]
    gamma_asum  = d["gamma_asumido"]
    fc          = d["fc"]
    fy          = d["fy"]
    H           = d["H"]
    gamma_s     = d["gamma_s"]
    gamma_c     = d["gamma_c"]
    b_ped       = d["b_ped"]
    mu          = d["mu"]
    B_adop      = d["B_adop"]
    d_adop      = d["d_adop"]
    phi_corte   = d["phi_corte"]
    phi_aplast  = d["phi_aplast"]
    phi_flexion = d["phi_flexion"]
    ju          = d["ju"]

    M_cm = M * 100.0          # momento en kg*cm
    B_cm = B_adop * 100.0     # ancho B en cm
    d_m  = d_adop / 100.0     # d en m
    b_m  = b_ped / 100.0      # pedestal en m

    r = {}
    # --- Dimensionamiento en planta ---
    r["Areq"]    = (gamma_asum * Pu) / sigma_adm
    r["B_calc"]  = math.sqrt(r["Areq"])
    r["sigma_u"] = Pu / r["Areq"]
    # --- Altura ---
    r["d_min"]   = math.sqrt(M / (mu * fc * B_adop))
    r["n"]       = B_cm / 2 - b_ped / 2
    r["c"]       = r["n"] - d_adop
    r["Mu"]      = (r["sigma_u"] * B_cm * r["n"] ** 2) / 2
    # --- Corte (una direccion) ---
    r["Vu"]  = r["sigma_u"] * B_cm * r["c"]
    r["Vc"]  = 0.53 * math.sqrt(fc)
    r["Vu1"] = r["Vu"] / (phi_corte * B_cm * d_adop)
    r["corte_ok"] = r["Vu1"] < r["Vc"]
    # --- Punzonado (dos direcciones) ---
    r["Vu2"] = Pu - r["sigma_u"] * (b_ped + d_adop) ** 2
    r["bo"]  = 4 * (b_ped + d_adop)
    r["Vc1"] = 1.06 * math.sqrt(fc)
    r["Vu3"] = r["Vu2"] / (phi_corte * r["bo"] * d_adop)
    r["punz_ok"] = r["Vu3"] < r["Vc1"]
    # --- Aplastamiento ---
    r["Ag"] = b_ped ** 2
    r["Pu_max_col"]  = phi_aplast * (0.85 * fc * r["Ag"])
    r["aplast_col_ok"] = r["Pu_max_col"] > Pu
    r["Pu_max_base"] = 535 * math.sqrt(B_cm / b_ped)
    r["lim_base"]    = 2 * 535.5
    r["aplast_base_ok"] = r["Pu_max_base"] < r["lim_base"]
    # --- Verificacion del factor gamma ---
    r["Q1"] = B_adop ** 2 * d_m * gamma_c
    r["Q2"] = (B_adop ** 2 - b_m ** 2) * (H - d_m) * gamma_s
    r["Q"]  = r["Q1"] + r["Q2"]
    r["gamma_real"] = (Pu + r["Q"]) / Pu
    # --- Acero de flexion ---
    r["As"]   = (M_cm * 10) / (phi_flexion * fy * ju * d_adop)
    r["As_m"] = r["As"] / B_adop
    return r


# --------------------------------------------------------------------------- #
#  Adaptador -> Resultado (lo que consume la interfaz y el reporte)
# --------------------------------------------------------------------------- #
def calcular(d: dict) -> Resultado:
    r = _motor(d)
    res = Resultado()

    res.valores = [
        Valor("Areq",    "Area requerida",            r["Areq"],    "cm²",     "γ·Pu / σadm",           1),
        Valor("B_calc",  "Lado B calculado",          r["B_calc"],  "cm",      "√Areq",                 2),
        Valor("B_adop",  "Lado B adoptado",           d["B_adop"],  "m",       "adoptado",              2),
        Valor("sigma_u", "Presion ultima σu",         r["sigma_u"], "kg/cm²",  "Pu / Areq",             3),
        Valor("d_min",   "Altura util minima",        r["d_min"],   "cm",      "√(M / (µ·f'c·B))",      2),
        Valor("d_adop",  "Altura util adoptada",      d["d_adop"],  "cm",      "adoptado",              1),
        Valor("n",       "Volado n",                  r["n"],       "cm",      "B/2 − b/2",             2),
        Valor("c",       "Distancia c",               r["c"],       "cm",      "n − d",                 2),
        Valor("Mu",      "Momento ultimo Mu",         r["Mu"],      "kg·cm",   "σu·B·n² / 2",           1),
        Valor("Ag",      "Area gruesa pedestal",      r["Ag"],      "cm²",     "b²",                    0),
        Valor("Q",       "Peso zapata + relleno",     r["Q"],       "kg",      "Q1 + Q2",               1),
        Valor("gamma_real", "Factor γ real",          r["gamma_real"], "",     "(Pu + Q) / Pu",         3),
        Valor("As",      "Acero total As",            r["As"],      "cm²",     "M·10 / (φ·fy·ju·d)",    3),
        Valor("As_m",    "Acero por metro",           r["As_m"],    "cm²/m",   "As / B",                3),
    ]

    res.chequeos = [
        Chequeo("Corte a una direccion",
                f"Vu1 = {r['Vu1']:.3f}", "<", f"Vc = {r['Vc']:.3f} kg/cm²",
                r["corte_ok"]),
        Chequeo("Punzonado (dos direcciones)",
                f"Vu3 = {r['Vu3']:.3f}", "<", f"Vc = {r['Vc1']:.3f} kg/cm²",
                r["punz_ok"]),
        Chequeo("Aplastamiento en columna",
                f"Pu.máx = {r['Pu_max_col']:.0f} kg", ">", f"P = {d['Pu']:.0f} kg",
                r["aplast_col_ok"]),
        Chequeo("Aplastamiento en base",
                f"Pu.máx-base = {r['Pu_max_base']:.0f}", "<", f"2·535.5 = {r['lim_base']:.0f} kg",
                r["aplast_base_ok"]),
        Chequeo("Factor γ",
                f"γ real = {r['gamma_real']:.3f}", "≈", f"γ asumido = {d['gamma_asumido']:.2f}",
                abs(r["gamma_real"] - d["gamma_asumido"]) <= 0.05,
                "El γ real debe aproximarse al asumido; ajuste B, d o H si difiere."),
    ]

    res.resumen = [
        Valor("B_adop", "Dimensiones en planta", d["B_adop"], "m × m",  "", 2),
        Valor("d_adop", "Altura util d",         d["d_adop"], "cm",     "", 0),
        Valor("As_m",   "Acero requerido",       r["As_m"],   "cm²/m",  "", 2),
    ]

    # Sugerencia de armado entrando en la Tabla 7.4 con el As requerido
    armado = sugerir_armado(r["As_m"])
    if armado:
        res.armado_texto = armado.texto
        res.notas.append(
            f"Armado sugerido: {armado.texto} en ambos sentidos (a/s) — "
            f"provee {armado.As_provisto:.2f} cm²/m ≥ {r['As_m']:.2f} cm²/m requerido."
        )

    return res


# --------------------------------------------------------------------------- #
#  Esquema (dibujo) de la zapata: corte + planta
# --------------------------------------------------------------------------- #
def _valor(res: Resultado, clave: str, defecto=0.0):
    for v in res.valores:
        if v.clave == clave:
            return v.valor
    return defecto


def _corte(B_cm, d_cm, b_cm):
    W, H = 300, 220
    mL, mR, mT, mB = 48, 18, 34, 40
    pedH = max(28.0, 0.9 * d_cm)
    sc = min((W - mL - mR) / B_cm, (H - mT - mB) / (d_cm + pedH))
    Bpx, dpx, bpx, pedpx = B_cm * sc, d_cm * sc, b_cm * sc, pedH * sc
    x0 = mL
    ybase = H - mB
    ytop = ybase - dpx
    pedx = x0 + (Bpx - bpx) / 2
    p = []
    # linea de terreno (nivel superior de la zapata)
    p.append({"k": "line", "x1": x0 - 6, "y1": ytop, "x2": x0 + Bpx + 6, "y2": ytop,
              "stroke": "#9aa7b5", "sw": 0.8, "dash": True})
    # zapata y pedestal
    p.append({"k": "rect", "x": x0, "y": ytop, "w": Bpx, "h": dpx,
              "fill": RELLENO_ZAP, "stroke": AZUL, "sw": 1.4})
    p.append({"k": "rect", "x": pedx, "y": ytop - pedpx, "w": bpx, "h": pedpx,
              "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.4})
    # acero de fondo (linea + ganchos)
    ya = ybase - 5
    p.append({"k": "line", "x1": x0 + 5, "y1": ya, "x2": x0 + Bpx - 5, "y2": ya,
              "stroke": ACERO, "sw": 1.6})
    p.append({"k": "line", "x1": x0 + 5, "y1": ya, "x2": x0 + 5, "y2": ya - 7, "stroke": ACERO, "sw": 1.6})
    p.append({"k": "line", "x1": x0 + Bpx - 5, "y1": ya, "x2": x0 + Bpx - 5, "y2": ya - 7, "stroke": ACERO, "sw": 1.6})
    # cotas
    p += cota_h(x0, x0 + Bpx, ybase + 18, f"B = {B_cm/100:.2f} m")
    p += cota_v(x0 - 18, ytop, ybase, f"d = {d_cm:.0f} cm")
    p += cota_h(pedx, pedx + bpx, ytop - pedpx - 8, f"b = {b_cm:.0f} cm", arriba=True)
    return {"titulo": "Corte", "ancho": W, "alto": H, "primitivas": p}


def _planta(B_cm, d_cm, b_cm, As_m):
    W, H = 300, 220
    mL, mR, mT, mB = 26, 26, 22, 46
    sc = min((W - mL - mR), (H - mT - mB)) / B_cm
    Bpx, bpx = B_cm * sc, b_cm * sc
    x0 = (W - Bpx) / 2
    y0 = mT
    px = x0 + (Bpx - bpx) / 2
    py = y0 + (Bpx - bpx) / 2
    p = []
    # malla de acero (lineas finas en ambos sentidos)
    n = 7
    for i in range(1, n):
        xx = x0 + Bpx * i / n
        p.append({"k": "line", "x1": xx, "y1": y0 + 4, "x2": xx, "y2": y0 + Bpx - 4,
                  "stroke": ACERO, "sw": 0.6})
        yy = y0 + Bpx * i / n
        p.append({"k": "line", "x1": x0 + 4, "y1": yy, "x2": x0 + Bpx - 4, "y2": yy,
                  "stroke": ACERO, "sw": 0.6})
    # contorno zapata y pedestal
    p.append({"k": "rect", "x": x0, "y": y0, "w": Bpx, "h": Bpx,
              "fill": None, "stroke": AZUL, "sw": 1.4})
    p.append({"k": "rect", "x": px, "y": py, "w": bpx, "h": bpx,
              "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.2})
    p.append({"k": "text", "x": x0 + Bpx / 2, "y": py - 4, "s": "pedestal",
              "size": 7.5, "anchor": "middle", "fill": GRIS})
    # cotas B en dos lados
    p += cota_h(x0, x0 + Bpx, y0 + Bpx + 16, f"B = {B_cm/100:.2f} m")
    p += cota_v(x0 - 12, y0, y0 + Bpx, f"B = {B_cm/100:.2f} m")
    # etiqueta de acero
    p.append({"k": "text", "x": W / 2, "y": H - 8, "s": f"As = {As_m:.2f} cm2/m (a/s)",
              "size": 8.5, "anchor": "middle", "fill": ACERO, "bold": True})
    return {"titulo": "Planta", "ancho": W, "alto": H, "primitivas": p}


def esquema(entradas: dict, res: Resultado):
    B_cm = entradas["B_adop"] * 100
    d_cm = entradas["d_adop"]
    b_cm = entradas["b_ped"]
    As_m = _valor(res, "As_m")
    return [_corte(B_cm, d_cm, b_cm), _planta(B_cm, d_cm, b_cm, As_m)]


# --------------------------------------------------------------------------- #
#  Dimensionamiento asistido: sugiere B y d que hacen cumplir las verificaciones
# --------------------------------------------------------------------------- #
def sugerir(d: dict) -> dict:
    """Sugiere {B_adop, d_adop} (y b_ped si hace falta) minimos, a medidas
    constructivas, que hacen cumplir corte, punzonado y aplastamiento.
    El resto de los datos se mantiene. Los campos siguen siendo editables."""
    base = dict(d)
    b = base["b_ped"]

    # Punto fijo: B (por area del suelo) y b (por aplastamiento) se acoplan
    B = base["B_adop"]
    for _ in range(6):
        Areq = (base["gamma_asumido"] * base["Pu"]) / base["sigma_adm"]
        B_area = math.sqrt(Areq) / 100.0                        # m
        B = max(math.ceil(B_area / 0.05) * 0.05, b / 100.0 + 0.20)
        B = round(B, 2)
        B_cm = B * 100.0
        # pedestal minimo: aplastamiento en base (B_cm/b < 4.007) y en columna
        b_base = B_cm / 4.0
        b_col = math.sqrt(base["Pu"] / (0.595 * base["fc"]))
        b_nuevo = max(b, math.ceil(max(b_base, b_col) / 5.0) * 5.0)
        if abs(b_nuevo - b) < 1:
            b = b_nuevo
            break
        b = b_nuevo

    # d minimo (paso 5 cm) que pase corte y punzonado
    d_adop = 20
    while d_adop <= 200:
        r = _motor(dict(base, B_adop=B, d_adop=d_adop, b_ped=b))
        if r["corte_ok"] and r["punz_ok"]:
            break
        d_adop += 5

    sug = {"B_adop": B, "d_adop": float(d_adop)}
    if b != base["b_ped"]:
        sug["b_ped"] = float(b)
    return sug


# --------------------------------------------------------------------------- #
#  Declaracion de la calculadora
# --------------------------------------------------------------------------- #
CALCULADORA = Calculadora(
    id="zapata_pedestal",
    nombre="Zapata cuadrada con pedestal",
    categoria="Fundaciones",
    icono="🏗️",
    descripcion=(
        "Diseno de zapata aislada cuadrada con pedestal, sometida a carga axial y "
        "momento. Calcula dimension en planta, altura util y acero, y verifica "
        "corte, punzonado, aplastamiento y el factor γ."
    ),
    referencia="E. Araujo — Suelos, Fundaciones y Muros",
    campos=[
        # --- Cargas ---
        Campo("Pu", "Carga ultima axial  Pu", "kg", 20870, grupo="Cargas",
              ayuda="Reaccion axial mayorada en la base de la columna.", minimo=0),
        Campo("M", "Momento  M", "kg·m", 1101.22, grupo="Cargas",
              ayuda="Momento mayorado en la base.", minimo=0),

        # --- Suelo ---
        Campo("sigma_adm", "Capacidad portante de diseño  σadm", "kg/cm²", 1.5,
              grupo="Suelo", ayuda="σadm de diseño empleada para el area (E16 del Excel).",
              minimo=0.1),
        Campo("gamma_asumido", "Factor γ asumido", "", 1.2, grupo="Suelo",
              ayuda="Segun profundidad H (pág. 253). 1.5 m < H < 3 m → γ ≈ 1.2.",
              minimo=1.0, maximo=1.6, paso=0.05),
        Campo("H", "Profundidad de la fundacion  H", "m", 2.0, grupo="Suelo",
              minimo=0.5, paso=0.1),
        Campo("gamma_s", "Peso unitario del suelo  γs", "kg/m³", 2200, grupo="Suelo",
              minimo=1000),

        # --- Materiales ---
        Campo("fc", "Resistencia del concreto  f'c", "kg/cm²", 210, grupo="Materiales",
              minimo=100),
        Campo("fy", "Fluencia del acero  fy", "kg/cm²", 4200, grupo="Materiales",
              minimo=2000),
        Campo("gamma_c", "Peso unitario del concreto  γc", "kg/m³", 2500,
              grupo="Materiales", minimo=2000),

        # --- Geometria ---
        Campo("b_ped", "Lado del pedestal  b", "cm", 35, grupo="Geometria",
              ayuda="Pedestal cuadrado (b × b).", minimo=10),
        Campo("mu", "Coeficiente µ", "", 0.1448, grupo="Geometria",
              ayuda="Coeficiente para la altura util minima (pág. 214).", minimo=0.001),
        Campo("B_adop", "Lado B adoptado", "m", 1.1, grupo="Geometria",
              ayuda="Dimension en planta adoptada (≥ B calculado).", minimo=0.3, paso=0.05),
        Campo("d_adop", "Altura util d adoptada", "cm", 35, grupo="Geometria",
              ayuda="Altura util adoptada (≥ d minimo).", minimo=5),

        # --- Factores (avanzado) ---
        Campo("phi_corte", "φ corte", "", 0.85, grupo="Factores de reduccion",
              avanzado=True, minimo=0.5, maximo=1.0, paso=0.05),
        Campo("phi_aplast", "φ aplastamiento", "", 0.70, grupo="Factores de reduccion",
              avanzado=True, minimo=0.5, maximo=1.0, paso=0.05),
        Campo("phi_flexion", "φ flexion", "", 0.90, grupo="Factores de reduccion",
              avanzado=True, minimo=0.5, maximo=1.0, paso=0.05),
        Campo("ju", "ju (brazo interno)", "", 0.90, grupo="Factores de reduccion",
              avanzado=True, minimo=0.5, maximo=1.0, paso=0.05),
    ],
    funcion=calcular,
    tablas_referencia=TABLAS_SUELO + [TABLA_7_4],
    guia_suelo=GUIA_SIGMA_ADM,
    guia_suelo_destino="sigma_adm",
    esquema=esquema,
    sugerir=sugerir,
)
