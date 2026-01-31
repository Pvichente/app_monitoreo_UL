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

def load_google_sheet(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# --- 4. GESTIÓN DE MEMORIA Y RECUPERACIÓN (EL BLINDAJE) ---

# Función para guardar estado en la URL (La Caja Negra)
def sync_to_url():
    st.query_params["talk_acum"] = str(st.session_state.talk_time_accumulated)
    st.query_params["is_talking"] = "1" if st.session_state.is_talking else "0"
    if st.session_state.talk_time_start_marker:
        st.query_params["start_marker"] = str(st.session_state.talk_time_start_marker)

# Función para recuperar estado desde la URL (Resurrección)
def restore_from_url():
    params = st.query_params
    if "talk_acum" in params:
        st.session_state.talk_time_accumulated = float(params["talk_acum"])
    if "is_talking" in params and params["is_talking"] == "1":
        st.session_state.is_talking = True
        # Si estaba hablando y se recargó, recuperamos el marcador de inicio
        if "start_marker" in params:
            st.session_state.talk_time_start_marker = float(params["start_marker"])
        else:
            # Si falló algo, reiniciamos el marcador para no romper el cálculo
            st.session_state.talk_time_start_marker = time.time()

# Inicialización de variables
if 'init_done' not in st.session_state:
    restore_from_url() # ¡Aquí ocurre la magia al cargar!
    st.session_state.init_done = True

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'monitoring_active' not in st.session_state: st.session_state.monitoring_active = False
if 'talk_time_accumulated' not in st.session_state: st.session_state.talk_time_accumulated = 0
if 'talk_time_start_marker' not in st.session_state: st.session_state.talk_time_start_marker = None
if 'is_talking' not in st.session_state: st.session_state.is_talking = False
if 'start_session_time' not in st.session_state: st.session_state.start_session_time = None

# --- 5. COMPONENTE LATIDO (EVITA DESCONEXIÓN) ---
@st.fragment(run_every=20)
def keep_alive():
    # Mantiene el WebSocket activo
    st.sidebar.caption(f"🟢 En línea: {datetime.datetime.now().strftime('%H:%M:%S')}")

# Activamos el latido en toda la app
with st.sidebar:
    keep_alive()

# --- 6. COMPONENTE RELOJ EN VIVO ---
@st.fragment(run_every=1)
def live_clock_component():
    current_talk_session = 0
    if st.session_state.is_talking:
        current_talk_session = time.time() - st.session_state.talk_time_start_marker
    
    total_talk_display = st.session_state.talk_time_accumulated + current_talk_session
    
    mins, secs = divmod(int(total_talk_display), 60)
    timer_str = f"{mins:02d}:{secs:02d}"
    percentage = int((total_talk_display / (90 * 60)) * 100)
    
    st.metric("Acumulado (En vivo)", timer_str, f"{percentage}% (de 90m)")

# --- 7. GUARDADO LOCAL ---
def save_observation_locally(data_dict):
    file_path = "observaciones_consolidado.csv"
    new_row = pd.DataFrame([data_dict])
    if not os.path.exists(file_path):
        new_row.to_csv(file_path, index=False, encoding='utf-8-sig')
    else:
        new_row.to_csv(file_path, mode='a', header=False, index=False, encoding='utf-8-sig')

# --- PANTALLAS (Lógica Principal) ---

def login_screen():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🛡️ Monitor Blindado")
        with st.spinner("Conectando..."):
            df_users = load_google_sheet("Course Managers")
        
        if not df_users.empty and 'Nombre' in df_users.columns:
            lista_nombres = df_users['Nombre'].dropna().unique().tolist()
            selected_user = st.selectbox("Usuario", lista_nombres)
            password = st.text_input("Contraseña", type="password")
            
            if st.button("INGRESAR", type="primary"):
                try:
                    user_row = df_users[df_users['Nombre'] == selected_user].iloc[0]
                    if password.strip() == str(user_row['Contraseña']).strip():
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
    if df.empty: st.stop()

    col1, col2 = st.columns(2)
    with col1:
        trimestre = st.selectbox("Trimestre", sorted(df['Trimestre'].astype(str).unique()))
        df_t = df[df['Trimestre'] == trimestre]
        curso = st.selectbox("Curso", sorted(df_t['Curso'].unique()))
    with col2:
        df_c = df_t[df_t['Curso'] == curso]
        grupo = st.selectbox("Grupo", sorted(df_c['Grupo'].unique()))
        try:
            facilitador_nombre = df_c[df_c['Grupo'] == grupo].iloc[0]['Facilitador']
        except:
            facilitador_nombre = "No asignado"
        st.text_input("Facilitador", value=facilitador_nombre, disabled=True)
        sesion = st.selectbox("Sesión", range(1, 21))

    st.divider()
    if st.button("INICIAR OBSERVACIÓN 🚀", use_container_width=True, type="primary"):
        st.session_state.context = {"trimestre": trimestre, "curso": curso, "facilitador": facilitador_nombre, "grupo": grupo, "sesion": sesion}
        st.session_state.monitoring_active = True
        st.session_state.start_session_time = datetime.datetime.now()
        st.rerun()

def monitoring_dashboard():
    st.markdown("### 📡 Tablero de Monitoreo")
    col_left, col_center, col_right = st.columns([1, 2.5, 1.2])
    
    with col_left:
        st.info(f"**Manager:** {st.session_state.user_name}")
        ctx = st.session_state.context
        st.markdown(f"**Curso:** {ctx['curso']}\n**Prof:** {ctx['facilitador']}")
        
        # Reloj de sesión total (Fragmentado)
        @st.fragment(run_every=1)
        def session_clock():
            if st.session_state.start_session_time:
                elapsed = datetime.datetime.now() - st.session_state.start_session_time
                st.metric("Tiempo Sesión", str(elapsed).split('.')[0])
        session_clock()

        if st.button("Salir (Sin Guardar)"):
             st.query_params.clear() # Limpiamos URL
             st.session_state.clear()
             st.rerun()

    with col_center:
        st.markdown("#### 1. Tiempo de Habla")
        tt_col1, tt_col2 = st.columns([1, 1])
        with tt_col1:
            # BOTÓN INTELIGENTE: Guarda en URL cada vez que se toca
            btn_label = "🔴 PAUSAR" if st.session_state.is_talking else "🟢 ACTIVAR"
            if st.button(btn_label, type="primary" if st.session_state.is_talking else "secondary"):
                if not st.session_state.is_talking:
                    st.session_state.is_talking = True
                    st.session_state.talk_time_start_marker = time.time()
                else:
                    st.session_state.is_talking = False
                    st.session_state.talk_time_accumulated += (time.time() - st.session_state.talk_time_start_marker)
                
                # ¡AQUÍ ESTÁ EL TRUCO! Guardamos en URL al instante
                sync_to_url()
                st.rerun()
        
        with tt_col2:
            live_clock_component()

        st.divider()
        # Variables (Simplificadas para el ejemplo)
        st.markdown("#### 2. Variables")
        col_vars1, col_vars2 = st.columns(2)
        with col_vars1:
            inicio_puntual = st.radio("¿Puntual?", ["Sí", "No"], horizontal=True)
            prework = st.radio("¿Pre-work?", ["Sí", "No"], horizontal=True)
        with col_vars2:
            asistencia = st.number_input("Asistencia Total", 0, 100)

    with col_right:
        st.markdown("#### 📝 Bitácora")
        notas = st.text_area("Notas", height=350, help="Escribe aquí. Si recargas la página, este texto se perderá, ¡cuidado!")
        
        if st.button("💾 GUARDAR Y DESCARGAR", type="primary"):
            # Cálculo final
            final_talk = st.session_state.talk_time_accumulated
            if st.session_state.is_talking:
                final_talk += (time.time() - st.session_state.talk_time_start_marker)
            
            registro = {
                "Manager": st.session_state.user_name,
                "Fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Curso": st.session_state.context['curso'],
                "Talk_Time_Sec": int(final_talk),
                "Inicio_Puntual": inicio_puntual,
                "Prework": prework,
                "Asistencia": asistencia,
                "Notas": notas
            }
            
            save_observation_locally(registro)
            
            # Generar descarga
            with open("observaciones_consolidado.csv", "rb") as f:
                st.download_button("📥 DESCARGAR CSV AHORA", f, "observaciones.csv", "text/csv")
            
            st.success("¡Datos procesados! Descarga el archivo para terminar.")
            # Limpiamos URL para que la próxima vez empiece de 0
            st.query_params.clear()

# --- CONTROLADOR ---
if not st.session_state.logged_in:
    login_screen()
elif not st.session_state.monitoring_active:
    context_screen()
else:
    monitoring_dashboard()
