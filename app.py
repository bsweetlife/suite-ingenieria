"""
Suite de Ingenieria — aplicacion Streamlit.

Ejecutar:   streamlit run app.py

La interfaz se genera automaticamente a partir de las calculadoras registradas
en el paquete `calculadoras`. Para agregar una calculadora nueva no hay que tocar
este archivo: basta con crear su modulo.
"""
from __future__ import annotations

import streamlit as st

from motor.registro import cargar_calculadoras, por_categoria
from motor.base import Calculadora, Resultado
from motor.reporte import generar_pdf
from motor.dibujo import primitivas_a_svg
from motor.auth import requiere_login


st.set_page_config(page_title="Suite de Ingeniería", page_icon="🏗️", layout="wide")

# --------------------------------------------------------------------------- #
#  Estilos
# --------------------------------------------------------------------------- #
st.markdown("""
<style>
  .stApp { background: #f5f7fa; }
  section[data-testid="stSidebar"] { background: #1f3a5f; }
  section[data-testid="stSidebar"] * { color: #eaf0f6 !important; }
  .tarjeta { background:#fff;border:1px solid #e2e8f0;border-radius:12px;
             padding:18px 20px;height:100%; }
  .chip-ok  { background:#e7f6ec;color:#1b7f3b;border-radius:20px;
              padding:2px 12px;font-weight:600;font-size:0.85rem; }
  .chip-no  { background:#fdecea;color:#b3261e;border-radius:20px;
              padding:2px 12px;font-weight:600;font-size:0.85rem; }
  /* Alinea las cajas de entrada aunque las etiquetas ocupen 1 o 2 lineas */
  div[data-testid="stNumberInput"] label,
  div[data-testid="stTextInput"] label,
  div[data-testid="stSelectbox"] label {
      min-height: 2.8em;
      align-items: flex-start;
      line-height: 1.25;
  }
</style>
""", unsafe_allow_html=True)

# Control de acceso (contraseña compartida configurada en Secrets)
requiere_login()


# --------------------------------------------------------------------------- #
#  Estado
# --------------------------------------------------------------------------- #
if "calc_id" not in st.session_state:
    st.session_state.calc_id = None

CALCS = {c.id: c for c in cargar_calculadoras()}


def ir_a(calc_id):
    st.session_state.calc_id = calc_id


# --------------------------------------------------------------------------- #
#  Barra lateral
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.title("🏗️ Suite de Ingeniería")
    st.caption("Cálculos estructurales y de fundaciones")
    st.divider()
    if st.button("🏠  Inicio", use_container_width=True):
        ir_a(None)
    for categoria, calcs in por_categoria().items():
        st.markdown(f"**{categoria}**")
        for c in calcs:
            if st.button(f"{c.icono}  {c.nombre}", key=f"nav_{c.id}",
                         use_container_width=True):
                ir_a(c.id)
    st.divider()
    st.caption(f"{len(CALCS)} calculadora(s) disponibles")


# --------------------------------------------------------------------------- #
#  Vista: Inicio
# --------------------------------------------------------------------------- #
def vista_inicio():
    st.title("Suite de Ingeniería")
    st.write("Selecciona una calculadora para comenzar. "
             "Cada una genera resultados verificados y una memoria de cálculo en PDF.")
    st.write("")
    for categoria, calcs in por_categoria().items():
        st.subheader(categoria)
        cols = st.columns(3)
        for i, c in enumerate(calcs):
            with cols[i % 3]:
                st.markdown(
                    f"<div class='tarjeta'><h4>{c.icono} {c.nombre}</h4>"
                    f"<p style='color:#5b6b7b;font-size:0.9rem'>{c.descripcion}</p></div>",
                    unsafe_allow_html=True)
                st.button("Abrir  →", key=f"open_{c.id}",
                          on_click=ir_a, args=(c.id,), use_container_width=True)


# --------------------------------------------------------------------------- #
#  Vista: Calculadora
# --------------------------------------------------------------------------- #
def _init_estado(campo, calc_id):
    """Inicializa el valor del campo en session_state una sola vez."""
    kkey = f"in_{calc_id}_{campo.clave}"
    if kkey not in st.session_state:
        st.session_state[kkey] = (int(campo.defecto) if campo.tipo == "entero"
                                  else campo.defecto if campo.tipo == "opcion"
                                  else float(campo.defecto))


