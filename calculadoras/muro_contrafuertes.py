"""
Muro de contencion con contrafuertes.

Diseno de un muro de contencion con contrafuertes (empuje activo/pasivo,
estabilidad global, fuste entre contrafuertes, talon, puntera y contrafuertes).

Referencia:  Maria Fratelli - "Suelos, Fundaciones y Muros", Capitulo 15.
Validado contra el Ejemplo 15.3 del libro (tests/test_muro_contrafuertes.py).

NOTA DE DESARROLLO (fase 1-4 de 5): implementados empujes, estabilidad global,
fuste, talon, puntera y contrafuerte (seccion critica en la base, con canto
adoptado). Faltan el esquema (dibujo) y el predimensionado asistido (sugerir).

NOTA DE TERMINOLOGIA: la geometria del Ejemplo 15.3 se reconstruyo a partir
de los brazos de la tabla de estabilidad del libro (5 coincidencias exactas
independientes). Este modulo usa terminologia estandar: "puntera" = lado sin
tierra encima (junto al punto de momentos por vuelco), "talon" = lado con
tierra retenida + sobrecarga + contrafuerte. Los bloques de numeros que el
libro rotula "Talon"/"Puntera" en la seccion del ejemplo parecen estar
intercambiados respecto a esta convencion -- verificar contra la figura 15.x
si se dispone del libro.
"""
from __future__ import annotations

import math

from motor.base import Calculadora, Campo, Chequeo, Resultado, Valor
from motor.dibujo import cota_h, cota_v, AZUL, GRIS, RELLENO_ZAP, RELLENO_PED, ACERO


# --------------------------------------------------------------------------- #
#  Tablas de placas (3 bordes empotrados, 1 libre) - Fratelli Cap. 15, tablas
#  15.1 (carga uniforme) y 15.2 (carga triangular).
#  Columnas: B/L, alfa1, beta1, alfa2, beta2, beta2p, beta3, gamma3, beta4,
#            gamma4, beta5, gamma5
# --------------------------------------------------------------------------- #
TABLA_PLACAS_UNIFORME = [
    (0.6, 0.00271, 0.0336, 0.00129, 0.0168, 0.0074, -0.0745, 0.750, -0.0365, 0.297, -0.0554, 0.416),
    (0.7, 0.00292, 0.0371, 0.00159, 0.0212, 0.0097, -0.0782, 0.717, -0.0139, 0.346, -0.0545, 0.413),
    (0.8, 0.00308, 0.0401, 0.00185, 0.0252, 0.0116, -0.0812, 0.685, -0.0505, 0.385, -0.0535, 0.410),
    (0.9, 0.00323, 0.0425, 0.00209, 0.0287, 0.0129, -0.0836, 0.656, -0.0563, 0.414, -0.0523, 0.406),
    (1.0, 0.00333, 0.0444, 0.00230, 0.0317, 0.0138, -0.0853, 0.628, -0.0614, 0.435, -0.0510, 0.401),
    (1.25, 0.00345, 0.0447, 0.00269, 0.0374, 0.0142, -0.0867, 0.570, -0.0708, 0.475, -0.0470, 0.388),
    (1.5, 0.00335, 0.0454, 0.00290, 0.0402, 0.0118, -0.0842, 0.527, -0.0755, 0.491, -0.0418, 0.373),
]

TABLA_PLACAS_TRIANGULAR = [
    (0.6, 0.00069, 0.0089, 0.00044, 0.0060, 0.0062, -0.0179, 0.093, -0.0131, 0.136, -0.0242, 0.248),
    (0.7, 0.00069, 0.0093, 0.00058, 0.0080, 0.0074, -0.0172, 0.081, -0.0170, 0.158, -0.0264, 0.262),
    (0.8, 0.00068, 0.0096, 0.00072, 0.0100, 0.0083, -0.0164, 0.069, -0.0206, 0.177, -0.0278, 0.275),
    (0.9, 0.00067, 0.0096, 0.00085, 0.0118, 0.0090, -0.0156, 0.057, -0.0239, 0.194, -0.0290, 0.286),
    (1.0, 0.00065, 0.0095, 0.00097, 0.0135, 0.0094, -0.0146, 0.045, -0.0269, 0.209, -0.0299, 0.295),
    (1.25, 0.00056, 0.0085, 0.00121, 0.0169, 0.0092, -0.0119, 0.018, -0.0327, 0.234, -0.0306, 0.309),
    (1.5, 0.00042, 0.0065, 0.00138, 0.0191, 0.0075, -0.0087, -0.006, -0.0364, 0.245, -0.0291, 0.311),
]

_COLS_PLACA = ["alfa1", "beta1", "alfa2", "beta2", "beta2p", "beta3", "gamma3", "beta4", "gamma4", "beta5", "gamma5"]


def _tabla_placa_a_referencia(tabla, titulo, nota):
    columnas = ["B/L"] + [f"{c}" for c in ["a1", "b1", "a2", "b2", "b2'", "b3", "g3", "b4", "g4", "b5", "g5"]]
    filas = []
    for fila in tabla:
        filas.append([f"{fila[0]:g}"] + [f"{v:.4f}" for v in fila[1:]])
    return {"titulo": titulo, "nota": nota, "columnas": columnas, "filas": filas}


