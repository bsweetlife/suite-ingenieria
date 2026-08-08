"""
Generador de memoria de calculo en PDF.

Es generico: recibe cualquier Calculadora + sus entradas + su Resultado y produce
un PDF profesional. Sirve para todas las calculadoras del suite sin cambios.
"""
from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

from motor.base import Calculadora, Resultado
from motor.dibujo import primitivas_a_drawing

_AZUL = colors.HexColor("#1f3a5f")
_GRIS = colors.HexColor("#5b6b7b")
_VERDE = colors.HexColor("#1b7f3b")
_ROJO = colors.HexColor("#b3261e")

# La fuente estandar del PDF (Helvetica) no tiene griegas ni varios simbolos
# matematicos; se reemplazan por equivalentes ASCII para que no salgan cuadritos.
_MAPA_PDF = {
    "σ": "s", "γ": "g", "μ": "u", "√": "raiz ", "φ": "phi",
    "≈": "~", "≥": ">=", "≤": "<=", "→": "->", "≠": "!=",
}


def _s(x) -> str:
    t = str(x)
    for a, b in _MAPA_PDF.items():
        t = t.replace(a, b)
    return t


def _estilos():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("Titulo", parent=ss["Title"], textColor=_AZUL, fontSize=17))
    ss.add(ParagraphStyle("Seccion", parent=ss["Heading2"], textColor=_AZUL,
                           fontSize=12, spaceBefore=12, spaceAfter=4))
    ss.add(ParagraphStyle("Pie", parent=ss["Normal"], fontSize=7.5, textColor=_GRIS))
    ss.add(ParagraphStyle("Meta", parent=ss["Normal"], fontSize=9, textColor=_GRIS))
    return ss


def _tabla(datos, anchos, encabezado=True):
    ss = getSampleStyleSheet()
    estilo_celda = ParagraphStyle("Celda", parent=ss["Normal"], fontSize=9, leading=11)
    estilo_encabezado = ParagraphStyle("CeldaEnc", parent=estilo_celda, textColor=colors.white,
                                        fontName="Helvetica-Bold")

    def _celda(c, es_encabezado):
        texto = _s(c)
        return Paragraph(texto, estilo_encabezado if es_encabezado else estilo_celda)

    datos = [[_celda(c, encabezado and i == 0) for c in fila]
             for i, fila in enumerate(datos)]
    t = Table(datos, colWidths=anchos, hAlign="LEFT")
    estilo = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dfe4ea")),
    ]
    if encabezado:
        estilo += [
            ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(estilo))
    return t


