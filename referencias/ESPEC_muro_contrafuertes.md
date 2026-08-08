# Especificación — Calculadora "Muro de contención con contrafuertes"

Fuente: María Fratelli, *Suelos, Fundaciones y Muros*, **Capítulo 15** (págs. 474–499).
Objetivo: construir un módulo del suite (`calculadoras/muro_contrafuertes.py`) que
diseñe un muro de contención con contrafuertes, con la misma arquitectura que la
zapata (motor puro + `Resultado` + verificaciones CUMPLE/NO CUMPLE + esquema + PDF),
validado contra el **Ejemplo 15.3** del libro.

> Es una calculadora bastante más grande que la zapata: tiene 4 sub-diseños
> (estabilidad global, fuste, talón/puntera, contrafuertes). Conviene implementarla
> por partes y validar cada una contra el ejemplo.

---

## 1. Datos de entrada

**Suelo contenido (relleno):** γs [kg/m³], φ [°], c [kg/cm²], β (inclinación del talud, °),
Ka (coef. empuje activo; de tablas de Rankine 14.5, o `Ka = tan²(45−φ/2)` si β=0).
**Suelo de apoyo (fundación):** γs2 [kg/m³], φ2 [°], c2 [kg/cm²], Kp (coef. empuje pasivo,
tabla 14.6 o `Kp = tan²(45+φ2/2)`), σadm [kg/cm²].
**Sobrecarga:** q [kg/m²] sobre el relleno.
**Materiales:** f'c [kg/cm²], fy [kg/cm²], γc [kg/m³] (=2500).
**Geometría a contener:** H [m] (altura total del muro).

Dimensiones adoptadas (se predimensionan y el usuario ajusta — ver §3):
B (ancho de base), B' (espesor del fuste), D (espesor de la losa de base),
puntera, talón, L (separación entre ejes de contrafuertes), t (espesor del contrafuerte).

---

## 2. Empujes de tierra (Cap. 14, usados aquí)

Presión activa horizontal a profundidad z (con cohesión y sobrecarga):

    σa(z) = (q + γs·z)·Ka − 2c·√Ka

- El término `−2c·√Ka` produce **tracción** en la parte superior → esa zona se ignora.
- Profundidad donde σa=0:  z0 = (2c·√Ka − q·Ka)/(γs·Ka).
- Empuje activo resultante (triángulo/trapecio de la parte a compresión). En el ejemplo:
  `σa_max = −616 + γs·H·Ka` y `Ea = σa_max · H_efectiva / 2`, aplicado a `H_efectiva/3` del pie.

Presión pasiva (resistente, delante del pie, sobre la profundidad D_p de empotramiento):

    σp(z) = 2c2·√Kp + γs2·z·Kp
    Ep = (σp1 + σp_max)·D_p / 2      con  σp1 = 2c2·√Kp

Componentes del empuje activo si β≠0:  Eav = Ea·senβ ,  Eah = Ea·cosβ.

---

## 3. Predimensionado (tanteo inicial)

- Ancho de base:            B ≈ 0,4 a 0,7 H
- Espesor del fuste:        B' ≈ H/12 a H/10   (mín. 25–30 cm en el tope)
- Espesor losa de base:     D ≈ H/12 a H/10
- Separación contrafuertes: L ≈ 0,5 a 1,5 · B_panel   (B_panel = altura del fuste sobre la base)
- Relación de aspecto del panel:  B_panel / L  (entra a las Tablas 15.1/15.2)
- Espesor del contrafuerte: t ≥ 30 cm (aumentar a ~50 cm en el pie si el acero no cabe)
- Pendiente mínima del paramento exterior: 1:48.
- Los muros con contrafuertes se usan cuando H > 7 m (por debajo, Cantilever).
  Si H > 10 m, conviene volados horizontales intermedios en el fuste.

---

## 4. Estabilidad global (por metro de muro)

Cargas gravitacionales Wi con sus brazos ci respecto al punto I (extremo del talón):
peso del fuste, peso de la losa de base (pie), peso del suelo sobre el talón,
sobrecarga sobre el talón, peso de contrafuertes repartido (W_contrafuerte / L).

    R = Σ Wi + Eav
    M_volc  = Eah · h1                                  (h1 = brazo de Eah)
    M_estab = Σ Wi·ci + Eav·B  (+ Ep·h2 si se cuenta el pasivo)

