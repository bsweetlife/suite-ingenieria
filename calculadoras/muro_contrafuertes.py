"""
Muro de contencion con contrafuertes.

Diseno de un muro de contencion con contrafuertes (empuje activo/pasivo,
estabilidad global, fuste entre contrafuertes, talon, puntera y contrafuertes).

Referencia:  Maria Fratelli - "Suelos, Fundaciones y Muros", Capitulo 15.
Validado contra el Ejemplo 15.3 del libro (tests/test_muro_contrafuertes.py).

NOTA DE TERMINOLOGIA: "puntera" = lado con tierra retenida + sobrecarga +
contrafuerte (C=2.0 m en el ejemplo, C/L=0.357), "talon" = lado sin tierra,
junto al punto de momentos por vuelco (~1.2 m). Esta es la convencion del
propio Ejemplo 15.3 del libro (verificada con los V1/Mu de la seccion 6 del
libro), aunque es opuesta a la convencion mas comun en otros textos (donde
"talon" suele ser el lado bajo tierra). Se mantiene por consistencia con la
fuente que se esta validando.

NOTA SOBRE EL CONTRAFUERTE: la carga horizontal sobre el contrafuerte usa el
mismo recorte por traccion (z0) que el empuje activo global (Sec. 2): la
presion es triangular pura a partir de z0 (no desde el tope del fuste). Con
ese ajuste, las secciones 1 y 2 (y = Bpanel/3, 2Bpanel/3) reproducen M, As y
vu del ejemplo con menos de 2% de diferencia. La seccion 3 (base del fuste,
y=Bpanel) tambien reproduce el corte del ejemplo exacto, pero el ejemplo NO
diseña el acero principal ahi: el contrafuerte sigue como voladizo hasta el
FONDO DE LA LOSA (H = Bpanel + D). En ese tramo el canto h ya no crece (el
paramento posterior se vuelve vertical), pero el momento si sigue creciendo
porque el corte acumulado V3 actua sobre el brazo adicional D:
    M_fondo = M3 + V3.D
Con esto, M_fondo/As_fondo reproducen la 4ta fila del Ejemplo 15.3 (M~290 tm,
As~68.96 cm2) dentro de ~1%, y es la que gobierna el armado principal.

NOTA SOBRE EL CANTO DEL CONTRAFUERTE (geometria, no dato suelto): "canto" (h,
usado como profundidad de flexion, d=0.9h) y "puntera" NO son la misma
distancia -- miden cosas distintas y por eso canto_base (2.40 m) > puntera
(2.00 m) sin que el contrafuerte quede sin apoyo:

- La cuña VISIBLE del contrafuerte (el volado triangular mas alla de la cara
  posterior del fuste, lo que se dibuja en el esquema) crece de 0 en el tope
  del panel (y=0) a exactamente "puntera" en la base (y=Bpanel). Su punta
  queda siempre al ras del borde de la losa -- nunca la sobrepasa.
- El canto h usado para el calculo de acero es la profundidad de flexion de
  la seccion COMPUESTA contrafuerte+fuste (accion tipo viga T/L): el acero de
  traccion va en el borde inclinado de la cuña (lado puntera) y la zona de
  compresion cae en la cara ANTERIOR (exterior) del fuste, porque contra-
  fuerte y fuste se funden monoliticos y el fuste aporta su espesor B' como
  ala de compresion en toda la altura. Por eso:
      canto(y) = B' + puntera . (y / Bpanel)   ->   canto_base = B' + puntera
  En el ejemplo, canto_base = 0.4 + 2.0 = 2.40 m = el h=2.40 de la fila 3/4
  del libro, pero el volado fisico (lo que se apoya sobre la losa) sigue
  siendo "puntera" = 2.00 m, sin voladizo fuera de ella.
"""
from __future__ import annotations

import math

from motor.base import Calculadora, Campo, Chequeo, Resultado, Valor
from motor.dibujo import cota_h, cota_v, AZUL, GRIS, RELLENO_ZAP, RELLENO_PED, ACERO
from datos.acero import sugerir_armado, diametro_barras, barras_con_diametro, ld_basico, BARRAS


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
#  Corte: vigas (contrafuerte) llevan estribos; losas (talon/puntera) se
#  corrigen con espesor, nunca con estribos.
# --------------------------------------------------------------------------- #
def _corte_viga(vu, vc, fc, d_cm, bw_cm, fy, s_max_cm, diam_pierna_cm, ramas):
    """Tres estados: sin estribos (vu<=vc); con estribos (vc<vu<=vc+2.1.sqrt(fc)),
    s=min(Av.fy/(vs.bw), d/2, s_max), redondeado hacia abajo a multiplos de 5 cm;
    o NO CUMPLE (vu excede el limite superior, ni los estribos alcanzan)."""
    lim = vc + 2.1 * math.sqrt(fc)
    if vu <= vc:
        return {"necesita": False, "s": None, "vs": 0.0, "ok": True, "excede": False}
    if vu <= lim:
        vs = vu - vc
        Av = ramas * (math.pi / 4 * diam_pierna_cm ** 2)
        s_teo = Av * fy / (vs * bw_cm)
        s = min(s_teo, d_cm / 2, s_max_cm)
        s = math.floor(s / 5.0) * 5.0
        return {"necesita": True, "s": max(s, 5.0), "s_teo": s_teo, "vs": vs,
                "ok": True, "excede": False}
    return {"necesita": True, "s": None, "vs": vu - vc, "ok": False, "excede": True, "lim": lim}


def _corte_losa(vu, vc, V_critico, phi_corte, bw_cm, d_cm):
    """Losas (talon, puntera): sin estribos. Si vu > vc, se corrige con mas
    espesor (nunca con estribos); se reporta el d necesario."""
    if vu <= vc:
        return {"ok": True, "d_necesario": None}
    d_necesario = 1.7 * V_critico / (phi_corte * bw_cm * vc)
    return {"ok": False, "d_necesario": d_necesario}