def generar_pdf(calc: Calculadora, entradas: dict, res: Resultado,
                proyecto: str = "", elemento: str = "",
                autor: str = "") -> bytes:
    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        title=f"Memoria de calculo - {calc.nombre}",
    )
    ss = _estilos()
    E = []

    E.append(Paragraph("MEMORIA DE CÁLCULO", ss["Titulo"]))
    E.append(Paragraph(_s(calc.nombre), ss["Seccion"]))
    if calc.referencia:
        E.append(Paragraph(f"Referencia: {_s(calc.referencia)}", ss["Meta"]))
    meta = []
    if proyecto: meta.append(f"Proyecto: {proyecto}")
    if elemento: meta.append(f"Elemento: {elemento}")
    if autor:    meta.append(f"Calculó: {autor}")
    meta.append(f"Fecha: {date.today().isoformat()}")
    E.append(Paragraph(" &nbsp;|&nbsp; ".join(meta), ss["Meta"]))
    E.append(Spacer(1, 6))
    E.append(HRFlowable(width="100%", thickness=1, color=_AZUL))

    # ---- Datos de entrada ----
    E.append(Paragraph("1. Datos de entrada", ss["Seccion"]))
    grupos: dict[str, list] = {}
    for campo in calc.campos:
        grupos.setdefault(campo.grupo, []).append(campo)
    for grupo, campos in grupos.items():
        filas = [[grupo, "Valor", "Unidad"]]
        for c in campos:
            v = entradas.get(c.clave, c.defecto)
            v = f"{v:g}" if isinstance(v, (int, float)) else str(v)
            filas.append([c.etiqueta, v, c.unidad])
        E.append(_tabla(filas, [9 * cm, 3.5 * cm, 3.5 * cm]))
        E.append(Spacer(1, 6))

    # ---- Resultados ----
    E.append(Paragraph("2. Resultados del calculo", ss["Seccion"]))
    filas = [["Variable", "Fórmula", "Valor", "Unidad"]]
    for v in res.valores:
        filas.append([v.etiqueta, v.formula, f"{v.valor:,.{v.decimales}f}", v.unidad])
    E.append(_tabla(filas, [6 * cm, 5 * cm, 3 * cm, 2 * cm]))

    # ---- Verificaciones ----
    E.append(Paragraph("3. Verificaciones", ss["Seccion"]))
    filas = [["Verificación", "Condición", "Resultado"]]
    for c in res.chequeos:
        color = "#1b7f3b" if c.cumple else "#b3261e"
        veredicto_cell = f'<font color="{color}"><b>{"CUMPLE" if c.cumple else "NO CUMPLE"}</b></font>'
        filas.append([c.nombre, f"{c.izquierda}  {c.relacion}  {c.derecha}", veredicto_cell])
    E.append(_tabla(filas, [5.5 * cm, 7.5 * cm, 3 * cm]))
    E.append(Spacer(1, 6))
    veredicto = "DISEÑO CONFORME" if res.conforme else "REVISAR: alguna verificación no cumple"
    E.append(Paragraph(
        f'<b><font color="{"#1b7f3b" if res.conforme else "#b3261e"}">{veredicto}</font></b>',
        ss["Normal"]))

    # ---- Esquema (dibujo) ----
    esquema_fn = getattr(calc, "esquema", None)
    if esquema_fn:
        try:
            vistas = esquema_fn(entradas, res)
            celdas = []
            for e in vistas:
                dib = primitivas_a_drawing(e, escala=0.62)
                celdas.append([Paragraph(f"<b>{e['titulo']}</b>", ss["Meta"]), dib])
            # una tabla con las vistas lado a lado
            fila_titulos = [c[0] for c in celdas]
            fila_dibujos = [c[1] for c in celdas]
            E.append(Paragraph("Esquema", ss["Seccion"]))
            t = Table([fila_titulos, fila_dibujos], hAlign="LEFT")
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("BOTTOMPADDING", (0, 0), (-1, 0), 2)]))
            E.append(t)
        except Exception:  # noqa
            pass

    # ---- Diseno final ----
    if res.resumen:
        E.append(Paragraph("4. Diseño adoptado", ss["Seccion"]))
        filas = [["Concepto", "Valor", "Unidad"]]
        for v in res.resumen:
            filas.append([v.etiqueta, f"{v.valor:,.{v.decimales}f}", v.unidad])
        E.append(_tabla(filas, [8 * cm, 4 * cm, 4 * cm]))

    if getattr(res, "armado_texto", ""):
        E.append(Spacer(1, 8))
        E.append(Paragraph("Armado sugerido", ss["Seccion"]))
        E.append(Paragraph(_s(res.armado_texto), ss["Normal"]))

    if res.notas:
        E.append(Spacer(1, 8))
        for n in res.notas:
            E.append(Paragraph(f"• {_s(n)}", ss["Meta"]))

    def _pie(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(_GRIS)
        canvas.drawString(2 * cm, 1 * cm,
                          "Generado con Suite de Ingeniería — verificar según normativa vigente.")
        canvas.drawRightString(19 * cm, 1 * cm, f"Página {documento.page}")
        canvas.restoreState()

    doc.build(E, onFirstPage=_pie, onLaterPages=_pie)
    return buff.getvalue()