**Verificaciones:**

| # | Verificación | Condición |
|---|---|---|
| 1 | Vuelco | `FS_volc = M_estab / M_volc ≥ 1,5` (sin pasivo) o `≥ 2` (con pasivo) |
| 2 | Deslizamiento | `FS_desliz = Fr / Eah ≥ 1,5` (sin pasivo) o `≥ 2` (con pasivo) |
| 3 | Excentricidad | `e = B/2 − x ≤ B/6`,  con `x = (M_estab − M_volc)/R` |
| 4 | Presión de contacto | `σmax = R/(B·1m)·(1 + 6e/B) ≤ σadm`  y  `σmin ≥ 0` |

Resistencia al deslizamiento:  `Fr = R·tanφ' + c'·B (+ Ep)`, con `tanφ' = 0,67·tanφ2`,
`c' = 0,5 a 0,75·c2`. (Si el suelo del talón es removible, no contar Ep.)

---

## 5. Diseño del fuste (placas entre contrafuertes)

El fuste, dividido por los contrafuertes, se diseña como **placas** con 3 bordes
empotrados y 1 libre (el tope), bajo empuje **triangular**. Dos caminos:

### 5.a Teoría de placas (Tablas 15.1/15.2)

Con la relación de aspecto `B_panel/L`, se interpolan los coeficientes y:

    Momentos:  Mx = β·q0·L² ,  My = β'·q0·L²      (q0 = presión máxima en la base del panel)
    Reacciones (sobre el contrafuerte):  V = γ·q0·L
    (Tabla 15.1 → carga uniforme;  Tabla 15.2 → carga triangular, usar q0)

Puntos: 1(x=0,y=B), 2(x=0,y=B/2), 3(x=L/2,y=B), 4(x=L/2,y=B/2), 0(x=0,y=0).
El momento de diseño gobernante es el mayor |M| de los puntos; `Mu = 1,7·M`.

### 5.b Método aproximado (envolvente) — recomendado para el programa

El fuste se analiza como **losa/viga continua horizontal** apoyada en los contrafuertes,
en franjas horizontales. En cada franja, carga uniforme = promedio del empuje trapecial
de esa altura. Momentos por franja (q = empuje medio de la franja, L = separación):

    Tercio inferior:   M⁻ = qL²/14 a qL²/12         (15.35)
    Franjas superiores:M⁻ = qL²/10 a qL²/9          (15.36)
    Positivos (vano):  M⁺ = qL²/11 a qL²/16         (15.37)

Acero por franja:  `As = Mu / (0,81·fy·d) ≥ As_min` (0,81 = φ·ju = 0,9·0,9).
Verificar corte:  `vu = 1,7·V/(φ·b·d) ≤ vc = 0,53·√f'c` (φ=0,85, b=1 m).
Acero mínimo (retracción/temp) `As_min = 0,18·d` como malla en la cara comprimida;
acero horizontal ≈ As/3 junto al paramento interno.

---

## 6. Diseño del talón y la puntera (losas de la base)

- **Talón:** losa en voladizo empotrada en el fuste. Carga hacia arriba = reacción del
  suelo; hacia abajo = peso propio + tierra + sobrecarga. `V1`, `M1 = V1·brazo`,
  `Mu = 1,7·M1`, se despeja `d` con `d ≥ √(Mu/(μ·f'c·b))`, μ=0,1448, b=1 m.
- **Puntera:** si su relación de aspecto `C/L < 0,5` (C = largo de la puntera), las franjas
  se analizan como **empotradas en el fuste y libres en el extremo** (voladizo). Si no,
  se analiza como placa (igual que el fuste). Carga `q` = sobrecarga + peso de tierra +
  peso propio. Mismo criterio de `Mu`, `d`, acero.
- En la unión fuste–pie se coloca un chaflán a 45° y se verifica el corte mayorado.

---

## 7. Diseño de los contrafuertes