def _widget(campo, calc_id):
    etiqueta = f"{campo.etiqueta}" + (f"  [{campo.unidad}]" if campo.unidad else "")
    kkey = f"in_{calc_id}_{campo.clave}"
    comun = dict(help=campo.ayuda or None, key=kkey)
    if campo.tipo == "opcion":
        return st.selectbox(etiqueta, campo.opciones, **comun)
    if campo.tipo == "entero":
        return st.number_input(etiqueta,
                               min_value=int(campo.minimo) if campo.minimo is not None else None,
                               max_value=int(campo.maximo) if campo.maximo is not None else None,
                               step=int(campo.paso) if campo.paso else 1, **comun)
    return st.number_input(
        etiqueta,
        min_value=float(campo.minimo) if campo.minimo is not None else None,
        max_value=float(campo.maximo) if campo.maximo is not None else None,
        step=float(campo.paso) if campo.paso else None,
        format="%g", **comun)


def _aplicar_suelo(calc: Calculadora):
    """Callback: al elegir un material, escribe el σadm sugerido en su campo."""
    mat = st.session_state.get(f"suelo_{calc.id}")
    destino = getattr(calc, "guia_suelo_destino", "")
    if mat and mat in calc.guia_suelo and destino:
        st.session_state[f"in_{calc.id}_{destino}"] = float(calc.guia_suelo[mat])


def _entradas_actuales(calc: Calculadora) -> dict:
    return {c.clave: st.session_state.get(f"in_{calc.id}_{c.clave}", c.defecto) for c in calc.campos}


def _aplicar_sugerencia(calc: Calculadora):
    """Callback: escribe en los campos los valores sugeridos que cumplen."""
    limites = {c.clave: (c.minimo, c.maximo) for c in calc.campos}
    sug = calc.sugerir(_entradas_actuales(calc))
    for k, v in sug.items():
        lo, hi = limites.get(k, (None, None))
        if lo is not None:
            v = max(v, lo)
        if hi is not None:
            v = min(v, hi)
        st.session_state[f"in_{calc.id}_{k}"] = v


