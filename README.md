# Suite de Ingeniería

Suite de calculadoras de ingeniería estructural y de fundaciones, con interfaz web
intuitiva y generación de memorias de cálculo en PDF. La primera calculadora incluida
—**Zapata cuadrada con pedestal**— reproduce exactamente la hoja de cálculo original
de *Suelos, Fundaciones y Muros* (validada contra sus 24 valores).

## Cómo ejecutar

```bash
# 1. Instalar dependencias (una sola vez)
pip install -r requirements.txt

# 2. Levantar la aplicación
streamlit run app.py
```

Se abre en el navegador (`http://localhost:8501`). Es una app web: puedes usarla en
tu equipo, o desplegarla en un servidor / Streamlit Community Cloud para que todo el
equipo la use desde un enlace, sin instalar nada.

## Cómo se usa

1. Elige una calculadora en el inicio o en la barra lateral.
2. Introduce los datos (los factores φ, ju, etc. están en un panel *avanzado* con
   valores por defecto, para no estorbar).
3. Los resultados y las verificaciones (**CUMPLE / NO CUMPLE**) se actualizan solos.
4. Rellena Proyecto / Elemento / Calculó y descarga la **memoria de cálculo en PDF**.

## Cómo agregar tus otras aplicaciones

La suite está diseñada para crecer. Cada calculadora es un módulo independiente que
**solo declara sus datos de entrada y su fórmula**; el formulario, las verificaciones
y el PDF se generan automáticamente.

1. Copia `calculadoras/_plantilla.py.txt` a `calculadoras/mi_calculo.py`.
2. Escribe tu motor (`_motor`), tus campos (`Campo`) y la metadata (`Calculadora`).
3. Guárdalo. Aparece sola en el menú. **No hay que tocar `app.py` ni el PDF.**

Si me pasas tus otras hojas de Excel, puedo convertir cada una en un módulo como el
de la zapata.

## Estructura

```
suite_ingenieria/
├── app.py                     # Interfaz web (Streamlit). No se toca al agregar apps.
├── requirements.txt
├── motor/
│   ├── base.py                # Contratos: Campo, Chequeo, Resultado, Calculadora
│   ├── registro.py            # Descubre las calculadoras automáticamente
│   └── reporte.py             # Genera la memoria de cálculo en PDF (genérico)
├── calculadoras/
│   ├── zapata_pedestal.py     # 1ª calculadora (validada contra el Excel)
│   └── _plantilla.py.txt      # Plantilla para crear nuevas
└── tests/
    └── test_zapata.py         # Verifica el motor contra los valores del Excel
```

## Validación

```bash
python tests/test_zapata.py
# OK — el motor reproduce exactamente los 24 valores del Excel.
```

## Notas de ingeniería

- El motor replica **literalmente** las fórmulas de la hoja original, incluidas sus
  constantes de libro (µ de la Tabla 7.7, coeficientes de aplastamiento 535 / 535.5,
  el factor ·10 en el acero). Están documentadas en `calculadoras/zapata_pedestal.py`.
- La herramienta es una ayuda de cálculo: **verifica siempre** los resultados frente a
  la normativa vigente y el criterio del ingeniero responsable.