El contrafuerte se diseña como **viga en voladizo vertical** (altura = B_panel),
empotrada en la base, cuya alma triangular resiste flexión por el empuje del suelo y
compresión por peso propio (la compresión es pequeña → se cubre con acero mínimo y se
verifica pandeo). Se toma el empuje **directo** sobre el ancho tributario L.

    σB = γs·B_panel·Ka             (presión horizontal en la base del contrafuerte)   (15.38)
    σL = σB·L                      (carga lineal sobre el contrafuerte)
    EaL = σL·B_panel/2 = σB·L·B_panel/2   (resultante triangular sobre 1 contrafuerte)  (15.42)

En varias secciones a lo largo de la altura (0,1,2,…) se obtienen V y M del empuje
triangular acumulado. Para cada sección, con `θ` = pendiente del paramento inclinado
del contrafuerte y `d = 0,9·h` (h = canto del contrafuerte en esa sección):

    Mu = 1,7·M
    As = Mu / (φ·fy·ju·d) / cosθ  ≥ As_min      (φ = ju = 0,9)                     (15.43)
    Rv = T·cosθ                                                                    (15.44)

Acero principal en el **borde inclinado** (traccionado), anclado en el paramento exterior
del fuste. Acero de paramento (retracción/temp) ≈ 0,1·As_princ (mín. `14/fy·b·d`) en ambas
caras + ligaduras/estribos cerrados. Verificar corte con estribos:
`vu = 1,7·V/(φ·b·d)`, si `vu > vc` → `s = Av·fy/(vs·bw)` con `vs = vu − vc`, `s ≤ d/2`.

**Criterio alternativo de Huntington (fig 15.14), útil como verificación rápida:**

    M⁻ ≈ 0,003·σB·L·B_panel ,   M⁺ = M⁻/4 ,   V ≈ 0,2·σB·B_panel

---

## 8. Lista de verificaciones (para los `Chequeo` del módulo)

1. Vuelco (`FS_volc`)   2. Deslizamiento (`FS_desliz`)   3. Excentricidad (`e ≤ B/6`)
4. Presión de contacto (`σmax ≤ σadm`, `σmin ≥ 0`)
5. Corte en el fuste (`vu ≤ vc`)   6. Corte en talón y puntera (`vu ≤ vc`)
7. Corte en el contrafuerte (`vu ≤ vc` o estribos)   8. Espesores `d` suficientes en cada elemento.

---

## 9. Tablas de placas (bordes: 3 empotrados, 1 libre)

`Mx = β·q·L²`, `My = β'·q·L²`, `V = γ·q·L`, `δ = α·q·L⁴/D` (D=E·I, μ=1/6).
Puntos: 1(x=0,y=B), 2(x=0,y=B/2), 3(x=L/2,y=B), 4(x=L/2,y=B/2), 0(x=0,y=0).

### Tabla 15.1 — carga uniformemente distribuida

| B/L | α1 | β1 | α2 | β2 | β2' | β3 | γ3 | β4 | γ4 | β5 | γ5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
|0,6|0,00271|0,0336|0,00129|0,0168|0,0074|−0,0745|0,750|−0,0365|0,297|−0,0554|0,416|
|0,7|0,00292|0,0371|0,00159|0,0212|0,0097|−0,0782|0,717|−0,0139|0,346|−0,0545|0,413|
|0,8|0,00308|0,0401|0,00185|0,0252|0,0116|−0,0812|0,685|−0,0505|0,385|−0,0535|0,410|
|0,9|0,00323|0,0425|0,00209|0,0287|0,0129|−0,0836|0,656|−0,0563|0,414|−0,0523|0,406|
|1,0|0,00333|0,0444|0,00230|0,0317|0,0138|−0,0853|0,628|−0,0614|0,435|−0,0510|0,401|
|1,25|0,00345|0,0447|0,00269|0,0374|0,0142|−0,0867|0,570|−0,0708|0,475|−0,0470|0,388|
|1,5|0,00335|0,0454|0,00290|0,0402|0,0118|−0,0842|0,527|−0,0755|0,491|−0,0418|0,373|

### Tabla 15.2 — carga triangular (usar q0 = presión máx. en la base)