def _V_seccion_critica(w_func, largo, d_m, N=400):
    """Corte en la seccion critica de un voladizo, a distancia d de la cara
    (el empotramiento), integrando la carga distribuida desde ahi hasta la
    punta (no desde la cara, que sobreestima vu)."""
    offset = min(d_m, largo)
    tramo = largo - offset
    if tramo <= 0:
        return 0.0
    h = tramo / N
    V = 0.0
    for i in range(N):
        xi = offset + (i + 0.5) * h
        V += w_func(xi) * h
    return V


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
    s_max_estribo = d["s_max_estribo"]
    diam_estribo = d["diam_estribo"]
    ramas_estribo = d["ramas_estribo"]

    Bpanel = H - D
    # "puntera" = lado con tierra + sobrecarga + contrafuerte (C, ~2.0 m en el
    # ejemplo). "talon" = lado sin tierra, junto al punto de momentos (~1.2 m).
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

    # ---------------- 3. Pesos y brazos (respecto al punto I, junto al talon) ----------------
    x_talon = talon / 2
    x_stem = talon + Bp / 2
    x_slab = B / 2
    x_puntera = talon + Bp + puntera / 2
    x_ctf = talon + Bp + puntera / 3     # centroide de la cuna triangular del contrafuerte

    W1 = Bp * Bpanel * gc                      # fuste
    W2 = B * D * gc                            # losa de base completa
    W3 = puntera * Bpanel * gs                 # suelo sobre la puntera (lado con tierra)
    Wq = q * puntera                           # sobrecarga sobre la puntera
    Vol_ctf = 0.5 * puntera * Bpanel * t
    W4 = Vol_ctf * gc / L                       # contrafuerte, repartido por metro

    R = W1 + W2 + W3 + Wq + W4 + Eav
    M_estab = (W1 * x_stem + W2 * x_slab + W3 * x_puntera + Wq * x_puntera
               + W4 * x_ctf + Eav * B)
    M_volc = Eah * brazo_Ea

    r.update(W1=W1, W2=W2, W3=W3, Wq=Wq, W4=W4, R=R, M_estab=M_estab, M_volc=M_volc,
              x_stem=x_stem, x_slab=x_slab, x_puntera=x_puntera, x_ctf=x_ctf)

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
    # El punto 0 (empotramiento junto al contrafuerte, momento negativo My0) es
    # el que gobierna el armado en el ejemplo del libro, aun cuando Mx4 es
    # mayor en magnitud -- el acero de My0 ancla directamente en el
    # contrafuerte y controla el detalle constructivo.
    clave_gob, M_fuste_gob = "My0", My0
    Mu_fuste = 1.7 * abs(M_fuste_gob)
    d_min_fuste = math.sqrt(Mu_fuste * 100 / (mu * fc * 100))
    As_fuste = Mu_fuste * 100 / (phi_flexion * fy * ju * fuste_d_adop)
    Vc = 0.53 * math.sqrt(fc)
    V_fuste = coef["gamma5"] * q0 * L        # reaccion (aprox.) sobre contrafuerte, referencia
    vu_fuste = 1.7 * V_fuste / (phi_corte * 100 * fuste_d_adop)
    r.update(clave_fuste_gob=clave_gob, M_fuste_gob=M_fuste_gob, Mx4_mayor_magnitud=Mx4,
              Mu_fuste=Mu_fuste, d_min_fuste=d_min_fuste, As_fuste=As_fuste, Vc=Vc,
              V_fuste=V_fuste, vu_fuste=vu_fuste, fuste_flexion_ok=fuste_d_adop >= d_min_fuste,
              fuste_corte_ok=vu_fuste <= Vc)

    # ---------------- 6. Talon y puntera (losas: sin estribos) ----------------
    def sigma_base(x):
        # x medido desde el punto I (x=0, donde ocurre sigma_max) hasta la puntera (x=B)
        return sigma_max - (sigma_max - sigma_min) * (x / B)

    # Talon (lado sin tierra, junto al punto I): voladizo empotrado en el
    # fuste, carga neta hacia arriba (reaccion del suelo - peso propio). El
    # momento se toma en la cara; el corte, en la seccion critica a d de la
    # cara (tomarlo en la cara sobreestima vu).
    N = 400
    w_talon = lambda xi: sigma_base(talon - xi) - D * gc
    h_t = talon / N
    V1_talon = 0.0
    M1_talon = 0.0
    for i in range(N):
        xi = (i + 0.5) * h_t
        V1_talon += w_talon(xi) * h_t
        M1_talon += w_talon(xi) * xi * h_t
    # abs(): en geometrias extremas (H muy chico) el neto puede invertirse;
    # d_min/As dependen de la magnitud, no del signo (igual que en el fuste).
    Mu_talon = 1.7 * M1_talon
    d_min_talon = math.sqrt(abs(Mu_talon) * 100 / (mu * fc * 100))
    As_talon = abs(Mu_talon) * 100 / (phi_flexion * fy * ju * talon_d_adop)
    Vcrit_talon = _V_seccion_critica(w_talon, talon, talon_d_adop / 100.0)
    vu_talon = 1.7 * Vcrit_talon / (phi_corte * 100 * talon_d_adop)
    corte_talon = _corte_losa(vu_talon, Vc, Vcrit_talon, phi_corte, 100.0, talon_d_adop)

    # Puntera (lado con tierra, C/L determina el criterio de analisis):
    # voladizo empotrado en el fuste, carga neta hacia abajo (peso propio +
    # tierra + sobrecarga) - reaccion del suelo. Mismo criterio: momento en
    # la cara, corte en la seccion critica a d de la cara.
    CL = puntera / L
    x0_p = talon + Bp
    w_punt = lambda xi: (D * gc + Bpanel * gs + q) - sigma_base(x0_p + xi)
    h_p = puntera / N
    V1_punt = 0.0
    M1_punt = 0.0
    for i in range(N):
        xi = (i + 0.5) * h_p
        V1_punt += w_punt(xi) * h_p
        M1_punt += w_punt(xi) * xi * h_p
    Mu_punt = 1.7 * M1_punt
    d_min_punt = math.sqrt(abs(Mu_punt) * 100 / (mu * fc * 100))
    As_punt = abs(Mu_punt) * 100 / (phi_flexion * fy * ju * puntera_d_adop)
    Vcrit_punt = _V_seccion_critica(w_punt, puntera, puntera_d_adop / 100.0)
    vu_punt = 1.7 * Vcrit_punt / (phi_corte * 100 * puntera_d_adop)
    corte_punt = _corte_losa(vu_punt, Vc, Vcrit_punt, phi_corte, 100.0, puntera_d_adop)

    r.update(V1_talon=V1_talon, M1_talon=M1_talon, Mu_talon=Mu_talon,
              d_min_talon=d_min_talon, As_talon=As_talon, vu_talon=vu_talon,
              talon_flexion_ok=talon_d_adop >= d_min_talon,
              talon_corte_ok=corte_talon["ok"], corte_talon=corte_talon,
              CL=CL, V1_punt=V1_punt, M1_punt=M1_punt, Mu_punt=Mu_punt,
              d_min_punt=d_min_punt, As_punt=As_punt, vu_punt=vu_punt,
              punt_flexion_ok=puntera_d_adop >= d_min_punt,
              punt_corte_ok=corte_punt["ok"], corte_punt=corte_punt)

    # ---------------- 7. Contrafuerte: 3 secciones (y = Bpanel/3, 2Bpanel/3, Bpanel) ----------------
    # La presion horizontal sobre el contrafuerte es triangular a partir de z0
    # (mismo recorte por traccion que el empuje activo global, Sec. 2), no
    # desde el tope del fuste. Con y medido desde el tope del fuste:
    #   V(y) = L . k1 . (y-z0)^2 / 2 ,   M(y) = L . k1 . (y-z0)^3 / 6 ,  k1 = gs.Ka
    k1 = gs * Ka
    # Canto de diseno (h, profundidad de flexion) por geometria pura, no como
    # dato suelto. OJO: "canto" y "puntera" NO son la misma distancia:
    #   - la cuña VISIBLE (lo que se dibuja, el volado del contrafuerte mas
    #     alla de la cara posterior del fuste) crece de 0 en el tope del
    #     panel a "puntera" en la base -- su punta queda al ras del borde de
    #     la losa, nunca la sobrepasa (ver _corte(), que dibuja exactamente
    #     ese ancho, independiente de este canto de diseno).
    #   - el canto h de aqui es la profundidad de flexion de la seccion
    #     COMPUESTA contrafuerte+fuste (accion tipo viga T/L): el fuste aporta
    #     su espesor Bp como ala de compresion (esta monolitico con la cuña en
    #     toda la altura), por eso h = Bp + puntera.(y/Bpanel), mayor que el
    #     volado fisico.
    # En el Ejemplo 15.3: canto_base = 0.4 + 2.0 = 2.40 m = h de la fila 3/4
    # del libro; el volado fisico (apoyado sobre la losa) es puntera = 2.0 m.
    canto_base = Bp + puntera
    r["canto_base_ctf"] = canto_base
    h_ctf = [Bp + puntera * frac for frac in (1 / 3, 2 / 3, 1.0)]
    bw_ctf = [t * 100, t * 100, d["t_ctf_base"] * 100]     # cm; la base se ensancha (nota original Sec. 3)
    fracciones_y = [1 / 3, 2 / 3, 1.0]
    secciones_ctf = []
    for i, (frac, h_m, bw) in enumerate(zip(fracciones_y, h_ctf, bw_ctf), start=1):
        y = Bpanel * frac
        H_ = max(y - z0, 0.0)
        V = L * k1 * H_ ** 2 / 2
        M = L * k1 * H_ ** 3 / 6
        Mu = 1.7 * M
        h_cm = h_m * 100
        theta = math.atan(h_cm / (Bpanel * 100))
        d_cm = 0.9 * h_cm
        As = (Mu * 100) / (phi_flexion * fy * ju * d_cm) / math.cos(theta)
        # As minimo de flexion (14/fy.b.d), con el b y d PROPIOS de esta seccion
        # (el contrafuerte se ensancha en la base: usar el b de la base ahi
        # subestimaria el As_min en las secciones superiores, mas angostas).
        As_min = (14 / fy) * bw * d_cm
        vu = 1.7 * V / (phi_corte * bw * d_cm)
        est = _corte_viga(vu, Vc, fc, d_cm, bw, fy, s_max_estribo, diam_estribo, ramas_estribo)
        secciones_ctf.append({
            "nivel": i, "y": y, "h": h_m, "bw": bw, "V": V, "M": M, "Mu": Mu,
            "theta": theta, "d": d_cm, "As": As, "As_min": As_min, "As_gob": max(As, As_min),
            "vu": vu, "estribos": est, "corte_ok": est["ok"],
        })
    r["secciones_ctf"] = secciones_ctf

    # Seccion 3 (base del fuste, y=Bpanel) no es el apoyo real del contrafuerte:
    # este continua como voladizo hasta el FONDO DE LA LOSA (H = Bpanel + D). De
    # ahi hacia abajo el paramento posterior ya es vertical (h no crece mas),
    # pero el corte acumulado V3 sigue generando momento en el tramo D:
    #   M4 = M3 + V3.D   (mismo V, mismo h -> mismo d y theta que la seccion 3)
    # Con esto, M4/As4 reproducen la 4ta fila del Ejemplo 15.3 (M~290 tm,
    # As~68.96 cm2) dentro de ~1%.
    base_ctf = secciones_ctf[-1]
    M4 = base_ctf["M"] + base_ctf["V"] * D
    Mu4 = 1.7 * M4
    As4 = (Mu4 * 100) / (phi_flexion * fy * ju * base_ctf["d"]) / math.cos(base_ctf["theta"])
    # Mismo b y d que la seccion 3 (el canto ya no crece en el tramo D, ver nota
    # arriba): usar base_ctf["bw"], el espesor REAL de la base (t_ctf_base, la
    # base se ensancha respecto al resto del contrafuerte, ver Sec. 3), no "t".
    As_min4 = (14 / fy) * base_ctf["bw"] * base_ctf["d"]
    r["fondo_losa_ctf"] = {"M": M4, "Mu": Mu4, "As": As4, "As_min": As_min4, "As_gob": max(As4, As_min4),
                            "d": base_ctf["d"], "theta": base_ctf["theta"], "V": base_ctf["V"]}

    # El fondo de la losa gobierna el armado principal (mayor momento, mismo d).
    As_ctf = As4
    As_min_ctf = As_min4
    ctf_corte_ok = all(s["corte_ok"] for s in secciones_ctf)

    r.update(As_ctf=As_ctf, As_min_ctf=As_min_ctf, d_ctf=base_ctf["d"], theta_ctf=base_ctf["theta"],
              Mu_ctf=Mu4, V_ctf=base_ctf["V"], ctf_corte_ok=ctf_corte_ok)

    return r


