import streamlit as st
import pandas as pd
import datetime
import time
import os

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Monitor Blindado",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILOS VISUALES ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .metric-box { border: 1px solid #e0e0e0; padding: 10px; border-radius: 5px; background-color: #f9f9f9; text-align: center;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN A GOOGLE SHEETS ---
SHEET_ID = "17XScIYv_FzsYApoF30p6PPZm6moUqH6WLzD33cetPbs"

@st.cache_data(ttl=300, show_spinner=False)
def load_google_sheet(sheet_name: str) -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# --- 4. GESTIÓN DE MEMORIA Y RECUPERACIÓN (EL BLINDAJE) ---

def _get_qp_value(params, key, default=None):
    """st.query_params puede devolver str o list[str] según versión/config."""
    if key not in params:
        return default
    v = params[key]
    if isinstance(v, list):
        return v[0] if len(v) > 0 else default
    return v

def sync_to_url():
    st.query_params["talk_acum"] = str(st.session_state.talk_time_accumulated)
    st.query_params["is_talking"] = "1" if st.session_state.is_talking else "0"
    if st.session_state.talk_time_start_marker:
        st.query_params["start_marker"] = str(st.session_state.talk_time_start_marker)

def restore_from_url():
    params = st.query_params
    talk_acum = _get_qp_value(params, "talk_acum", None)
    is_talking = _get_qp_value(params, "is_talking", "0")
    start_marker = _get_qp_value(params, "start_marker", None)

    if talk_acum is not None:
        try:
            st.session_state.talk_time_accumulated = float(talk_acum)
        except:
            st.session_state.talk_time_accumulated = 0.0

    if is_talking == "1":
        st.session_state.is_talking = True
        if start_marker is not None:
            try:
                st.session_state.talk_time_start_marker = float(start_marker)
            except:
                st.session_state.talk_time_start_marker = time.time()
        else:
            st.session_state.talk_time_start_marker = time.time()

# Inicialización base
if "init_done" not in st.session_state:
    restore_from_url()
    st.session_state.init_done = True

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "monitoring_active" not in st.session_state: st.session_state.monitoring_active = False
if "talk_time_accumulated" not in st.session_state: st.session_state.talk_time_accumulated = 0.0
if "talk_time_start_marker" not in st.session_state: st.session_state.talk_time_start_marker = None
if "is_talking" not in st.session_state: st.session_state.is_talking = False
if "start_session_time" not in st.session_state: st.session_state.start_session_time = None
if "context" not in st.session_state: st.session_state.context = {}

# --- 5. COMPONENTE LATIDO ---
@st.fragment(run_every=20)
def keep_alive():
    st.caption(f"🟢 En línea: {datetime.datetime.now().strftime('%H:%M:%S')}")

with st.sidebar:
    keep_alive()

# --- 6. RELOJ EN VIVO (TALK TIME) ---
@st.fragment(run_every=1)
def live_clock_component():
    current_talk_session = 0
    if st.session_state.is_talking and st.session_state.talk_time_start_marker:
        current_talk_session = time.time() - st.session_state.talk_time_start_marker

    total_talk_display = st.session_state.talk_time_accumulated + current_talk_session
    mins, secs = divmod(int(total_talk_display), 60)
    timer_str = f"{mins:02d}:{secs:02d}"
    percentage = int((total_talk_display / (90 * 60)) * 100)
    percentage = max(0, min(percentage, 999))
    st.metric("Acumulado (En vivo)", timer_str, f"{percentage}% (de 90m)")

# --- 7. GUARDADO LOCAL ROBUSTO ---
def save_observation_locally(data_dict):
    file_path = "observaciones_consolidado.csv"
    new_row = pd.DataFrame([data_dict])

    if not os.path.exists(file_path):
        new_row.to_csv(file_path, index=False, encoding="utf-8-sig")
        return

    try:
        old = pd.read_csv(file_path, encoding="utf-8-sig")
    except:
        old = pd.read_csv(file_path)

    combined = pd.concat([old, new_row], ignore_index=True)
    combined.to_csv(file_path, index=False, encoding="utf-8-sig")

# --- PANTALLAS ---