| B/L | α1 | β1 | α2 | β2 | β2' | β3 | γ3 | β4 | γ4 | β5 | γ5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
|0,6|0,00069|0,0089|0,00044|0,0060|0,0062|−0,0179|0,093|−0,0131|0,136|−0,0242|0,248|
|0,7|0,00069|0,0093|0,00058|0,0080|0,0074|−0,0172|0,081|−0,0170|0,158|−0,0264|0,262|
|0,8|0,00068|0,0096|0,00072|0,0100|0,0083|−0,0164|0,069|−0,0206|0,177|−0,0278|0,275|
|0,9|0,00067|0,0096|0,00085|0,0118|0,0090|−0,0156|0,057|−0,0239|0,194|−0,0290|0,286|
|1,0|0,00065|0,0095|0,00097|0,0135|0,0094|−0,0146|0,045|−0,0269|0,209|−0,0299|0,295|
|1,25|0,00056|0,0085|0,00121|0,0169|0,0092|−0,0119|0,018|−0,0327|0,234|−0,0306|0,309|
|1,5|0,00042|0,0065|0,00138|0,0191|0,0075|−0,0087|−0,006|−0,0364|0,245|−0,0291|0,311|

(β1 de la Tabla 15.1 a B/L=1,25 en el libro aparece como 0,0167; es errata evidente,
usar ≈0,0447 por interpolación.)

---

## 10. Ejemplo de validación — EJEMPLO 15.3 (H = 9 m)

**Datos:** Relleno γs=1850, φ=30°, c=0,088 kg/cm² (=880 kg/m²), Ka=1/3.
Apoyo γs2=2000, φ2=34°, c2=0,4 kg/cm² (=4000 kg/m²), Kp=3,537, σadm=2,8 kg/cm².
Sobrecarga q=1200 kg/m². f'c=200, fy=4200, γc=2500. H=9 m.
Geometría: B=3,6 m, B'=0,4 m, D=0,6 m, puntera C=2 m, L=5,6 m, t=40 cm, B_panel=8,4 m.

**Resultados esperados (para el test):**

- Empuje activo: `σa_max = −616 + 1850·9·(1/3) = 4934 kg/m²`; `Ea = 4934·8/2 = 19.736 kg/m`; brazo 2,67 m.
- Pasivo: `σp1 = 2·4000·√3,537 = 15.045`; `σp_max = 15.045 + 2000·1,2·3,537 = 23.533`; `Ep = 23.147 kg/m`.
- Cargas: W1(fuste)=8.400 (brazo 1,4), W2(pie)=5.400 (1,8), W3(suelo)=31.080 (2,6),
  Q=2.400 (2,6), W4(contrafuerte)=1.500 (2,27).  **R = 48.780 kg/m**, **M_estab = 111.933 kgm/m**.
- `M_volc = 19.736·2,67 = 52.695`.  **FS_volc = 2,12** (sin pasivo) / **2,37** (con pasivo).
- `Fr = 30.684 kg`.  **FS_desliz = 1,55** (sin pasivo) / **2,72** (con pasivo).
- `x = 1,2 m`, `e = 0,6 m = B/6`. `σmax = 2,71 kg/cm² < σadm`, `σmin = 0`.
- Talón: `V1=25.320 kg`, `M1=16,2 tm`, `Mu=27,54 tm`, d≥30 (se usa 50).
- Puntera: C/L=0,357<0,5 → voladizo; `q=1.824 kg/m²`, `Mu=44,7 tm`, d≥40.
- **Fuste (Tabla 15.2, B/L=1,5, q0=4.563 kg/m²), `q0·L²=143.096`:**
  - M⁺x1 = 0,0065·q0L² = **930 kgm**
  - M⁺x2 = 0,0191·q0L² = **2.733 kgm**
  - M⁺y2 = 0,0075·q0L² = **1.073 kgm**
  - M⁻x3 = −0,0087·q0L² = **−1.245 kgm**
  - M⁻x4 = −0,0364·q0L² = **−5.208 kgm**
  - M⁻y0 = −0,0291·q0L² = **−4.164 kgm**  → gobierna;  `Mu = 1,7·4.164 = 7.078 kgm`, d≥16 (se usa 30).