def calcular(d: dict) -> Resultado:
    r = _motor(d)
    res = Resultado()

    res.valores = [
        Valor("Ka", "Ka (empuje activo)", r["Ka"], "", "tan2(45-phi/2)", 4),
        Valor("Kp", "Kp (empuje pasivo)", r["Kp"], "", "tan2(45+phi2/2)", 4),
        Valor("Ea", "Empuje activo Ea", r["Ea"], "kg/m", "sa_max . H_ef / 2", 0),
        Valor("Ep", "Empuje pasivo Ep", r["Ep"], "kg/m", "(sp1+sp_max) . Dp / 2", 0),
        Valor("R", "Resultante vertical R", r["R"], "kg/m", "suma Wi + Eav", 0),
        Valor("M_estab", "Momento estabilizador", r["M_estab"], "kg.m/m", "suma Wi.ci", 0),
        Valor("M_volc", "Momento volcador", r["M_volc"], "kg.m/m", "Eah . brazo", 0),
        Valor("e", "Excentricidad e", r["e"], "m", "B/2 - x", 3),
        Valor("sigma_max", "Presion max. contacto", r["sigma_max"] / 10000, "kg/cm2", "R/B . (1+6e/B)", 3),
        Valor("sigma_min", "Presion min. contacto", r["sigma_min"] / 10000, "kg/cm2", "R/B . (1-6e/B)", 3),
        Valor("Mu_fuste", "Mu fuste", r["Mu_fuste"], "kg.m", "1.7 . My0", 0),
        Valor("As_fuste", "As fuste", r["As_fuste"], "cm2/m", "Mu/(phi.fy.ju.d)", 2),
        Valor("Mu_talon", "Mu talon", r["Mu_talon"], "kg.m", "1.7 . M1", 0),
        Valor("As_talon", "As talon", r["As_talon"], "cm2/m", "Mu/(phi.fy.ju.d)", 2),
        Valor("Mu_punt", "Mu puntera", r["Mu_punt"], "kg.m", "1.7 . M1", 0),
        Valor("As_punt", "As puntera", r["As_punt"], "cm2/m", "Mu/(phi.fy.ju.d)", 2),
        Valor("Mu_ctf", "Mu contrafuerte (base)", r["Mu_ctf"], "kg.m", "1.7 . (M3 + V3.D)", 0),
        Valor("As_ctf", "As contrafuerte (base)", r["As_ctf"], "cm2", "Mu/(phi.fy.ju.d)/cos(theta)", 2),
        Valor("canto_base_ctf", "Canto de diseno en la base (viga T con fuste)", r["canto_base_ctf"], "m",
              "B' + puntera (seccion compuesta contrafuerte+fuste)", 2),
        Valor("voladizo_ctf", "Volado fisico en la base (apoyado en la losa)", d["puntera_adop"], "m",
              "= puntera, sin sobresalir de la losa", 2),
    ]

    diam_pulg = d["diam_estribo"] / 2.54
    ramas = int(d["ramas_estribo"])

    def _chequeo_corte(nombre, vu, vc, est):
        """Contrafuerte (viga): puede llevar estribos."""
        if not est["necesita"]:
            return Chequeo(nombre, f"vu = {vu:.3f}", "<=", f"vc = {vc:.3f} kg/cm2", True)
        if est["ok"]:
            return Chequeo(nombre, f"vu = {vu:.2f} > vc = {vc:.2f}", "->", f"estr. @{est['s']:.0f}cm",
                            True, f"Requiere estribos ({ramas} ramas Ø{diam_pulg:.3g}\"): "
                            f"separacion adoptada {est['s']:.0f} cm.")
        return Chequeo(nombre, f"vu = {vu:.2f} > lim = {est['lim']:.2f}", "->", "aumentar seccion",
                        False, "vu excede vc+2.1.sqrt(f'c): ni con estribos alcanza, hay que agrandar la seccion.")

    def _chequeo_corte_losa(nombre, vu, vc, corte):
        """Talon/puntera (losas): sin estribos, se corrige con espesor."""
        if corte["ok"]:
            return Chequeo(nombre, f"vu = {vu:.3f} kg/cm2", "<=", f"vc = {vc:.3f} kg/cm2", True)
        return Chequeo(nombre, f"vu = {vu:.2f} kg/cm2", ">", f"vc = {vc:.2f} kg/cm2", False,
                        f"Aumentar el peralte a ~{corte['d_necesario']:.0f} cm (las losas no llevan estribos).")

    res.chequeos = [
        Chequeo("Vuelco", f"FS = {r['FS_volc_sin']:.2f}", ">=", "1.5", r["volc_ok"]),
        Chequeo("Deslizamiento", f"FS = {r['FS_desliz_sin']:.2f}", ">=", "1.5", r["desliz_ok"]),
        Chequeo("Excentricidad", f"e = {r['e']:.3f} m", "<=", f"B/6 = {d['B_adop']/6:.3f} m", r["exc_ok"]),
        Chequeo("Presion de contacto", f"s_max = {r['sigma_max']/10000:.2f}", "<=",
                f"s_adm = {d['sigma_adm']:.2f} kg/cm2", r["contacto_ok"],
                f"sigma_min = {r['sigma_min']/10000:.3f} kg/cm2 (debe ser >= 0)."),
        Chequeo("Flexion en el fuste", f"d = {d['fuste_d_adop']:.1f} cm", ">=",
                f"d_min = {r['d_min_fuste']:.1f} cm", r["fuste_flexion_ok"]),
        Chequeo("Corte en el fuste", f"vu = {r['vu_fuste']:.3f} kg/cm2", "<=",
                f"vc = {r['Vc']:.3f} kg/cm2", r["fuste_corte_ok"]),
        Chequeo("Flexion en el talon", f"d = {d['talon_d_adop']:.1f} cm", ">=",
                f"d_min = {r['d_min_talon']:.1f} cm", r["talon_flexion_ok"]),
        _chequeo_corte_losa("Corte en el talon", r["vu_talon"], r["Vc"], r["corte_talon"]),
        Chequeo("Flexion en la puntera", f"d = {d['puntera_d_adop']:.1f} cm", ">=",
                f"d_min = {r['d_min_punt']:.1f} cm", r["punt_flexion_ok"]),
        _chequeo_corte_losa("Corte en la puntera", r["vu_punt"], r["Vc"], r["corte_punt"]),
    ]
    for s in r["secciones_ctf"]:
        etiqueta = "Corte en el contrafuerte" + (" (base)" if s["nivel"] == len(r["secciones_ctf"]) else f" (nivel {s['nivel']})")
        res.chequeos.append(_chequeo_corte(etiqueta, s["vu"], r["Vc"], s["estribos"]))

    res.resumen = [
        Valor("B_adop", "B", d["B_adop"], "m", "", 2),
        Valor("Bprima_adop", "Fuste", d["Bprima_adop"], "m", "", 2),
        Valor("D_adop", "Losa", d["D_adop"], "m", "", 2),
        Valor("L_adop", "Separacion contraf.", d["L_adop"], "m", "", 2),
    ]

    # ---- Armado consolidado (destacado, separado de las dimensiones) ----
    armados = []
    a_fuste = sugerir_armado(r["As_fuste"])
    if a_fuste:
        armados.append(f"Fuste (franja {r['clave_fuste_gob']}): {a_fuste.texto} (a/s) "
                        f"- provee {a_fuste.As_provisto:.2f} cm2/m >= {r['As_fuste']:.2f} requerido")
    a_talon = sugerir_armado(r["As_talon"])
    if a_talon:
        armados.append(f"Talon: {a_talon.texto} (a/s) - provee {a_talon.As_provisto:.2f} cm2/m "
                        f">= {r['As_talon']:.2f} requerido")
    a_punt = sugerir_armado(r["As_punt"])
    if a_punt:
        armados.append(f"Puntera: {a_punt.texto} (a/s) - provee {a_punt.As_provisto:.2f} cm2/m "
                        f">= {r['As_punt']:.2f} requerido")
    # Un solo diametro para todo el contrafuerte, fijado por la seccion mas
    # exigida (el fondo de losa, donde el momento acumulado gobierna); la
    # cantidad de barras de ese mismo diametro se recalcula nivel a nivel,
    # igual que se detallan los cortes de barra en obra (menos barras hacia
    # el tope, donde el momento es menor).
    fondo = r["fondo_losa_ctf"]
    diam_ctf = diametro_barras(fondo["As_gob"])
    armados.append(f"Contrafuerte, acero principal (borde inclinado, anclado en el paramento "
                    f"exterior del fuste). Diametro adoptado Ø{diam_ctf} en toda la altura; "
                    "cantidad de barras por nivel (menos barras hacia el tope):")
    for s in r["secciones_ctf"]:
        barras = barras_con_diametro(s["As_gob"], diam_ctf)
        rige = " -- rige As minimo, no el momento" if s["As_min"] > s["As"] else ""
        armados.append(f"&nbsp;&nbsp;Nivel {s['nivel']} (a {s['y']:.2f} m del tope del panel): "
                        f"{barras.texto} - provee {barras.As_provisto:.2f} cm2 >= "
                        f"{s['As_gob']:.2f} cm2 requerido{rige}")
    barras_fondo = barras_con_diametro(fondo["As_gob"], diam_ctf)
    rige_fondo = " -- rige As minimo, no el momento" if fondo["As_min"] > fondo["As"] else ""
    armados.append(f"&nbsp;&nbsp;Fondo de losa (base del contrafuerte, gobierna todo el armado): "
                    f"{barras_fondo.texto} - provee {barras_fondo.As_provisto:.2f} cm2 >= "
                    f"{fondo['As_gob']:.2f} cm2 requerido{rige_fondo}")

    # ---- Continuidad y corte del acero principal (no son grupos independientes) ----
    db_ctf_cm = dict(BARRAS)[diam_ctf]
    ld_ctf = ld_basico(d["fy"], d["fc"], db_ctf_cm)
    conteos = [("fondo de losa", barras_fondo.n_barras)] + [
        (f"nivel {s['nivel']}", barras_con_diametro(s["As_gob"], diam_ctf).n_barras)
        for s in reversed(r["secciones_ctf"])
    ]
    armados.append(
        "Continuidad: las barras de arriba NO son grupos independientes por nivel -- todas "
        "corren continuas desde el fondo de la losa (su anclaje) y se van cortando hacia "
        f"arriba a medida que el momento decrece, cada corte extendido al menos "
        f"{ld_ctf:.0f} cm mas alla del punto teorico (long. de anclaje, ver nota):"
    )
    for (etq_prev, n_prev), (etq_next, n_next) in zip(conteos, conteos[1:]):
        cortadas = n_prev - n_next
        if cortadas > 0:
            armados.append(f"&nbsp;&nbsp;De {etq_prev} ({n_prev} barras) hacia {etq_next}: "
                            f"se cortan {cortadas} (quedan {n_next}), corte real a >= "
                            f"{ld_ctf:.0f} cm mas alla de {etq_next}.")
    armados.append(f"&nbsp;&nbsp;Las {conteos[-1][1]} barras restantes de {conteos[-1][0]} "
                    "continuan hasta la punta del panel (armadura minima, sin corte).")

    armados.append("Contrafuerte, estribos (corte):")
    for s in r["secciones_ctf"]:
        if s["estribos"]["necesita"]:
            txt = f"@ {s['estribos']['s']:.0f} cm" if s["estribos"]["ok"] else "insuficientes"
            armados.append(f"&nbsp;&nbsp;Nivel {s['nivel']} ({ramas} ramas Ø{diam_pulg:.3g}\"): {txt}")
        else:
            armados.append(f"&nbsp;&nbsp;Nivel {s['nivel']}: no requiere (vu &lt;= vc)")
    # separador <br/> (no "\n"): se muestra crudo en un <span> de app.py y en
    # un Paragraph de reportlab en el PDF, ambos interpretan <br/> pero no \n.
    res.armado_texto = "<br/>".join(armados)

    res.notas.append(
        "Terminologia: 'puntera' = lado con tierra + sobrecarga + contrafuerte (C/L="
        f"{r['CL']:.3f}); 'talon' = lado sin tierra, junto al punto de momentos por vuelco."
    )
    res.notas.append(
        "Contrafuerte: la cantidad de barras por nivel usa siempre el mayor entre el As por "
        "momento y el As minimo de flexion (14/fy.b.d) de esa seccion. El Ejemplo 15.3 del "
        "libro solo señala el As minimo donde es obvio que gobierna (nivel 1); el motor lo "
        "verifica en los 4 niveles, por lo que el conteo de barras puede quedar 1 barra por "
        "encima de la tabla impresa del libro en algun nivel intermedio -- es una verificacion "
        "adicional, no un error de calculo."
    )
    res.notas.append(
        f"Longitud de anclaje del acero principal del contrafuerte: ld = {ld_ctf:.0f} cm "
        f"(Ø{diam_ctf}), formula SIMPLIFICADA de ACI 318 Sec. 12.2.2 en kg/cm2 y cm (no es una "
        "formula validada contra el Ejemplo 15.3 -- el libro no cubre anclaje en este capitulo). "
        "Supone espaciamiento/recubrimiento adecuados y barra inferior sin recubrimiento "
        "epoxico; verificar contra el codigo vigente (COVENIN 1753 u otro) antes de detallar "
        "los planos finales."
    )
    if r["CL"] >= 0.5:
        res.notas.append(
            f"ADVERTENCIA: C/L = {r['CL']:.3f} >= 0.5 -- segun la Sec. 6, la puntera deberia "
            "analizarse como placa (igual que el fuste), no como voladizo simple. Este modulo "
            "solo implementa el voladizo; el As/d_min de la puntera puede no ser conservador "
            "en esta geometria. Reducir C/L (menos puntera o mas separacion L) o verificar "
            "a mano con la teoria de placas."
        )
    res.notas.append(
        f"Fuste: gobierna My0 = {r['M_fuste_gob']:.0f} kg.m (empotramiento junto al "
        f"contrafuerte), aunque Mx4 = {r['Mx4_mayor_magnitud']:.0f} kg.m es mayor en magnitud; "
        "se sigue el criterio del ejemplo del libro (continuidad del acero hacia el contrafuerte)."
    )
    res.notas.append(
        "Contrafuerte: el voladizo continua hasta el fondo de la losa (H = Bpanel + D), no solo "
        "hasta la base del fuste. El canto h ya no crece en ese tramo, pero el momento si sigue "
        f"creciendo (M_fondo = M_base_fuste + V_base_fuste . D = {r['fondo_losa_ctf']['M']:.0f} kg.m); "
        "por eso el armado principal se calcula en el fondo de la losa, no en la base del fuste."
    )
    res.notas.append(
        f"Canto del contrafuerte: 'canto' (h={r['canto_base_ctf']:.2f} m en la base, usado para el "
        f"acero) y 'puntera' ({d['puntera_adop']:.2f} m, el volado fisico apoyado en la losa) miden "
        "cosas distintas -- no hay voladizo fuera de la losa. La cuña visible crece de 0 en el "
        "tope del panel a exactamente 'puntera' en la base (se dibuja asi en el esquema). El canto "
        "h usado en el calculo de acero es mayor porque es la profundidad de flexion de la seccion "
        "COMPUESTA contrafuerte+fuste (accion tipo viga T): h = B' + puntera, ya que el fuste esta "
        "monolitico con la cuña y aporta su espesor como ala de compresion en toda la altura."
    )
    res.notas.append(
        "Talon y puntera son losas: el corte se verifica en la seccion critica a d de la cara "
        "y se corrige con espesor, nunca con estribos. Con d=45 cm la puntera no cumple "
        "(vu=8.41>vc=7.50 integrando la presion de contacto real); por eso el default de "
        "puntera_d_adop es 50 cm, no 40 cm como en el calculo simplificado de referencia."
    )

    return res


