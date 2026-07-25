"""
Control de acceso por contraseña compartida.

La contraseña se lee de los "Secrets" de Streamlit (no del codigo), con la clave
`app_password`. Si no hay ninguna configurada (por ejemplo al ejecutar localmente
sin secrets), el acceso queda abierto para no bloquear el desarrollo.

Configurar en Streamlit Cloud:  Manage app -> Settings -> Secrets:
    app_password = "TU_CLAVE"

Localmente (opcional), crear .streamlit/secrets.toml con la misma linea.
Ese archivo NO debe subirse al repositorio (esta en .gitignore).
"""
from __future__ import annotations

import streamlit as st


def requiere_login():
    # Obtener la contraseña esperada de los secrets
    try:
        esperada = str(st.secrets["app_password"])
    except Exception:
        return  # sin contraseña configurada -> acceso abierto (uso local)

    if st.session_state.get("auth_ok"):
        return

    # Pantalla de login (centrada)
    st.markdown(
        "<div style='max-width:380px;margin:10vh auto 0;'>", unsafe_allow_html=True)
    st.markdown("### 🏗️ Suite de Ingeniería")
    st.caption("Acceso restringido al equipo. Introduce la contraseña.")
    with st.form("login"):
        pw = st.text_input("Contraseña", type="password")
        entrar = st.form_submit_button("Entrar", use_container_width=True)
    if entrar:
        if pw == esperada:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()   # bloquea el resto de la app hasta autenticarse