- **Contrafuertes** (4 secciones, de arriba hacia el pie):
  | Sección | M (tm) | Mu=1,7M (tm) | h (m) | d=0,9h (m) | As (cm²) | Armado |
  |---|---|---|---|---|---|---|
  | 1 | 3,358 | 5,708 | 1,07 | 0,963 | 1,78 (< As_min 12,8) | 3 Ø1" |
  | 2 | 56,034 | 95,258 | 1,73 | 1,557 | 18,50 | 4 Ø1" |
  | 3 | 233,262 | 396,545 | 2,40 | 2,160 | 55,47 | 11 Ø1" |
  | 4 | 290,000 | 493,000 | 2,40 | 2,160 | 68,96 | 14 Ø1" |
  - Corte: N1 vu=2,9<vc=7,49 (OK); N2 vu=11,73>vc → estribos Ø5/8" 2 ramas @30;
    N3 vu=17,51>vc → estribos @30. Acero paramento Ø1/2"@20 (ambas caras).

Si el módulo reproduce estos números, el motor está correcto.

---

## 11. Cómo encaja en el suite (para implementar como el de zapatas)

- Motor puro `_motor(d)` con TODAS las fórmulas anteriores; `calcular(d)->Resultado`
  armando `Valor` (empujes, R, momentos, σ, As de cada elemento), `Chequeo` (las 8
  verificaciones de §8) y `resumen` (B, D, B', L, t, armados).
- `campos`: los datos de §1 (agrupados en Cargas/Suelo relleno/Suelo apoyo/Materiales/Geometría),
  con los factores φ, ju en un grupo avanzado.
- `esquema(entradas, res)`: dibujar **corte** (muro con talud, empujes, dimensiones H, B, D)
  y **planta** (fuste, contrafuertes cada L, talón/puntera). Usar `Ø`, `cm2`, sin griegas.
- `sugerir(entradas)`: predimensionar B, B', D, L, t (§3) y —como en la zapata— iterar
  hasta que las 8 verificaciones cumplan.
- `tablas_referencia`: incluir Tabla 15.1 y 15.2 (§9) con títulos genéricos (sin "Tabla 15.x").
- `tests/test_muro_contrafuertes.py`: validar `_motor` contra los números del §10.

> Sugerencia de implementación por fases (validando cada una contra el ejemplo 15.3):
> 1) Empujes + estabilidad (§2–§4).  2) Fuste por método aproximado y placas (§5).
> 3) Talón/puntera (§6).  4) Contrafuertes (§7).  5) Esquema + sugerir + PDF.

---

## Notas de implementación (post-validación, ver también el módulo y los tests)

Estos puntos se resolvieron mientras se implementaba el módulo, reconciliando
numéricamente los datos de este documento con la geometría real del Ejemplo 15.3
(ver docstring de `calculadoras/muro_contrafuertes.py` y comentarios en el motor):

- **Dp (profundidad de empotramiento del pasivo, §2) no está en la lista de §1.**
  Se agregó como campo nuevo (`Dp_adop`, 1.2 m en el ejemplo) — es el único valor
  que reproduce `Ep=23.147 kg/m` exacto.
- **Terminología talón/puntera:** en el motor, "puntera" = lado con tierra +
  sobrecarga + contrafuerte (C=2.0 m, C/L=0.357) y "talón" = lado sin tierra
  (~1.2 m), confirmado con los V1/M1/Mu de la sección 6 y validado con 5
  coincidencias numéricas independientes en la tabla de estabilidad (pesos y
  brazos W1–W4).
- **Contrafuerte (§7):** la carga horizontal usa el mismo recorte por tracción
  z0 que el empuje activo global (§2), no solo `σB = γs·B_panel·Ka` como sugiere
  la fórmula 15.38 literal. Con ese ajuste, 3 secciones a y=B_panel/3, 2B_panel/3
  y B_panel reproducen las filas 1–3 de la tabla del §10 dentro de ~2%. La fila 4
  (misma sección base, M=290 tm en vez de 233 tm) no se pudo derivar de las
  fórmulas de este documento — probablemente incluye un efecto adicional
  (p.ej. la reacción de la losa de la puntera sobre el contrafuerte).
- **Fuste:** el ejemplo usa My0 como momento gobernante aunque Mx4 es mayor en
  magnitud (posiblemente por continuidad constructiva del acero hacia el
  contrafuerte, no por ser el mayor valor absoluto).
- **Huntington:** la fórmula `M⁻ ≈ 0,003·σB·L·B_panel` no cierra dimensionalmente
  (da kg, no kg·m). No se pudo corregir con confianza sin la fuente original;
  se eliminó del módulo en vez de dejarla con una corrección adivinada.