def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🛡️ Monitor Blindado")
        with st.spinner("Conectando..."):
            df_users = load_google_sheet("Course Managers")

        if not df_users.empty and "Nombre" in df_users.columns:
            lista_nombres = df_users["Nombre"].dropna().unique().tolist()
            selected_user = st.selectbox("Usuario", lista_nombres, key="login_user")
            password = st.text_input("Contraseña", type="password", key="login_pass")

            if st.button("INGRESAR", type="primary"):
                try:
                    user_row = df_users[df_users["Nombre"] == selected_user].iloc[0]
                    if password.strip() == str(user_row["Contraseña"]).strip():
                        st.session_state.logged_in = True
                        st.session_state.user_name = selected_user
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta")
                except:
                    st.error("Error de validación")

def context_screen():
    st.title(f"Hola, {st.session_state.user_name} 👋")
    with st.spinner("Cargando cursos..."):
        df = load_google_sheet("Facilitadores")
    if df.empty:
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        trimestre = st.selectbox("Trimestre", sorted(df["Trimestre"].astype(str).unique()), key="ctx_trimestre")
        df_t = df[df["Trimestre"].astype(str) == str(trimestre)]
        curso = st.selectbox("Curso", sorted(df_t["Curso"].unique()), key="ctx_curso")

    with col2:
        df_c = df_t[df_t["Curso"] == curso]
        grupo = st.selectbox("Grupo", sorted(df_c["Grupo"].unique()), key="ctx_grupo")
        try:
            facilitador_nombre = df_c[df_c["Grupo"] == grupo].iloc[0]["Facilitador"]
        except:
            facilitador_nombre = "No asignado"
        st.text_input("Facilitador", value=facilitador_nombre, disabled=True)
        sesion = st.selectbox("Sesión", range(1, 21), key="ctx_sesion")

    st.divider()
    if st.button("INICIAR OBSERVACIÓN 🚀", use_container_width=True, type="primary"):
        st.session_state.context = {
            "trimestre": str(trimestre),
            "curso": curso,
            "facilitador": facilitador_nombre,
            "grupo": grupo,
            "sesion": int(sesion),
        }
        st.session_state.monitoring_active = True
        st.session_state.start_session_time = datetime.datetime.now()
        st.rerun()