# --------------------------------------------------------------------------- #
#  Esquema (dibujo): corte (elevacion) + planta
# --------------------------------------------------------------------------- #
def _corte(H, B, Bp, D, talon, puntera, Bpanel):
    # Muros altos y angostos: se usan escalas horizontal y vertical
    # independientes (como en un croquis de mano), no una unica escala,
    # para que la base siga siendo legible.
    W, Hpx = 320, 260
    mL, mR, mT, mB = 42, 18, 20, 40
    scx = (W - mL - mR) / B
    scy = (Hpx - mT - mB) / H
    Bpx, Hpanelpx, Dpx = B * scx, Bpanel * scy, D * scy
    talonpx, Bppx = talon * scx, Bp * scx
    x0 = mL
    ybase = Hpx - mB
    ytop_losa = ybase - Dpx
    ytop_muro = ytop_losa - Hpanelpx
    x_stem = x0 + talonpx
    p = []
    # linea de terreno sobre la puntera (lado con tierra retenida)
    p.append({"k": "line", "x1": x_stem + Bppx, "y1": ytop_muro, "x2": x0 + Bpx + 8, "y2": ytop_muro,
              "stroke": "#9aa7b5", "sw": 0.8, "dash": True})
    # losa de base completa
    p.append({"k": "rect", "x": x0, "y": ytop_losa, "w": Bpx, "h": Dpx,
              "fill": RELLENO_ZAP, "stroke": AZUL, "sw": 1.4})
    # fuste (stem)
    p.append({"k": "rect", "x": x_stem, "y": ytop_muro, "w": Bppx, "h": Hpanelpx,
              "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.4})
    # cuna del contrafuerte, punteada, detras del fuste (lado de la puntera/tierra)
    p.append({"k": "line", "x1": x_stem + Bppx, "y1": ytop_muro, "x2": x0 + Bpx, "y2": ytop_losa,
              "stroke": ACERO, "sw": 1.4, "dash": True})
    p.append({"k": "text", "x": x_stem + Bppx + (Bpx - Bppx - talonpx) * 0.35, "y": ytop_muro + Hpanelpx * 0.55,
              "s": "contrafuerte", "size": 7, "anchor": "middle", "fill": ACERO, "rot": -60})
    # flecha de empuje activo (Ea), a media altura, apuntando hacia el fuste
    ya = ytop_muro + Hpanelpx * 0.4
    p.append({"k": "line", "x1": x0 + Bpx + 6, "y1": ya, "x2": x_stem + Bppx + 4, "y2": ya,
              "stroke": ACERO, "sw": 1.6})
    p.append({"k": "text", "x": x0 + Bpx + 6, "y": ya - 4, "s": "Ea", "size": 8.5,
              "anchor": "start", "fill": ACERO, "bold": True})
    # cotas
    p += cota_h(x0, x0 + talonpx, ybase + 14, f"talon {talon:.1f}")
    p += cota_h(x_stem + Bppx, x0 + Bpx, ybase + 14, f"punt. {puntera:.1f}")
    p += cota_v(x0 - 24, ytop_muro, ybase, f"H = {H:.1f} m")
    p += cota_h(x0, x0 + Bpx, ybase + 28, f"B = {B:.2f} m")
    p.append({"k": "text", "x": x_stem + Bppx / 2, "y": ytop_muro - 6, "s": "B'", "size": 8,
              "anchor": "middle", "fill": GRIS})
    return {"titulo": "Corte", "ancho": W, "alto": Hpx, "primitivas": p}


def _planta(B, Bp, talon, puntera, L, t):
    # Eje horizontal = longitud del muro (contrafuertes repetidos cada L);
    # eje vertical = seccion transversal (talon / fuste / puntera). Asi el
    # dibujo queda apaisado, mas legible que repetir la seccion en vertical.
    #
    # Los contrafuertes son macizos: rectangulos de ancho t, del lado de la
    # puntera (donde queda el relleno retenido), perpendiculares al fuste.
    # Sin diagonales -- el perfil triangular es solo del corte (Fig. 15.11).
    W, H = 320, 195
    mL, mR, mT, mB = 20, 34, 16, 38
    n_contrafuertes = 3
    largo = n_contrafuertes * L
    sc = min((W - mL - mR) / largo, (H - mT - mB) / (talon + Bp + puntera))
    x0, y0 = mL, mT
    talonpx, Bppx, punterapx = talon * sc, Bp * sc, puntera * sc
    Lpx = L * sc
    tpx = max(t * sc, 3.0)
    y_stem = y0 + talonpx
    y_punt_top = y_stem + Bppx
    y_bottom = y_punt_top + punterapx
    p = []
    # contorno del cimiento (talon + puntera), de referencia
    p.append({"k": "rect", "x": x0, "y": y0, "w": n_contrafuertes * Lpx, "h": talonpx,
              "fill": None, "stroke": GRIS, "sw": 0.8, "dash": True})
    p.append({"k": "rect", "x": x0, "y": y_punt_top, "w": n_contrafuertes * Lpx, "h": punterapx,
              "fill": None, "stroke": GRIS, "sw": 0.8, "dash": True})
    # contrafuertes: rectangulos macizos de ancho t, del lado de la puntera, cada L
    for i in range(n_contrafuertes + 1):
        xc = x0 + i * Lpx
        p.append({"k": "rect", "x": xc - tpx / 2, "y": y_punt_top, "w": tpx, "h": punterapx,
                  "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.0})
    # fuste: franja larga y delgada, contigua a los contrafuertes
    p.append({"k": "rect", "x": x0, "y": y_stem, "w": n_contrafuertes * Lpx, "h": Bppx,
              "fill": RELLENO_PED, "stroke": AZUL, "sw": 1.2})
    # cotas: L entre ejes de contrafuertes, puntera
    p += cota_h(x0, x0 + Lpx, y0 - 6, f"L = {L:.1f} m", arriba=True)
    p += cota_v(x0 + n_contrafuertes * Lpx + 10, y_punt_top, y_bottom, f"punt. {puntera:.1f} m")
    # cota de t: lineas de extension en abanico (el contrafuerte es muy angosto
    # para que el texto entre entre las marcas de una cota comun)
    x_a, x_b = x0 - tpx / 2, x0 + tpx / 2
    yA, yB = y_bottom + 6, y_bottom + 16
    p.append({"k": "line", "x1": x_a, "y1": y_bottom, "x2": x_a - 6, "y2": yB,
              "stroke": GRIS, "sw": 0.7})
    p.append({"k": "line", "x1": x_b, "y1": y_bottom, "x2": x_b + 6, "y2": yB,
              "stroke": GRIS, "sw": 0.7})
    p.append({"k": "line", "x1": x_a - 6, "y1": yB, "x2": x_b + 6, "y2": yB,
              "stroke": GRIS, "sw": 0.8})
    p.append({"k": "text", "x": (x_a + x_b) / 2, "y": yB + 10, "s": f"t = {t*100:.0f} cm",
              "size": 8.5, "anchor": "middle", "fill": GRIS, "bold": True})
    p.append({"k": "text", "x": W / 2, "y": H - 6, "s": f"contrafuertes @ {L:.1f} m, t = {t*100:.0f} cm",
              "size": 8, "anchor": "middle", "fill": ACERO})
    return {"titulo": "Planta", "ancho": W, "alto": H, "primitivas": p}


def esquema(entradas: dict, res: Resultado):
    H = entradas["H"]
    B, Bp, D = entradas["B_adop"], entradas["Bprima_adop"], entradas["D_adop"]
    puntera = entradas["puntera_adop"]
    talon = B - Bp - puntera
    Bpanel = H - D
    L, t = entradas["L_adop"], entradas["t_adop"]
    return [_corte(H, B, Bp, D, talon, puntera, Bpanel), _planta(B, Bp, talon, puntera, L, t)]


# --------------------------------------------------------------------------- #
#  Dimensionamiento asistido
# --------------------------------------------------------------------------- #
def sugerir(d: dict) -> dict:
    """Predimensiona B, B', D, puntera, L, t (Sec. 3) e itera hasta que las
    verificaciones de estabilidad, flexion y corte cumplan. El contrafuerte
    (viga) resuelve el corte con estribos cuando hace falta; el talon y la
    puntera (losas) no llevan estribos, se corrigen aumentando el peralte."""
    base = dict(d)
    H = base["H"]

    # Puntos de partida calibrados contra el Ejemplo 15.3 (H=9 -> B'=D=0.4,
    # B=3.6, puntera=2.0); la Sec. 3 del libro da estos rangos solo como
    # tanteo inicial de mano, mas conservador que lo que termina adoptandose
    # en un muro con contrafuertes bien proporcionado.
    Bp = max(round(H / 22 / 0.05) * 0.05, 0.30)
    D = max(round(H / 22 / 0.05) * 0.05, 0.30)
    Bpanel = H - D
    L = max(round(0.65 * Bpanel / 0.1) * 0.1, 3.0)

    B = round(max(0.4 * H, Bp + 0.6) / 0.1) * 0.1
    puntera = max(round(0.55 * B / 0.1) * 0.1, 0.6)
    if puntera >= B - Bp - 0.3:
        puntera = round(0.55 * (B - Bp) / 0.1) * 0.1

    def _prueba(B, puntera, extra=None):
        vals = dict(base, B_adop=B, Bprima_adop=Bp, D_adop=D, puntera_adop=puntera,
                    L_adop=L, t_adop=base.get("t_adop", 0.4),
                    talon_d_adop=base.get("talon_d_adop", 50),
                    puntera_d_adop=base.get("puntera_d_adop", 50),
                    fuste_d_adop=base.get("fuste_d_adop", 30),
                    t_ctf_base=base.get("t_ctf_base", 0.50),
                    s_max_estribo=base.get("s_max_estribo", 30.0),
                    diam_estribo=base.get("diam_estribo", 1.5875), ramas_estribo=base.get("ramas_estribo", 2))
        if extra:
            vals.update(extra)
        return _motor(vals)

    prev = None
    for _ in range(60):
        talon = B - Bp - puntera
        if talon < 0.3:
            B = round((B + 0.1) / 0.1) * 0.1
            continue
        r = _prueba(B, puntera)
        estado = (round(B, 2), round(puntera, 2))
        ok_estab = r["volc_ok"] and r["desliz_ok"] and r["exc_ok"] and r["contacto_ok"]
        if ok_estab:
            if estado == prev:
                break
            prev = estado
            break
        B = round((B + 0.1) / 0.1) * 0.1
        prev = estado

    r = _prueba(B, puntera)

    def _redondear_5cm(valor_cm):
        return max(math.ceil(valor_cm / 5.0) * 5.0, 15.0)

    phi_corte = base.get("phi_corte", 0.85)
    d_corte_fuste = 1.7 * r["V_fuste"] / (phi_corte * 100 * r["Vc"])

    talon_d = _redondear_5cm(r["d_min_talon"] * 1.15)
    puntera_d = _redondear_5cm(r["d_min_punt"] * 1.15)
    fuste_d = _redondear_5cm(max(r["d_min_fuste"] * 1.15, d_corte_fuste * 1.05))
    t_ctf = max(round(Bpanel / 20 / 0.05) * 0.05, 0.30)
    t_ctf_base = t_ctf + 0.10

    # Talon y puntera son losas: el corte se corrige aumentando d (no llevan
    # estribos). Se itera aumentando d de a 5 cm hasta que la seccion critica
    # (a d de la cara) cumpla, re-evaluando con el motor completo.
    for _ in range(20):
        rr = _prueba(B, puntera, {"talon_d_adop": talon_d, "puntera_d_adop": puntera_d,
                                    "fuste_d_adop": fuste_d, "t_ctf_base": t_ctf_base})
        listo = True
        if not rr["corte_talon"]["ok"]:
            talon_d += 5.0
            listo = False
        if not rr["corte_punt"]["ok"]:
            puntera_d += 5.0
            listo = False
        if listo:
            break

    return {
        "B_adop": B, "Bprima_adop": Bp, "D_adop": D, "puntera_adop": puntera,
        "L_adop": L, "t_adop": t_ctf, "t_ctf_base": t_ctf_base,
        "talon_d_adop": talon_d, "puntera_d_adop": puntera_d, "fuste_d_adop": fuste_d,
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
        "contrafuerte (3 secciones, con estribos donde el corte lo requiere)."
    ),
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
        Campo("puntera_adop", "Largo de la puntera adoptado (lado con tierra)  C", "m", 2.0, grupo="Geometria adoptada",
              minimo=0.3, paso=0.1, ayuda="El talon (lado sin tierra) se calcula como B - B' - puntera."),
        Campo("L_adop", "Separacion entre contrafuertes  L", "m", 5.6, grupo="Geometria adoptada", minimo=2.0, paso=0.1),
        Campo("t_adop", "Espesor tipico del contrafuerte  t", "m", 0.4, grupo="Geometria adoptada", minimo=0.3, paso=0.05),
        Campo("t_ctf_base", "Espesor del contrafuerte en la base  t_base", "m", 0.50, grupo="Geometria adoptada",
              minimo=0.3, paso=0.05, ayuda="Suele ensancharse cerca de la base para alojar el acero y resistir corte."),

        Campo("talon_d_adop", "Altura util adoptada del talon", "cm", 50, grupo="Espesores adoptados", minimo=10),
        Campo("puntera_d_adop", "Altura util adoptada de la puntera", "cm", 50, grupo="Espesores adoptados", minimo=10),
        Campo("fuste_d_adop", "Altura util adoptada del fuste", "cm", 30, grupo="Espesores adoptados", minimo=10),

        Campo("mu", "Coeficiente mu (altura minima)", "", 0.1448, grupo="Factores de reduccion", avanzado=True, minimo=0.001),
        Campo("ju", "ju (brazo interno)", "", 0.90, grupo="Factores de reduccion", avanzado=True, minimo=0.5, maximo=1.0),
        Campo("phi_corte", "phi corte", "", 0.85, grupo="Factores de reduccion", avanzado=True, minimo=0.5, maximo=1.0),
        Campo("phi_flexion", "phi flexion", "", 0.90, grupo="Factores de reduccion", avanzado=True, minimo=0.5, maximo=1.0),
        Campo("coef_tanphi_p", "Coeficiente sobre tan(phi2) para friccion base", "", 0.67, grupo="Factores de reduccion",
              avanzado=True, minimo=0.4, maximo=1.0),
        Campo("coef_c_p", "Coeficiente sobre c2 para cohesion base", "", 0.6, grupo="Factores de reduccion",
              avanzado=True, minimo=0.5, maximo=0.75, ayuda="Rango tipico recomendado: 0.5 a 0.75 de c2."),
        Campo("s_max_estribo", "Separacion maxima practica de estribos", "cm", 30.0, grupo="Estribos",
              avanzado=True, minimo=5.0, maximo=60.0,
              ayuda="Tope constructivo adoptado (ademas de s<=d/2); el libro usa 30 cm."),
        Campo("diam_estribo", "Diametro de la pierna del estribo", "cm", 1.5875, grupo="Estribos",
              avanzado=True, minimo=0.6, maximo=2.6, ayuda="1.5875 cm = 5/8 pulgada (valor del ejemplo)."),
        Campo("ramas_estribo", "Ramas del estribo", "", 2, grupo="Estribos", avanzado=True, minimo=2, maximo=6),
    ],
    funcion=calcular,
    tablas_referencia=[TABLA_FUSTE_TRIANGULAR, TABLA_FUSTE_UNIFORME],
    esquema=esquema,
    sugerir=sugerir,
)