TABLA_FUSTE_UNIFORME = _tabla_placa_a_referencia(
    TABLA_PLACAS_UNIFORME,
    "Placa con 3 bordes empotrados y 1 libre - carga uniforme",
    "Mx=b.q.L2, My=b'.q.L2, V=g.q.L. Puntos: 1(x=0,y=B) 2(x=0,y=B/2) 3(x=L/2,y=B) 4(x=L/2,y=B/2) 0(x=0,y=0).",
)
TABLA_FUSTE_TRIANGULAR = _tabla_placa_a_referencia(
    TABLA_PLACAS_TRIANGULAR,
    "Placa con 3 bordes empotrados y 1 libre - carga triangular (q0 = presion maxima en la base)",
    "Mx=b.q0.L2, My=b'.q0.L2, V=g.q0.L. Puntos: 1(x=0,y=B) 2(x=0,y=B/2) 3(x=L/2,y=B) 4(x=L/2,y=B/2) 0(x=0,y=0).",
)


def _interp_tabla_placa(tabla, bl):
    """Interpola los coeficientes de la tabla de placas para una relacion B/L dada."""
    filas = tabla
    bl = min(max(bl, filas[0][0]), filas[-1][0])
    for i in range(len(filas) - 1):
        b0, b1 = filas[i][0], filas[i + 1][0]
        if b0 <= bl <= b1:
            t = 0.0 if b1 == b0 else (bl - b0) / (b1 - b0)
            f0, f1 = filas[i][1:], filas[i + 1][1:]
            vals = [v0 + t * (v1 - v0) for v0, v1 in zip(f0, f1)]
            return dict(zip(_COLS_PLACA, vals))
    f = filas[-1][1:]
    return dict(zip(_COLS_PLACA, f))