def monitoring_dashboard():
    st.markdown("### 📡 Tablero de Monitoreo")
    col_left, col_center, col_right = st.columns([1, 2.5, 1.2])

    with col_left:
        st.info(f"**Manager:** {st.session_state.user_name}")
        ctx = st.session_state.context
        st.markdown(
            f"**Curso:** {ctx.get('curso','')}\n\n"
            f"**Prof:** {ctx.get('facilitador','')}\n\n"
            f"**Grupo:** {ctx.get('grupo','')}\n\n"
            f"**Sesión:** {ctx.get('sesion','')}"
        )

        @st.fragment(run_every=1)
        def session_clock():
            if st.session_state.start_session_time:
                elapsed = datetime.datetime.now() - st.session_state.start_session_time
                st.metric("Tiempo Sesión", str(elapsed).split(".")[0])

        session_clock()

        if st.button("Salir (Sin Guardar)"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

    with col_center:
        st.markdown("#### 1. Tiempo de Habla")
        tt_col1, tt_col2 = st.columns([1, 1])

        with tt_col1:
            btn_label = "🔴 PAUSAR" if st.session_state.is_talking else "🟢 ACTIVAR"
            if st.button(btn_label, type="primary" if st.session_state.is_talking else "secondary"):
                if not st.session_state.is_talking:
                    st.session_state.is_talking = True
                    st.session_state.talk_time_start_marker = time.time()
                else:
                    st.session_state.is_talking = False
                    if st.session_state.talk_time_start_marker:
                        st.session_state.talk_time_accumulated += (
                            time.time() - st.session_state.talk_time_start_marker
                        )
                        st.session_state.talk_time_start_marker = None

                sync_to_url()
                st.rerun()

        with tt_col2:
            live_clock_component()

        st.divider()

        st.markdown("#### 2. Variables")
        col_vars1, col_vars2 = st.columns(2)

        # IMPORTANTE:
        # - keys fijas para que NO se reinicien valores
        # - max_value estable (no depende de asistencia) para que NO se “bloquee” ni se resetee al cambiar asistencia
        with col_vars2:
            asistencia = st.number_input(
                "Asistencia Total",
                min_value=0,
                max_value=100,
                step=1,
                key="asistencia_total"
            )

            llegaron_antes_10 = st.number_input(
                "¿Cuántos estudiantes llegaron antes de los 10 minutos?",
                min_value=0,
                max_value=100,
                step=1,
                key="llegaron_antes_10"
            )

            llegaron_despues_10 = st.number_input(
                "¿Cuántos estudiantes llegaron después de los 10 minutos?",
                min_value=0,
                max_value=100,
                step=1,
                key="llegaron_despues_10"
            )

        with col_vars1:
            inicio_puntual = st.radio(
                "¿Puntual?",
                ["Sí", "No"],
                horizontal=True,
                key="inicio_puntual"
            )

            prework = st.radio(
                "¿Hubo Pre-work?",
                ["Sí", "No"],
                horizontal=True,
                key="hubo_prework"
            )

            # Mantener valor aunque cambie asistencia (por key fija)
            # Si no hubo prework, guardamos 0 (sin borrar estado a la mala)
            prework_count = int(st.session_state.get("prework_count", 0))

            if prework == "Sí":
                prework_count = st.number_input(
                    "¿Cuántos estudiantes hicieron Pre-work?",
                    min_value=0,
                    max_value=100,
                    step=1,
                    key="prework_count"
                )
            else:
                # Para consistencia de datos
                st.session_state["prework_count"] = 0
                prework_count = 0

        # Validación suave (no resetea inputs)
        a = int(asistencia)
        b = int(llegaron_antes_10)
        c = int(llegaron_despues_10)
        p = int(prework_count)

        if a > 0:
            if b > a:
                st.warning("⚠️ 'Llegaron antes de 10 min' es mayor que 'Asistencia Total'.")
            if c > a:
                st.warning("⚠️ 'Llegaron después de 10 min' es mayor que 'Asistencia Total'.")
            if (b + c) > a:
                st.warning("⚠️ La suma de 'antes' + 'después' excede la 'Asistencia Total'.")
            if prework == "Sí" and p > a:
                st.warning("⚠️ 'Hicieron Pre-work' es mayor que 'Asistencia Total'.")

    with col_right:
        st.markdown("#### 📝 Bitácora")
        notas = st.text_area(
            "Notas",
            height=350,
            help="Escribe aquí. Si recargas la página, este texto se perderá, ¡cuidado!"
        )

        if st.button("💾 GUARDAR Y DESCARGAR", type="primary"):
            # Bloqueo de guardado si hay inconsistencias duras (opcional pero recomendado)
            a = int(st.session_state.get("asistencia_total", 0))
            b = int(st.session_state.get("llegaron_antes_10", 0))
            c = int(st.session_state.get("llegaron_despues_10", 0))
            p = int(st.session_state.get("prework_count", 0))
            hubo_pre = st.session_state.get("hubo_prework", "No")

            errores = []
            if a > 0:
                if b > a: errores.append("• 'Llegaron antes de 10 min' > 'Asistencia Total'")
                if c > a: errores.append("• 'Llegaron después de 10 min' > 'Asistencia Total'")
                if (b + c) > a: errores.append("• 'Antes' + 'Después' > 'Asistencia Total'")
                if hubo_pre == "Sí" and p > a: errores.append("• 'Hicieron Pre-work' > 'Asistencia Total'")

            if errores:
                st.error("No se puede guardar. Corrige lo siguiente:\n" + "\n".join(errores))
                return

            # Cálculo final del talk time
            final_talk = st.session_state.talk_time_accumulated
            if st.session_state.is_talking and st.session_state.talk_time_start_marker:
                final_talk += (time.time() - st.session_state.talk_time_start_marker)

            ctx = st.session_state.context

            registro = {
                "Manager": st.session_state.user_name,
                "Fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Trimestre": ctx.get("trimestre", ""),
                "Curso": ctx.get("curso", ""),
                "Facilitador": ctx.get("facilitador", ""),
                "Grupo": ctx.get("grupo", ""),
                "Sesion": ctx.get("sesion", ""),
                "Talk_Time_Sec": int(final_talk),

                "Inicio_Puntual": st.session_state.get("inicio_puntual", ""),
                "Prework": st.session_state.get("hubo_prework", "No"),
                "Prework_Count": int(p) if st.session_state.get("hubo_prework", "No") == "Sí" else 0,

                "Asistencia": int(a),
                "Llegaron_Antes_10min": int(b),
                "Llegaron_Despues_10min": int(c),

                "Notas": notas,
            }

            save_observation_locally(registro)

            with open("observaciones_consolidado.csv", "rb") as f:
                st.download_button("📥 DESCARGAR CSV AHORA", f, "observaciones.csv", "text/csv")

            st.success("¡Datos procesados! Descarga el archivo para terminar.")
            st.query_params.clear()

# --- CONTROLADOR ---
if not st.session_state.logged_in:
    login_screen()
elif not st.session_state.monitoring_active:
    context_screen()
else:
    monitoring_dashboard()