def vista_calculadora(calc: Calculadora):
    st.title(f"{calc.icono}  {calc.nombre}")
    st.caption(calc.descripcion)
    if calc.referencia:
        st.caption(f"📖 {calc.referencia}")

    izq, der = st.columns([1, 1.15], gap="large")

    # ---- Formulario (izquierda) ----
    with izq:
        st.subheader("Datos de entrada")

        for c in calc.campos:          # asegura valores en session_state
            _init_estado(c, calc.id)

        # Guia rapida de suelo (si la calculadora la declara): auto-rellena el campo
        if getattr(calc, "guia_suelo", None):
            with st.container(border=True):
                st.markdown("🧭 **Referencia rápida de suelo**")
                mat = st.selectbox("Tipo de material",
                                   ["— elegir —"] + list(calc.guia_suelo.keys()),
                                   key=f"suelo_{calc.id}",
                                   on_change=_aplicar_suelo, args=(calc,))
                if mat != "— elegir —":
                    st.caption(f"σadm de **{mat}** ≈ {calc.guia_suelo[mat]} kg/cm² "
                               f"— cargado abajo. Puedes cambiarlo a mano si lo necesitas.")

        grupos: dict[str, list] = {}
        for c in calc.campos:
            grupos.setdefault(c.grupo, []).append(c)

        entradas = {}
        for grupo, campos in grupos.items():
            normales = [c for c in campos if not c.avanzado]
            avanzados = [c for c in campos if c.avanzado]
            if normales:
                st.markdown(f"**{grupo}**")
                cc = st.columns(2)
                for i, campo in enumerate(normales):
                    with cc[i % 2]:
                        entradas[campo.clave] = _widget(campo, calc.id)
            if avanzados:
                with st.expander(f"⚙️ {grupo} (avanzado)"):
                    cc = st.columns(2)
                    for i, campo in enumerate(avanzados):
                        with cc[i % 2]:
                            entradas[campo.clave] = _widget(campo, calc.id)

        # Dimensionamiento asistido: al final, cuando ya estan todos los datos
        if getattr(calc, "sugerir", None):
            st.markdown("")
            with st.container(border=True):
                st.markdown("🎯 **Dimensionamiento asistido**")
                try:
                    sug = calc.sugerir(entradas)
                    partes = []
                    if "B_adop" in sug: partes.append(f"B = {sug['B_adop']:.2f} m")
                    if "d_adop" in sug: partes.append(f"d = {sug['d_adop']:.0f} cm")
                    if "gamma_asumido" in sug: partes.append(f"γ = {sug['gamma_asumido']:.2f}")
                    if "b_ped" in sug: partes.append(f"pedestal b = {sug['b_ped']:.0f} cm")
                    st.caption("Con los datos actuales, cumple con: " + " · ".join(partes))
                    st.button("Usar valores sugeridos", key=f"sug_{calc.id}",
                              on_click=_aplicar_sugerencia, args=(calc,),
                              use_container_width=True)
                    st.caption("Se cargan en los campos de arriba; luego puedes ajustarlos a mano.")
                except Exception:  # noqa
                    st.caption("(No disponible con los datos actuales.)")

    # ---- Resultados (derecha) ----
    with der:
        st.subheader("Resultados")
        try:
            res: Resultado = calc.funcion(entradas)
        except Exception as ex:  # noqa
            st.error(f"No se pudo calcular: {ex}")
            return

        # Diseno adoptado destacado (compacto)
        if res.resumen:
            tarjetas = "".join(
                f"<div style='flex:1;min-width:0;background:#fff;border:1px solid #e2e8f0;"
                f"border-radius:10px;padding:8px 12px;'>"
                f"<div style='font-size:11px;color:#5b6b7b;white-space:nowrap;'>{v.etiqueta}</div>"
                f"<div style='font-size:17px;font-weight:600;color:#1f3a5f;'>"
                f"{v.valor:,.{v.decimales}f} <span style='font-size:11px;color:#5b6b7b;'>{v.unidad}</span></div>"
                f"</div>"
                for v in res.resumen)
            st.markdown(f"<div style='display:flex;gap:8px;margin-bottom:10px;'>{tarjetas}</div>",
                        unsafe_allow_html=True)

        # Armado sugerido (destacado)
        if getattr(res, "armado_texto", ""):
            st.markdown(
                f"<div style='background:#fbf0ea;border:1px solid #e6c3b0;border-radius:10px;"
                f"padding:8px 12px;margin-bottom:10px;'>"
                f"<span style='font-size:11px;color:#5b6b7b;'>Armado sugerido (a/s)</span><br>"
                f"<span style='font-size:17px;font-weight:600;color:#c0562b;'>🔩 {res.armado_texto}</span>"
                f"</div>", unsafe_allow_html=True)

        # Veredicto
        if res.conforme:
            st.success("✅ Todas las verificaciones cumplen.")
        else:
            st.error("⚠️ Alguna verificación no cumple — revisar dimensiones.")

        # Verificaciones
        with st.container(border=True):
            st.markdown("**Verificaciones**")
            for c in res.chequeos:
                chip = ("<span class='chip-ok'>CUMPLE</span>" if c.cumple
                        else "<span class='chip-no'>NO CUMPLE</span>")
                st.markdown(
                    f"{chip} &nbsp; **{c.nombre}**: "
                    f"{c.izquierda} {c.relacion} {c.derecha}",
                    unsafe_allow_html=True)
                if c.comentario:
                    st.caption(c.comentario)

        # Tabla de valores
        with st.expander("📊 Ver todos los valores calculados", expanded=False):
            st.dataframe(
                [{"Variable": v.etiqueta, "Fórmula": v.formula,
                  "Valor": round(v.valor, v.decimales), "Unidad": v.unidad}
                 for v in res.valores],
                use_container_width=True, hide_index=True)

        for n in res.notas:
            st.info(n)

    # ---- Esquema (dibujo) ----
    if getattr(calc, "esquema", None):
        st.divider()
        st.subheader("📐 Esquema")
        try:
            vistas = calc.esquema(entradas, res)
            vcols = st.columns(len(vistas))
            for col, e in zip(vcols, vistas):
                with col:
                    st.caption(e["titulo"])
                    st.markdown(primitivas_a_svg(e), unsafe_allow_html=True)
        except Exception as ex:  # noqa
            st.caption(f"(No se pudo dibujar el esquema: {ex})")

    # ---- Tablas de referencia ----
    if getattr(calc, "tablas_referencia", None):
        st.divider()
        st.subheader("📋 Tablas de referencia")
        cols = st.columns(len(calc.tablas_referencia))
        for col, tabla in zip(cols, calc.tablas_referencia):
            with col:
                with st.expander(tabla["titulo"], expanded=False):
                    if tabla.get("nota"):
                        st.caption(tabla["nota"])
                    filas = [dict(zip(tabla["columnas"], f)) for f in tabla["filas"]]
                    st.dataframe(filas, use_container_width=True, hide_index=True)

    # ---- Exportar memoria ----
    st.divider()
    st.subheader("📄 Exportar memoria de cálculo")
    m1, m2, m3 = st.columns(3)
    proyecto = m1.text_input("Proyecto")
    elemento = m2.text_input("Elemento / eje")
    autor = m3.text_input("Calculó")
    pdf = generar_pdf(calc, entradas, res, proyecto, elemento, autor)
    st.download_button("⬇️  Descargar PDF", data=pdf,
                       file_name=f"memoria_{calc.id}.pdf", mime="application/pdf",
                       use_container_width=True)


# --------------------------------------------------------------------------- #
#  Enrutado
# --------------------------------------------------------------------------- #
if st.session_state.calc_id and st.session_state.calc_id in CALCS:
    vista_calculadora(CALCS[st.session_state.calc_id])
else:
    vista_inicio()