# --------------------------------------------------------------------------- #
#  Motor de calculo puro
# --------------------------------------------------------------------------- #
def _motor(d: dict) -> dict:
    r = {}

    # ---------------- datos ----------------
    gs, phi, beta = d["gs"], d["phi"], d["beta"]
    c = d["c"] * 10000.0        # kg/cm2 -> kg/m2
    gs2, phi2, sigma_adm = d["gs2"], d["phi2"], d["sigma_adm"]
    c2 = d["c2"] * 10000.0      # kg/cm2 -> kg/m2
    q = d["q"]
    fc, fy, gc = d["fc"], d["fy"], d["gc"]
    H = d["H"]
    B, Bp, D = d["B_adop"], d["Bprima_adop"], d["D_adop"]
    puntera, L, t = d["puntera_adop"], d["L_adop"], d["t_adop"]
    Dp = d["Dp_adop"]
    mu, ju = d["mu"], d["ju"]
    phi_corte, phi_flexion = d["phi_corte"], d["phi_flexion"]
    coef_tanphi_p = d["coef_tanphi_p"]
    coef_c_p = d["coef_c_p"]
    talon_d_adop = d["talon_d_adop"]
    puntera_d_adop = d["puntera_d_adop"]
    fuste_d_adop = d["fuste_d_adop"]

    Bpanel = H - D
    talon = B - Bp - puntera
    r["Bpanel"] = Bpanel
    r["talon"] = talon

    # ---------------- 1. Coeficientes de empuje ----------------
    Ka = math.tan(math.radians(45 - phi / 2)) ** 2
    Kp = math.tan(math.radians(45 + phi2 / 2)) ** 2
    r["Ka"], r["Kp"] = Ka, Kp

    # ---------------- 2. Empuje activo ----------------
    def sigma_a(z):
        return (q + gs * z) * Ka - 2 * c * math.sqrt(Ka)

    z0 = (2 * c * math.sqrt(Ka) - q * Ka) / (gs * Ka)
    z0 = max(z0, 0.0)
    H_ef = max(H - z0, 0.0)
    sigma_a_max = sigma_a(H)
    Ea = sigma_a_max * H_ef / 2
    brazo_Ea = H_ef / 3     # sobre el pie (base)
    Eav = Ea * math.sin(math.radians(beta))
    Eah = Ea * math.cos(math.radians(beta))
    r.update(z0=z0, H_ef=H_ef, sigma_a_max=sigma_a_max, Ea=Ea, brazo_Ea=brazo_Ea,
              Eav=Eav, Eah=Eah)

    # ---------------- 2b. Empuje pasivo ----------------
    sigma_p1 = 2 * c2 * math.sqrt(Kp)
    sigma_p_max = sigma_p1 + gs2 * Dp * Kp
    Ep = (sigma_p1 + sigma_p_max) * Dp / 2
    # brazo (altura sobre la base) del resultante del trapecio pasivo
    area_rect = sigma_p1 * Dp
    area_tri = (sigma_p_max - sigma_p1) * Dp / 2
    h2 = (area_rect * (Dp / 2) + area_tri * (Dp / 3)) / Ep if Ep > 0 else 0.0
    r.update(sigma_p1=sigma_p1, sigma_p_max=sigma_p_max, Ep=Ep, h2=h2)

    # ---------------- 3. Pesos y brazos (respecto al pie/toe, punto I) ----------------
    x_puntera = puntera / 2
    x_stem = puntera + Bp / 2
    x_slab = B / 2
    x_talon = puntera + Bp + talon / 2
    x_ctf = puntera + Bp + talon / 3     # centroide de la cuna triangular del contrafuerte

    W1 = Bp * Bpanel * gc                      # fuste
    W2 = B * D * gc                            # losa de base completa
    W3 = talon * Bpanel * gs                   # suelo sobre el talon
    Wq = q * talon                             # sobrecarga sobre el talon
    Vol_ctf = 0.5 * talon * Bpanel * t
    W4 = Vol_ctf * gc / L                       # contrafuerte, repartido por metro

    R = W1 + W2 + W3 + Wq + W4 + Eav
    M_estab = (W1 * x_stem + W2 * x_slab + W3 * x_talon + Wq * x_talon
               + W4 * x_ctf + Eav * B)
    M_volc = Eah * brazo_Ea

    r.update(W1=W1, W2=W2, W3=W3, Wq=Wq, W4=W4, R=R, M_estab=M_estab, M_volc=M_volc,
              x_stem=x_stem, x_slab=x_slab, x_talon=x_talon, x_ctf=x_ctf)

    # ---------------- 4. Verificaciones de estabilidad ----------------
    FS_volc_sin = M_estab / M_volc
    FS_volc_con = (M_estab + Ep * h2) / M_volc

    tanphi_p = coef_tanphi_p * math.tan(math.radians(phi2))
    cp = coef_c_p * c2
    Fr = R * tanphi_p + cp * B
    FS_desliz_sin = Fr / Eah
    FS_desliz_con = (Fr + Ep) / Eah

    x_R = (M_estab - M_volc) / R
    e = B / 2 - x_R
    sigma_max = R / B * (1 + 6 * e / B)
    sigma_min = R / B * (1 - 6 * e / B)

    r.update(FS_volc_sin=FS_volc_sin, FS_volc_con=FS_volc_con,
              Fr=Fr, FS_desliz_sin=FS_desliz_sin, FS_desliz_con=FS_desliz_con,
              x_R=x_R, e=e, sigma_max=sigma_max, sigma_min=sigma_min,
              volc_ok=FS_volc_sin >= 1.5, desliz_ok=FS_desliz_sin >= 1.5,
              exc_ok=e <= B / 6, contacto_ok=(sigma_max <= sigma_adm * 10000 and sigma_min >= 0))

    # ---------------- 5. Fuste (metodo de placas, tabla 15.2 triangular) ----------------
    q0 = sigma_a(Bpanel)
    r["q0"] = q0
    BL = Bpanel / L
    r["BL"] = BL
    coef = _interp_tabla_placa(TABLA_PLACAS_TRIANGULAR, BL)
    q0L2 = q0 * L ** 2
    r["q0L2"] = q0L2
    Mx1 = coef["beta1"] * q0L2
    Mx2 = coef["beta2"] * q0L2
    My2 = coef["beta2p"] * q0L2
    Mx3 = coef["beta3"] * q0L2
    Mx4 = coef["beta4"] * q0L2
    My0 = coef["beta5"] * q0L2
    momentos_fuste = {"Mx1": Mx1, "Mx2": Mx2, "My2": My2, "Mx3": Mx3, "Mx4": Mx4, "My0": My0}
    r.update(momentos_fuste)
    clave_gob, M_fuste_gob = max(momentos_fuste.items(), key=lambda kv: abs(kv[1]))
    Mu_fuste = 1.7 * abs(M_fuste_gob)
    d_min_fuste = math.sqrt(Mu_fuste * 100 / (mu * fc * 100))
    As_fuste = Mu_fuste * 100 / (phi_flexion * fy * ju * fuste_d_adop)
    Vc = 0.53 * math.sqrt(fc)
    V_fuste = coef["gamma5"] * q0 * L        # reaccion (aprox.) sobre contrafuerte, referencia
    vu_fuste = 1.7 * V_fuste / (phi_corte * 100 * fuste_d_adop)
    r.update(clave_fuste_gob=clave_gob, M_fuste_gob=M_fuste_gob, Mu_fuste=Mu_fuste,
              d_min_fuste=d_min_fuste, As_fuste=As_fuste, Vc=Vc,
              V_fuste=V_fuste, vu_fuste=vu_fuste, fuste_flexion_ok=fuste_d_adop >= d_min_fuste,
              fuste_corte_ok=vu_fuste <= Vc)

    # ---------------- 6. Talon y puntera ----------------
    def sigma_base(x):
        # x medido desde el pie (toe, x=0, donde ocurre sigma_max) hasta el talon (x=B)
        return sigma_max - (sigma_max - sigma_min) * (x / B)

    # Talon: voladizo empotrado en el fuste, carga neta hacia abajo
    # (peso propio + tierra + sobrecarga) - reaccion del suelo
    N = 400
    x0_t = puntera + Bp
    h_t = talon / N
    V1_talon = 0.0
    M1_talon = 0.0
    for i in range(N):
        xi = (i + 0.5) * h_t
        x = x0_t + xi
        w = (D * gc + Bpanel * gs + q) - sigma_base(x)
        V1_talon += w * h_t
        M1_talon += w * xi * h_t
    Mu_talon = 1.7 * M1_talon
    d_min_talon = math.sqrt(Mu_talon * 100 / (mu * fc * 100))
    As_talon = Mu_talon * 100 / (phi_flexion * fy * ju * talon_d_adop)
    vu_talon = 1.7 * V1_talon / (phi_corte * 100 * talon_d_adop)

    # Puntera: voladizo empotrado en el fuste, carga neta hacia arriba
    # (reaccion del suelo - peso propio); C/L determina el criterio de analisis
    CL = puntera / L
    h_p = puntera / N
    V1_punt = 0.0
    M1_punt = 0.0
    for i in range(N):
        xi = (i + 0.5) * h_p
        x = puntera - xi
        w = sigma_base(x) - D * gc
        V1_punt += w * h_p
        M1_punt += w * xi * h_p
    Mu_punt = 1.7 * M1_punt
    d_min_punt = math.sqrt(Mu_punt * 100 / (mu * fc * 100))
    As_punt = Mu_punt * 100 / (phi_flexion * fy * ju * puntera_d_adop)
    vu_punt = 1.7 * V1_punt / (phi_corte * 100 * puntera_d_adop)

    r.update(V1_talon=V1_talon, M1_talon=M1_talon, Mu_talon=Mu_talon,
              d_min_talon=d_min_talon, As_talon=As_talon, vu_talon=vu_talon,
              talon_flexion_ok=talon_d_adop >= d_min_talon, talon_corte_ok=vu_talon <= Vc,
              CL=CL, V1_punt=V1_punt, M1_punt=M1_punt, Mu_punt=Mu_punt,
              d_min_punt=d_min_punt, As_punt=As_punt, vu_punt=vu_punt,
              punt_flexion_ok=puntera_d_adop >= d_min_punt, punt_corte_ok=vu_punt <= Vc)

    # ---------------- 7. Contrafuerte: seccion critica (base) ----------------
    # Viga en voladizo vertical (altura = Bpanel) bajo empuje triangular directo
    # sobre el ancho tributario L. Se evalua en la base (la seccion mas cargada),
    # de forma conservadora frente al metodo de "n" secciones del libro.
    h_ctf = d["h_ctf_base"] * 100          # canto adoptado, m -> cm
    Bpanel_cm = Bpanel * 100
    sigma_B_ctf = gs * Bpanel * Ka                     # kg/m2, presion en la base (15.38)
    sigma_L_ctf = sigma_B_ctf * L                       # kg/m, carga lineal (15.38->15.42)
    EaL_ctf = sigma_L_ctf * Bpanel / 2                  # kg, resultante triangular (15.42)
    V_ctf = EaL_ctf
    M_ctf = EaL_ctf * (Bpanel / 3)                      # kg.m, brazo del triangulo
    Mu_ctf = 1.7 * M_ctf
    theta_ctf = math.atan(h_ctf / Bpanel_cm)            # pendiente del paramento inclinado
    d_ctf = 0.9 * h_ctf
    As_ctf = (Mu_ctf * 100) / (phi_flexion * fy * ju * d_ctf) / math.cos(theta_ctf)
    As_min_ctf = 0.18 * d_ctf     # retraccion/temperatura, por metro de ancho (referencia)
    vu_ctf = 1.7 * V_ctf / (phi_corte * t * 100 * d_ctf)
    ctf_flexion_ok = As_ctf >= 0  # siempre calculable; d se adopta, no se verifica contra d_min aqui
    ctf_corte_ok = vu_ctf <= Vc   # si no cumple, requiere estribos (no se disena aqui)

    r.update(sigma_B_ctf=sigma_B_ctf, EaL_ctf=EaL_ctf, V_ctf=V_ctf, M_ctf=M_ctf,
              Mu_ctf=Mu_ctf, theta_ctf=theta_ctf, d_ctf=d_ctf, As_ctf=As_ctf,
              As_min_ctf=As_min_ctf, vu_ctf=vu_ctf, ctf_corte_ok=ctf_corte_ok,
              ctf_necesita_estribos=not ctf_corte_ok)

    # ---------------- Verificacion rapida (opcional): criterio de Huntington ----------------
    # ADVERTENCIA: la formula de M- tal como aparece en la fuente no cierra
    # dimensionalmente (da kg en vez de kg.m); se deja aqui SOLO como referencia,
    # sin validar contra el Ejemplo 15.3, y no participa en ningun Chequeo.
    hunt_M_neg = 0.003 * sigma_B_ctf * L * Bpanel      # kg (dimension inconsistente, ver nota)
    hunt_M_pos = hunt_M_neg / 4
    hunt_V = 0.2 * sigma_B_ctf * Bpanel                # kg/m (dimension inconsistente, ver nota)
    r.update(hunt_M_neg=hunt_M_neg, hunt_M_pos=hunt_M_pos, hunt_V=hunt_V)

    return r


