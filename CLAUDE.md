# Suite de Ingeniería — Guía para Claude Code

Suite de calculadoras de ingeniería estructural y de fundaciones, hecho en Python +
Streamlit. Cada calculadora es un **módulo autónomo** que solo declara sus datos de
entrada y su fórmula; la interfaz web, las verificaciones, el dibujo y la memoria PDF
se generan solos desde esa descripción. Al agregar una calculadora **no se toca `app.py`**.

## Comandos

- Preparar entorno (una vez): `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Ejecutar en local: `streamlit run app.py`  (abre http://localhost:8501)
- Validar: `python tests/test_zapata.py`  (comprueba el motor contra la hoja Excel)
- Publicar: `git add . && git commit -m "..." && git push`  (la nube se actualiza sola)

## Arquitectura

- `app.py` — interfaz genérica (Streamlit). **No se modifica al agregar calculadoras.**
- `motor/base.py` — contratos: `Campo`, `Chequeo`, `Valor`, `Resultado`, `Calculadora`.
- `motor/registro.py` — descubre solo los módulos de `calculadoras/` que definan `CALCULADORA`.
- `motor/dibujo.py` — primitivas neutrales → SVG (app) y Drawing de reportlab (PDF).
- `motor/reporte.py` — memoria de cálculo PDF genérica (sirve para todas).
- `motor/auth.py` — login por contraseña compartida (lee `app_password` de Secrets).
- `calculadoras/` — un archivo por calculadora; cada uno expone `CALCULADORA`.
- `datos/` — tablas compartidas (`suelos.py`, `acero.py`).
- `tests/` — validación contra referencias conocidas (Excel/libro).

## Cómo agregar una calculadora nueva

1. Copia `calculadoras/_plantilla.py.txt` a `calculadoras/mi_calculo.py`.
2. Implementa, en ese archivo:
   - `_motor(d: dict) -> dict` — fórmulas puras, sin nada de interfaz.
   - `calcular(d: dict) -> Resultado` — arma `Valor`/`Chequeo`/`resumen`/`notas`.
   - `CALCULADORA = Calculadora(id=..., nombre=..., categoria=..., descripcion=..., campos=[Campo(...), ...], funcion=calcular, ...)`
3. Crea `tests/test_mi_calculo.py` validando `_motor` contra la fuente (Excel/libro).
4. Listo: aparece sola en el menú, con formulario y PDF automáticos.

### Contrato (ver `motor/base.py`)

- `Campo(clave, etiqueta, unidad, defecto, ayuda, grupo, tipo, opciones, minimo, maximo, paso, avanzado)`
- `Chequeo(nombre, izquierda, relacion, derecha, cumple, comentario)`
- `Valor(clave, etiqueta, valor, unidad, formula, decimales)`
- `Resultado(valores, chequeos, resumen, notas, armado_texto)`; `.conforme` = todos los chequeos cumplen.
- `Calculadora(..., campos, funcion, referencia, icono, tablas_referencia, guia_suelo, guia_suelo_destino, esquema, sugerir)`

### Extras opcionales de `Calculadora`

- `tablas_referencia`: lista de `{titulo, nota, columnas, filas}` — se muestran en la app y el PDF.
- `guia_suelo` (`{material: valor}`) + `guia_suelo_destino` (clave de un `Campo`): selector que autocompleta ese campo.
- `esquema(entradas, res) -> list[dict]`: dibujo(s). Cada dict es `{titulo, ancho, alto, primitivas}`; construir con `cota_h`/`cota_v` y primitivas `rect`/`line`/`text` de `motor/dibujo.py`.
- `sugerir(entradas) -> {clave: valor}`: dimensionamiento asistido. **Debe devolver valores que hagan cumplir TODAS las verificaciones.** Si una verificación depende de otra variable (p. ej. el factor γ depende de la geometría), **iterar hasta converger** — no basta con un subconjunto de chequeos.

## Convenciones (importantes)

- **Validación primero**: replica la fuente (Excel/libro) celda por celda y agrega un test antes de extender.
- **Dibujos y PDF sin símbolos que la fuente del PDF no tiene**: nada de griegas (σ, γ, φ, µ) ni `√` en el texto de los dibujos. Usar `Ø` para diámetro de barra, `cm2`, `raiz`, etc. El PDF ya sanea σ/γ/µ/√/≈/≥ vía `_s()` en `motor/reporte.py`, pero el texto de `esquema` debe evitarlas directamente.
- **No mostrar referencias a tablas del libro en la interfaz** (p. ej. "(Tabla 7.4)"). Las tablas se pueden incluir como referencia, pero con títulos genéricos.
- **Resultados compactos**: no usar `st.metric` (se ve enorme); usar tarjetas pequeñas como en `app.py`.
- **`sugerir` verifica TODAS las verificaciones**, nunca un subconjunto.
- Idioma: español. Unidades: kg, cm, kg/cm², kg/m³, m.

## Despliegue y relación con GitHub

- El repositorio **`bsweetlife/suite-ingenieria`** (rama `main`) es la **fuente de verdad**.
- **Streamlit Community Cloud** está conectado a ese repo (archivo principal `app.py`). Cada `git push` a `main` hace que la app en la nube **se reconstruya sola** en 1-2 minutos. No se sube nada a mano a Streamlit.
- La **contraseña** del login va en **Streamlit → Manage app → Settings → Secrets** como `app_password = "..."`. **Nunca** en el código (el repo puede ser público).
- `.gitignore` excluye `.venv/`, `__pycache__/` y `.streamlit/secrets.toml` (este último no se sube nunca).
- Python 3.12 en la nube (igual que en local).

## Flujo recomendado con Claude Code

1. Abrir Claude Code en la raíz del repo (`claude`).
2. Describirle la calculadora nueva: la fuente (hoja Excel o fórmulas), los datos de entrada y las verificaciones que debe pasar.
3. Claude crea `calculadoras/xxx.py` + `tests/test_xxx.py`, valida contra la fuente, y tú revisas.
4. `git push` para publicar.
