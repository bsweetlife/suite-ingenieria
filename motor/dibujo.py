"""
Motor de dibujo compartido.

Cada esquema se describe con una lista de PRIMITIVAS neutrales (rect, line, text)
en coordenadas con origen arriba-izquierda (como SVG). Dos renderizadores las
convierten:
  - primitivas_a_svg(...)      -> texto SVG para mostrar en la app (vectorial)
  - primitivas_a_drawing(...)  -> Drawing de reportlab para incrustar en el PDF

Asi el dibujo se define UNA sola vez y se ve igual en la app y en la memoria.

Nota: en las etiquetas se evita σ, ², γ porque la fuente estandar del PDF no las
tiene; se usa "cm2", "sadm", etc. La app podria mostrarlas, pero se mantienen
iguales en ambos formatos por coherencia.
"""
from __future__ import annotations

import math

from reportlab.graphics.shapes import Drawing, Rect, Line, String, Group
from reportlab.lib.colors import HexColor

AZUL = "#1f3a5f"
GRIS = "#5b6b7b"
TINTA = "#1a2733"
RELLENO_ZAP = "#e8edf3"
RELLENO_PED = "#d3dce8"
ACERO = "#c0562b"


# --------------------------------------------------------------------------- #
#  Renderizador SVG (para la app)
# --------------------------------------------------------------------------- #
def primitivas_a_svg(esq: dict, max_ancho_px: int = 340) -> str:
    W, H = esq["ancho"], esq["alto"]
    out = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
           f'width="100%" style="max-width:{max_ancho_px}px;height:auto;">']
    for p in esq["primitivas"]:
        k = p["k"]
        if k == "rect":
            fill = p.get("fill") or "none"
            out.append(f'<rect x="{p["x"]:.1f}" y="{p["y"]:.1f}" width="{p["w"]:.1f}" '
                       f'height="{p["h"]:.1f}" fill="{fill}" stroke="{p.get("stroke", AZUL)}" '
                       f'stroke-width="{p.get("sw", 1)}"/>')
        elif k == "line":
            dash = ' stroke-dasharray="4 3"' if p.get("dash") else ""
            out.append(f'<line x1="{p["x1"]:.1f}" y1="{p["y1"]:.1f}" x2="{p["x2"]:.1f}" '
                       f'y2="{p["y2"]:.1f}" stroke="{p.get("stroke", AZUL)}" '
                       f'stroke-width="{p.get("sw", 1)}"{dash}/>')
        elif k == "text":
            rot = f' transform="rotate({p["rot"]} {p["x"]:.1f} {p["y"]:.1f})"' if p.get("rot") else ""
            weight = ' font-weight="600"' if p.get("bold") else ""
            out.append(f'<text x="{p["x"]:.1f}" y="{p["y"]:.1f}" font-size="{p.get("size", 9)}" '
                       f'text-anchor="{p.get("anchor", "start")}" fill="{p.get("fill", TINTA)}" '
                       f'font-family="sans-serif"{weight}{rot}>{p["s"]}</text>')
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
#  Renderizador reportlab (para el PDF)
# --------------------------------------------------------------------------- #
def primitivas_a_drawing(esq: dict, escala: float = 1.0) -> Drawing:
    W, H = esq["ancho"], esq["alto"]
    d = Drawing(W * escala, H * escala)

    def fx(x): return x * escala
    def fy(y): return (H - y) * escala   # voltear eje vertical (reportlab es y-arriba)

    for p in esq["primitivas"]:
        k = p["k"]
        if k == "rect":
            r = Rect(fx(p["x"]), fy(p["y"] + p["h"]), p["w"] * escala, p["h"] * escala)
            r.strokeColor = HexColor(p.get("stroke", AZUL))
            r.strokeWidth = p.get("sw", 1)
            r.fillColor = HexColor(p["fill"]) if p.get("fill") else None
            d.add(r)
        elif k == "line":
            ln = Line(fx(p["x1"]), fy(p["y1"]), fx(p["x2"]), fy(p["y2"]))
            ln.strokeColor = HexColor(p.get("stroke", AZUL))
            ln.strokeWidth = p.get("sw", 1)
            if p.get("dash"):
                ln.strokeDashArray = [3, 2]
            d.add(ln)
        elif k == "text":
            s = String(fx(p["x"]), fy(p["y"]), p["s"])
            s.fontSize = p.get("size", 9)
            s.fillColor = HexColor(p.get("fill", TINTA))
            s.textAnchor = p.get("anchor", "start")
            s.fontName = "Helvetica-Bold" if p.get("bold") else "Helvetica"
            if p.get("rot"):
                # rotar alrededor del punto (X,Y) ya volteado. En SVG el angulo es
                # horario con y-abajo; al voltear a y-arriba se invierte el signo.
                a = math.radians(-p["rot"])
                X, Y = fx(p["x"]), fy(p["y"])
                c, s_ = math.cos(a), math.sin(a)
                g = Group(s)
                g.transform = (c, s_, -s_, c,
                               X - c * X + s_ * Y,
                               Y - s_ * X - c * Y)
                d.add(g)
            else:
                d.add(s)
    return d


# --------------------------------------------------------------------------- #
#  Ayudas de acotado
# --------------------------------------------------------------------------- #
def cota_h(x1, x2, y, etiqueta, arriba=False, color=GRIS):
    p = [{"k": "line", "x1": x1, "y1": y, "x2": x2, "y2": y, "stroke": color, "sw": 0.8}]
    for xx in (x1, x2):
        p.append({"k": "line", "x1": xx, "y1": y - 4, "x2": xx, "y2": y + 4,
                  "stroke": color, "sw": 0.8})
    ty = y - 5 if arriba else y + 11
    p.append({"k": "text", "x": (x1 + x2) / 2, "y": ty, "s": etiqueta, "size": 8.5,
              "anchor": "middle", "fill": color, "bold": True})
    return p


def cota_v(x, y1, y2, etiqueta, color=GRIS):
    p = [{"k": "line", "x1": x, "y1": y1, "x2": x, "y2": y2, "stroke": color, "sw": 0.8}]
    for yy in (y1, y2):
        p.append({"k": "line", "x1": x - 4, "y1": yy, "x2": x + 4, "y2": yy,
                  "stroke": color, "sw": 0.8})
    p.append({"k": "text", "x": x - 7, "y": (y1 + y2) / 2, "s": etiqueta, "size": 8.5,
              "anchor": "middle", "fill": color, "bold": True, "rot": -90})
    return p