def calcular(d: dict) -> Resultado:
    r = _motor(d)
    res = Resultado()

    res.valores = [
        Valor("Ka", "Coeficiente de empuje activo Ka", r["Ka"], "", "tan2(45-phi/2)", 4),
        Valor("Kp", "Coeficiente de empuje pasivo Kp", r["Kp"], "", "tan2(45+phi2/2)", 4),
        Valor("Ea", "Empuje activo Ea", r["Ea"], "kg/m", "sa_max . H_ef / 2", 0),
        Valor("Ep", "Empuje pasivo Ep", r["Ep"], "kg/m", "(sp1+sp_max) . Dp / 2", 0),
        Valor("R", "Resultante vertical R", r["R"], "kg/m", "suma Wi + Eav", 0),
        Valor("M_estab", "Momento estabilizador", r["M_estab"], "kg.m/m", "suma Wi.ci", 0),
        Valor("M_volc", "Momento volcador", r["M_volc"], "kg.m/m", "Eah . brazo", 0),
        Valor("e", "Excentricidad e", r["e"], "m", "B/2 - x", 3),
        Valor("sigma_max", "Presion maxima de contacto", r["sigma_max"] / 10000, "kg/cm2", "R/B . (1+6e/B)", 3),
        Valor("sigma_min", "Presion minima de contacto", r["sigma_min"] / 10000, "kg/cm2", "R/B . (1-6e/B)", 3),
        Valor("Mu_fuste", "Momento ultimo fuste (" + r["clave_fuste_gob"] + ")", r["Mu_fuste"], "kg.m", "1.7 . M gobernante", 0),
        Valor("As_fuste", "Acero fuste (franja gobernante)", r["As_fuste"], "cm2/m", "Mu/(phi.fy.ju.d)", 2),
        Valor("Mu_talon", "Momento ultimo talon", r["Mu_talon"], "kg.m", "1.7 . M1", 0),
        Valor("As_talon", "Acero talon", r["As_talon"], "cm2/m", "Mu/(phi.fy.ju.d)", 2),
        Valor("Mu_punt", "Momento ultimo puntera", r["Mu_punt"], "kg.m", "1.7 . M1", 0),
        Valor("As_punt", "Acero puntera", r["As_punt"], "cm2/m", "Mu/(phi.fy.ju.d)", 2),
        Valor("EaL_ctf", "Resultante sobre 1 contrafuerte EaL", r["EaL_ctf"], "kg", "sB.L.Bpanel/2", 0),
        Valor("Mu_ctf", "Momento ultimo en la base del contrafuerte", r["Mu_ctf"], "kg.m", "1.7 . EaL.Bpanel/3", 0),
        Valor("As_ctf", "Acero principal del contrafuerte (base)", r["As_ctf"], "cm2", "Mu/(phi.fy.ju.d)/cos(theta)", 2),
    ]

    res.chequeos = [
        Chequeo("Vuelco", f"FS = {r['FS_volc_sin']:.2f}", ">=", "1.5", r["volc_ok"]),
        Chequeo("Deslizamiento", f"FS = {r['FS_desliz_sin']:.2f}", ">=", "1.5", r["desliz_ok"]),
        Chequeo("Excentricidad", f"e = {r['e']:.3f} m", "<=", f"B/6 = {d['B_adop']/6:.3f} m", r["exc_ok"]),
        Chequeo("Presion de contacto", f"sigma_max = {r['sigma_max']/10000:.3f} kg/cm2", "<=",
                f"sigma_adm = {d['sigma_adm']:.2f} kg/cm2 (y sigma_min >= 0)", r["contacto_ok"]),
        Chequeo("Flexion en el fuste", f"d = {d['fuste_d_adop']:.1f} cm", ">=",
                f"d_min = {r['d_min_fuste']:.1f} cm", r["fuste_flexion_ok"]),
        Chequeo("Corte en el fuste", f"vu = {r['vu_fuste']:.3f} kg/cm2", "<=",
                f"vc = {r['Vc']:.3f} kg/cm2", r["fuste_corte_ok"]),
        Chequeo("Flexion en el talon", f"d = {d['talon_d_adop']:.1f} cm", ">=",
                f"d_min = {r['d_min_talon']:.1f} cm", r["talon_flexion_ok"]),
        Chequeo("Corte en el talon", f"vu = {r['vu_talon']:.3f} kg/cm2", "<=",
                f"vc = {r['Vc']:.3f} kg/cm2", r["talon_corte_ok"]),
        Chequeo("Flexion en la puntera", f"d = {d['puntera_d_adop']:.1f} cm", ">=",
                f"d_min = {r['d_min_punt']:.1f} cm", r["punt_flexion_ok"]),
        Chequeo("Corte en la puntera", f"vu = {r['vu_punt']:.3f} kg/cm2", "<=",
                f"vc = {r['Vc']:.3f} kg/cm2", r["punt_corte_ok"]),
        Chequeo("Corte en el contrafuerte (base)", f"vu = {r['vu_ctf']:.3f} kg/cm2", "<=",
                f"vc = {r['Vc']:.3f} kg/cm2", r["ctf_corte_ok"],
                "" if r["ctf_corte_ok"] else "No cumple: se requieren estribos (no calculados aqui)."),
    ]

    res.resumen = [
        Valor("B_adop", "Ancho de base B", d["B_adop"], "m", "", 2),
        Valor("Bprima_adop", "Espesor del fuste B'", d["Bprima_adop"], "m", "", 2),
        Valor("D_adop", "Espesor de la losa D", d["D_adop"], "m", "", 2),
        Valor("L_adop", "Separacion de contrafuertes L", d["L_adop"], "m", "", 2),
        Valor("As_ctf", "Acero principal contrafuerte (base)", r["As_ctf"], "cm2", "", 2),
    ]

    res.notas.append(
        f"Contrafuerte: seccion critica evaluada en la base (canto adoptado "
        f"h={d['h_ctf_base']:.2f} m). As minimo de retraccion/temperatura de referencia: "
        f"{r['As_min_ctf']:.2f} cm2/m."
    )
    res.notas.append(
        "Verificacion rapida (Huntington, orientativa, no validada contra el ejemplo del "
        f"libro por inconsistencia dimensional en la formula fuente): "
        f"M- ~ {r['hunt_M_neg']:.0f}, M+ ~ {r['hunt_M_pos']:.0f}, V ~ {r['hunt_V']:.0f} "
        "(unidades no confiables, usar solo como referencia)."
    )

    return res


# --------------------------------------------------------------------------- #
#  Esquema (dibujo): corte (elevacion) + planta
# --------------------------------------------------------------------------- #
def _corte(H, B, Bp, D, puntera, talon, Bpanel):
    # Muros altos y angostos: se usan escalas horizontal y vertical
    # independientes (como en un croquis de mano), no una unica escala,
    # para que la base siga siendo legible.
    W, Hpx = 320, 260
    mL, mR, mT, mB = 42, 18, 20, 40
    scx = (W - mL - mR) / B
    scy = (Hpx - mT - mB) / H
    Bpx, Hpanelpx, Dpx = B * scx, Bpanel * scy, D * scy
    puntpx, talonpx, Bppx = puntera * scx, talon * scx, Bp * scx
    x0 = mL
    ybase = Hpx - mB
    ytop_losa = ybase - Dpx
    ytop_muro = ytop_losa - Hpanelpx
    x_stem = x0 + puntpx
    p = []
    # linea de terreno detras del muro (sobre el talon)
    p.append({"k": "line", "x1": x_stem + Bppx, "y1": ytop_muro, "x2": x0 + Bpx + 8, "y2": ytop_muro,
              "stroke": "#9aa7b5", "sw": 0.8, "dash": True})
    # losa de base completa
    p.append({"k": "rect", "x": x0, "y": ytop_losa, "w": Bpx, "h": Dpx,
              "fill": RELLENO_ZAP, "stroke": AZUL, "sw": 1.4})
    # fuste (stem)
    p.append({"k": "rect", "x": x_stem, "y": ytop_muro, "w": Bppx, "h": Hpanelpx,
              "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.4})
    # cuna del contrafuerte (referencia, lado del talon)
    p.append({"k": "line", "x1": x_stem + Bppx, "y1": ytop_muro, "x2": x0 + Bpx, "y2": ytop_losa,
              "stroke": ACERO, "sw": 1.2, "dash": True})
    # flecha de empuje activo (Ea), a media altura, apuntando hacia el fuste
    ya = ytop_muro + Hpanelpx * 0.4
    p.append({"k": "line", "x1": x0 + Bpx + 6, "y1": ya, "x2": x_stem + Bppx + 4, "y2": ya,
              "stroke": ACERO, "sw": 1.6})
    p.append({"k": "text", "x": x0 + Bpx + 6, "y": ya - 4, "s": "Ea", "size": 8.5,
              "anchor": "start", "fill": ACERO, "bold": True})
    # cotas
    p += cota_h(x0, x0 + puntpx, ybase + 14, f"punt. {puntera:.1f}")
    p += cota_h(x_stem + Bppx, x0 + Bpx, ybase + 14, f"talon {talon:.1f}")
    p += cota_v(x0 - 24, ytop_muro, ybase, f"H = {H:.1f} m")
    p += cota_h(x0, x0 + Bpx, ybase + 28, f"B = {B:.2f} m")
    p.append({"k": "text", "x": x_stem + Bppx / 2, "y": ytop_muro - 6, "s": "B'", "size": 8,
              "anchor": "middle", "fill": GRIS})
    return {"titulo": "Corte", "ancho": W, "alto": Hpx, "primitivas": p}


def _planta(B, Bp, puntera, talon, L, t):
    W, H = 300, 180
    mL, mR, mT, mB = 20, 20, 20, 34
    largo = 2 * L
    sc = min((W - mL - mR) / largo, (H - mT - mB) / B)
    x0, y0 = mL, mT
    Bpx, Bppx, puntpx, talonpx = B * sc, Bp * sc, puntera * sc, talon * sc
    Lpx, tpx = L * sc, max(t * sc, 1.5)
    x_stem = x0 + puntpx
    p = []
    # fuste (linea llena, franja)
    p.append({"k": "rect", "x": x0, "y": y0, "w": puntpx + Bppx + talonpx, "h": Bpx,
              "fill": None, "stroke": GRIS, "sw": 0.8, "dash": True})
    p.append({"k": "rect", "x": x_stem, "y": y0, "w": Bppx, "h": Bpx,
              "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.2})
    # contrafuertes (triangulos hacia el lado del talon), cada L
    for i in range(3):
        yc = y0 + i * Lpx
        if yc > y0 + Bpx:
            break
        p.append({"k": "line", "x1": x_stem + Bppx, "y1": yc, "x2": x0 + puntpx + Bppx + talonpx, "y2": yc,
                  "stroke": ACERO, "sw": tpx})
    p += cota_v(x0 - 14, y0, y0 + Lpx, f"L = {L:.1f} m")
    p += cota_h(x_stem + Bppx, x0 + puntpx + Bppx + talonpx, y0 + Bpx + 14, f"talon = {talon:.1f} m")
    p.append({"k": "text", "x": W / 2, "y": H - 6, "s": f"contrafuertes @ {L:.1f} m, t={t*100:.0f} cm",
              "size": 8, "anchor": "middle", "fill": ACERO})
    return {"titulo": "Planta", "ancho": W, "alto": H, "primitivas": p}


def esquema(entradas: dict, res: Resultado):
    H = entradas["H"]
    B, Bp, D = entradas["B_adop"], entradas["Bprima_adop"], entradas["D_adop"]
    puntera = entradas["puntera_adop"]
    talon = B - Bp - puntera
    Bpanel = H - D
    L, t = entradas["L_adop"], entradas["t_adop"]
    return [_corte(H, B, Bp, D, puntera, talon, Bpanel), _planta(B, Bp, puntera, talon, L, t)]


# --------------------------------------------------------------------------- #
#  Dimensionamiento asistido
# --------------------------------------------------------------------------- #
def sugerir(d: dict) -> dict:
    """Predimensiona B, B', D, puntera, L, t (Sec. 3) e itera hasta que las
    verificaciones de estabilidad y flexion cumplan. El corte en talon/puntera
    se resuelve aumentando el peralte hasta un limite practico; el corte en el
    contrafuerte, por su magnitud, tipicamente requiere estribos (no se agranda
    la seccion de forma indefinida para cubrirlo solo con concreto)."""
    base = dict(d)
    H = base["H"]

    Bp = max(round(H / 11 / 0.05) * 0.05, 0.30)
    D = max(round(H / 11 / 0.05) * 0.05, 0.30)
    Bpanel = H - D
    L = max(round(0.65 * Bpanel / 0.1) * 0.1, 3.0)

    B = round(max(0.5 * H, Bp + 0.6) / 0.1) * 0.1
    puntera = max(round(B / 3 / 0.1) * 0.1, 0.6)
    if puntera >= B - Bp - 0.3:
        puntera = round((B - Bp) / 3 / 0.1) * 0.1

    prev = None
    for _ in range(60):
        talon = B - Bp - puntera
        if talon < 0.3:
            B = round((B + 0.1) / 0.1) * 0.1
            continue
        prueba = dict(base, B_adop=B, Bprima_adop=Bp, D_adop=D, puntera_adop=puntera,
                      L_adop=L, t_adop=base.get("t_adop", 0.4),
                      talon_d_adop=base.get("talon_d_adop", 50),
                      puntera_d_adop=base.get("puntera_d_adop", 45),
                      fuste_d_adop=base.get("fuste_d_adop", 30),
                      h_ctf_base=base.get("h_ctf_base", talon))
        r = _motor(prueba)
        estado = (round(B, 2), round(Bp, 2), round(D, 2), round(puntera, 2))
        ok_estab = r["volc_ok"] and r["desliz_ok"] and r["exc_ok"] and r["contacto_ok"]
        if ok_estab:
            if estado == prev:
                break
            prev = estado
            break
        B = round((B + 0.1) / 0.1) * 0.1
        prev = estado

    talon = B - Bp - puntera
    r = _motor(dict(base, B_adop=B, Bprima_adop=Bp, D_adop=D, puntera_adop=puntera,
                    L_adop=L, t_adop=base.get("t_adop", 0.4),
                    talon_d_adop=base.get("talon_d_adop", 50),
                    puntera_d_adop=base.get("puntera_d_adop", 45),
                    fuste_d_adop=base.get("fuste_d_adop", 30),
                    h_ctf_base=base.get("h_ctf_base", talon)))

    def _redondear_5cm(valor_cm):
        return max(math.ceil(valor_cm / 5.0) * 5.0, 15.0)

    phi_corte = base.get("phi_corte", 0.85)
    d_corte_talon = 1.7 * r["V1_talon"] / (phi_corte * 100 * r["Vc"])
    d_corte_punt = 1.7 * r["V1_punt"] / (phi_corte * 100 * r["Vc"])

    talon_d = _redondear_5cm(max(r["d_min_talon"] * 1.15, d_corte_talon * 1.05))
    puntera_d = _redondear_5cm(max(r["d_min_punt"] * 1.15, d_corte_punt * 1.05))
    fuste_d = _redondear_5cm(r["d_min_fuste"] * 1.15)
    t_ctf = max(round(Bpanel / 20 / 0.05) * 0.05, 0.30)
    h_ctf_base = round(talon / 0.1) * 0.1

    return {
        "B_adop": B, "Bprima_adop": Bp, "D_adop": D, "puntera_adop": puntera,
        "L_adop": L, "t_adop": t_ctf,
        "talon_d_adop": talon_d, "puntera_d_adop": puntera_d, "fuste_d_adop": fuste_d,
        "h_ctf_base": h_ctf_base,
    }


# --------------------------------------------------------------------------- #
#  Declaracion de la calculadora
# --------------------------------------------------------------------------- #
CALCULADORA = Calculadora(
    id="muro_contrafuertes",
    nombre="Muro de contencion con contrafuertes",
    categoria="Muros",
    icono="\U0001F9F1",
    descripcion=(
        "Diseno de muro de contencion con contrafuertes: empuje activo y pasivo, "
        "estabilidad global (vuelco, deslizamiento, excentricidad, presion de "
        "contacto), fuste entre contrafuertes (teoria de placas), talon, puntera y "
        "contrafuerte (seccion critica en la base)."
    ),
    referencia="M. Fratelli - Suelos, Fundaciones y Muros, Cap. 15",
    campos=[
        Campo("H", "Altura total del muro  H", "m", 9.0, grupo="Geometria a contener", minimo=1.0),

        Campo("gs", "Peso unitario del relleno  ys", "kg/m3", 1850, grupo="Suelo relleno", minimo=1000),
        Campo("phi", "Angulo de friccion del relleno  phi", "grados", 30, grupo="Suelo relleno", minimo=0, maximo=45),
        Campo("c", "Cohesion del relleno  c", "kg/cm2", 0.088, grupo="Suelo relleno", minimo=0),
        Campo("beta", "Inclinacion del talud  beta", "grados", 0, grupo="Suelo relleno", minimo=0, maximo=30),
        Campo("q", "Sobrecarga sobre el relleno  q", "kg/m2", 1200, grupo="Suelo relleno", minimo=0),

        Campo("gs2", "Peso unitario del suelo de apoyo  ys2", "kg/m3", 2000, grupo="Suelo apoyo", minimo=1000),
        Campo("phi2", "Angulo de friccion del apoyo  phi2", "grados", 34, grupo="Suelo apoyo", minimo=0, maximo=45),
        Campo("c2", "Cohesion del suelo de apoyo  c2", "kg/cm2", 0.4, grupo="Suelo apoyo", minimo=0),
        Campo("sigma_adm", "Capacidad portante admisible  sigma_adm", "kg/cm2", 2.8, grupo="Suelo apoyo", minimo=0.1),
        Campo("Dp_adop", "Profundidad de empotramiento delante del pie  Dp", "m", 1.2, grupo="Suelo apoyo",
              ayuda="Profundidad de suelo delante del pie que moviliza el empuje pasivo.", minimo=0),

        Campo("fc", "Resistencia del concreto  f'c", "kg/cm2", 200, grupo="Materiales", minimo=100),
        Campo("fy", "Fluencia del acero  fy", "kg/cm2", 4200, grupo="Materiales", minimo=2000),
        Campo("gc", "Peso unitario del concreto  yc", "kg/m3", 2500, grupo="Materiales", minimo=2000),

        Campo("B_adop", "Ancho de base adoptado  B", "m", 3.6, grupo="Geometria adoptada", minimo=1.0, paso=0.1),
        Campo("Bprima_adop", "Espesor del fuste adoptado  B'", "m", 0.4, grupo="Geometria adoptada", minimo=0.2, paso=0.05),
        Campo("D_adop", "Espesor de la losa de base adoptado  D", "m", 0.6, grupo="Geometria adoptada", minimo=0.2, paso=0.05),
        Campo("puntera_adop", "Largo de la puntera adoptado  C", "m", 1.2, grupo="Geometria adoptada", minimo=0.3, paso=0.1,
              ayuda="El talon se calcula como B - B' - puntera."),
        Campo("L_adop", "Separacion entre contrafuertes  L", "m", 5.6, grupo="Geometria adoptada", minimo=2.0, paso=0.1),
        Campo("t_adop", "Espesor del contrafuerte  t", "m", 0.4, grupo="Geometria adoptada", minimo=0.3, paso=0.05),

        Campo("talon_d_adop", "Altura util adoptada del talon", "cm", 50, grupo="Espesores adoptados", minimo=10),
        Campo("puntera_d_adop", "Altura util adoptada de la puntera", "cm", 45, grupo="Espesores adoptados", minimo=10),
        Campo("fuste_d_adop", "Altura util adoptada del fuste", "cm", 30, grupo="Espesores adoptados", minimo=10),
        Campo("h_ctf_base", "Canto del contrafuerte en la base (adoptado)", "m", 2.40, grupo="Espesores adoptados",
              ayuda="Canto (profundidad de flexion) del contrafuerte en su seccion mas cargada, "
                    "segun la geometria de la cuna dibujada en el plano.", minimo=0.3, paso=0.1),

        Campo("mu", "Coeficiente mu (altura minima)", "", 0.1448, grupo="Factores de reduccion", avanzado=True, minimo=0.001),
        Campo("ju", "ju (brazo interno)", "", 0.90, grupo="Factores de reduccion", avanzado=True, minimo=0.5, maximo=1.0),
        Campo("phi_corte", "phi corte", "", 0.85, grupo="Factores de reduccion", avanzado=True, minimo=0.5, maximo=1.0),
        Campo("phi_flexion", "phi flexion", "", 0.90, grupo="Factores de reduccion", avanzado=True, minimo=0.5, maximo=1.0),
        Campo("coef_tanphi_p", "Coeficiente sobre tan(phi2) para friccion base", "", 0.67, grupo="Factores de reduccion",
              avanzado=True, minimo=0.4, maximo=1.0),
        Campo("coef_c_p", "Coeficiente sobre c2 para cohesion base", "", 0.6, grupo="Factores de reduccion",
              avanzado=True, minimo=0.5, maximo=0.75, ayuda="Fratelli sugiere 0.5 a 0.75 de c2."),
    ],
    funcion=calcular,
    tablas_referencia=[TABLA_FUSTE_TRIANGULAR, TABLA_FUSTE_UNIFORME],
    esquema=esquema,
    sugerir=sugerir,
)
