import base64
import hashlib
import json
import os
import time
from datetime import date
import urllib.request
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

DATA_FILE = "neurofocus_data.json"

st.set_page_config(
    page_title="NEUROFOCUS | Sistema de Rendimiento",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ESTILOS CSS (DEEP FOCUS UI) ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    div[data-testid="stMetric"] {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px;
    }
    div[data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-weight: 700;
    }
    .stButton>button {
        border-radius: 6px;
        background-color: #238636;
        color: #ffffff;
        border: 1px solid rgba(240,246,252,0.1);
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #2ea043;
    }
    .badge-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-left: 4px solid #238636;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .badge-card.locked {
        border-left: 4px solid #484f58;
        opacity: 0.5;
    }
    .badge-title {
        font-weight: 700;
        color: #f0f6fc;
        font-size: 14px;
    }
    .badge-desc {
        font-size: 12px;
        color: #8b949e;
        margin-top: 2px;
    }
    .state-label {
        font-size: 13px;
        font-weight: 600;
        color: #58a6ff;
        margin-top: -10px;
        margin-bottom: 15px;
    }
    .admin-badge {
        background: #a371f7;
        color: #ffffff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
    }
    .protocol-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 15px;
    }
    .user-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .review-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 10px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest() if password else ""


# --- BASE DE DATOS ---
def cargar_base_datos():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "usuarios" not in data:
                        return {
                            "usuarios": {"default": data},
                            "usuario_actual": "default",
                            "sesion_persistente": False,
                            "valoraciones": [],
                        }
                    if "valoraciones" not in data:
                        data["valoraciones"] = []
                    return data
        except Exception:
            pass
    return {
        "usuarios": {},
        "usuario_actual": "",
        "sesion_persistente": False,
        "valoraciones": [],
    }


def guardar_base_datos(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


db = cargar_base_datos()


# --- CÁLCULO DE INSIGNIAS ---
def calcular_insignias(sesiones, racha):
    horas_totales = sum(s.get("duracion", 0) for s in sesiones) / 60.0
    num_sesiones = len(sesiones)

    insignias = [
        {
            "id": "b1",
            "nombre": "Primera Sesión",
            "requisito": "Completa tu primer bloque de trabajo",
            "desbloqueada": num_sesiones >= 1,
            "progreso": min(1.0, num_sesiones / 1),
            "tag": "[INICIO]",
        },
        {
            "id": "b2",
            "nombre": "Constancia (3 Días)",
            "requisito": "Mantén una racha de 3 días seguidos",
            "desbloqueada": racha >= 3,
            "progreso": min(1.0, racha / 3),
            "tag": "[3 DÍAS]",
        },
        {
            "id": "b3",
            "nombre": "10 Horas Enfocado",
            "requisito": "Acumula 10 horas totales de trabajo",
            "desbloqueada": horas_totales >= 10,
            "progreso": min(1.0, horas_totales / 10),
            "tag": "[10H]",
        },
        {
            "id": "b4",
            "nombre": "Dominio Total (50 Horas)",
            "requisito": "Acumula 50 horas totales de trabajo",
            "desbloqueada": horas_totales >= 50,
            "progreso": min(1.0, horas_totales / 50),
            "tag": "[50H]",
        },
    ]
    return insignias, horas_totales, num_sesiones


# --- SINCRONIZACIÓN NOTION ---
def sincronizar_con_notion(token, db_id, tarea, categoria, duracion):
    if not token or not db_id:
        return False
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Tarea": {"title": [{"text": {"content": str(tarea)}}]},
            "Categoría": {
                "rich_text": [{"text": {"content": str(categoria)}}]
            },
            "Duración": {"number": float(duracion)},
            "Fecha": {"date": {"start": str(date.today())}},
        },
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200
    except Exception:
        return False


# --- GESTIÓN DE SESIÓN PERSISTENTE ---
if "autenticado" not in st.session_state:
    if db.get("sesion_persistente", False) and db.get("usuario_actual") in db.get(
        "usuarios", {}
    ):
        st.session_state.autenticado = True
    else:
        st.session_state.autenticado = False

usuario_actual = db.get("usuario_actual", "")

# --- LOGIN Y REGISTRO ---
if not st.session_state.autenticado:
    st.title("NEUROFOCUS // ACCESO")
    tab_login, tab_registro = st.tabs(["Iniciar Sesión", "Registrar Usuario"])

    with tab_login:
        u_login = st.text_input("Usuario:", key="l_user")
        p_login = st.text_input("Contraseña:", type="password", key="l_pass")
        recordar = st.checkbox("Mantener sesión abierta siempre", value=True)

        if st.button("ENTRAR"):
            if u_login in db["usuarios"]:
                user_rec = db["usuarios"][u_login]
                if user_rec.get("password") == hash_password(p_login):
                    st.session_state.autenticado = True
                    db["usuario_actual"] = u_login
                    db["sesion_persistente"] = recordar
                    guardar_base_datos(db)
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
            else:
                st.error("El usuario no existe.")

    with tab_registro:
        u_reg = st.text_input("Nuevo Usuario:", key="r_user")
        p_reg = st.text_input("Crear Contraseña:", type="password", key="r_pass")
        recordar_reg = st.checkbox(
            "Mantener sesión abierta tras registro", value=True
        )

        if st.button("CREAR CUENTA"):
            if u_reg.strip() and u_reg not in db["usuarios"]:
                es_primer_user = len(db["usuarios"]) == 0
                db["usuarios"][u_reg] = {
                    "password": hash_password(p_reg),
                    "es_admin": es_primer_user,
                    "avatar": "",
                    "onboarding_completado": False,
                    "perfil": {},
                    "sesiones": [],
                    "racha": 0,
                    "ultima_fecha": "",
                    "notion_token": "",
                    "notion_db_id": "",
                    "notas_diarias": "",
                }
                db["usuario_actual"] = u_reg
                db["sesion_persistente"] = recordar_reg
                st.session_state.autenticado = True
                guardar_base_datos(db)
                st.success("Cuenta creada con éxito.")
                st.rerun()
            else:
                st.error("Nombre de usuario no disponible.")

else:
    # --- USUARIO CONECTADO ---
    datos_user = db["usuarios"][usuario_actual]

    # --- PANTALLA DE CONFIGURACIÓN INICIAL (ONBOARDING) ---
    if not datos_user.get("onboarding_completado", False):
        st.title("NEUROFOCUS // PREPARACIÓN DIARIA")
        st.markdown(
            "Ajusta tus parámetros para calcular los tiempos recomendados de trabajo."
        )
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            sueño = st.select_slider(
                "¿Cuántas horas has dormido?",
                options=[
                    "Menos de 5h",
                    "Entre 5h y 6h",
                    "Entre 7h y 8h",
                    "Más de 8h",
                ],
                value="Entre 7h y 8h",
            )
            distracciones = st.multiselect(
                "¿Qué te suele distraer más hoy?",
                [
                    "Móvil y redes sociales",
                    "Navegar por internet",
                    "Cansancio mental",
                    "Falta de organización",
                ],
                default=["Móvil y redes sociales"],
            )

        with col2:
            val_estres = st.slider("Nivel de estrés o saturación (1-5)", 1, 5, 2)
            lbl_estres = {
                1: "Muy bajo - Totalmente descansado",
                2: "Normal - Nivel adecuado para trabajar",
                3: "Moderado - Cierta presión mental",
                4: "Alto - Cansancio notable",
                5: "Muy alto - Necesita pausas frecuentes",
            }
            st.markdown(
                f'<div class="state-label">Estado: {lbl_estres[val_estres]}</div>',
                unsafe_allow_html=True,
            )

            meta_diaria = st.number_input(
                "Objetivo de trabajo para hoy (Horas)",
                min_value=0.5,
                max_value=12.0,
                value=4.0,
                step=0.5,
            )

        st.markdown("---")
        if st.button("GUARDAR Y EMPEZAR"):
            datos_user["onboarding_completado"] = True
            datos_user["perfil"] = {
                "sueño": sueño,
                "distracciones": distracciones,
                "estres": val_estres,
                "meta_diaria": meta_diaria,
            }
            guardar_base_datos(db)
            st.rerun()

    else:
        # --- MENÚ LATERAL ---
        st.sidebar.title("NEUROFOCUS")

        if datos_user.get("avatar"):
            st.sidebar.image(datos_user["avatar"], width=80)

        st.sidebar.caption(f"Usuario: {usuario_actual}")
        if datos_user.get("es_admin"):
            st.sidebar.markdown(
                '<span class="admin-badge">ADMINISTRADOR</span>',
                unsafe_allow_html=True,
            )

        sesiones_s = datos_user.get("sesiones", [])
        racha_s = datos_user.get("racha", 0)
        insignias_s, _, _ = calcular_insignias(sesiones_s, racha_s)
        unlocked_tags = " ".join(
            [b["tag"] for b in insignias_s if b["desbloqueada"]]
        )
        if unlocked_tags:
            st.sidebar.caption(f"Insignias: {unlocked_tags}")

        st.sidebar.metric(label="Racha Actual", value=f"{racha_s} Días")

        # --- SECCIÓN DE MÚSICA RESTAURADA (SIN LO-FI) ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("AUDIO PARA ENFOQUE")
        opciones_audio = {
            "Ruido Marrón (Aislamiento Total)": "https://www.youtube.com/embed/RqzGzwTY-6w?autoplay=0",
            "Sonido Blanco (Bloqueo de Ruido)": "https://www.youtube.com/embed/nMfPqeZjc2c?autoplay=0",
            "Ondas Alfa (Enfoque Profundo)": "https://www.youtube.com/embed/WPni755-Krg?autoplay=0",
            "Synthwave Focus (Instrumental Sostenido)": "https://www.youtube.com/embed/4xDzrJKXOOY?autoplay=0",
        }
        seleccion_audio = st.sidebar.selectbox(
            "Pista de Fondo", list(opciones_audio.keys())
        )
        url_embed = opciones_audio[seleccion_audio]

        components.html(
            f'<iframe width="100%" height="160" src="{url_embed}" title="YouTube audio player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>',
            height=170,
        )

        st.sidebar.markdown("---")
        opcion = st.sidebar.radio(
            "MENÚ PRINCIPAL",
            [
                "Ejecución de Bloque",
                "Métricas y Logros",
                "Comunidad / Perfiles",
                "Feedback & Valoraciones",
                "Protocolos de Enfoque",
                "Configuración & Cuentas",
            ],
        )

        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            db["sesion_persistente"] = False
            guardar_base_datos(db)
            st.rerun()

        perfil = datos_user.get("perfil", {})

        # --- PESTAÑA 1: EJECUCIÓN DE BLOQUE ---
        if opcion == "Ejecución de Bloque":
            st.title("MÓDULO DE TRABAJO PROFUNDO")

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                cat_tarea = st.selectbox(
                    "Categoría",
                    [
                        "Estudio",
                        "Programación / Código",
                        "Música / Producción",
                        "Lectura / Investigación",
                        "Otra Tarea",
                    ],
                )
            with col_t2:
                detalle_tarea = st.text_input(
                    "Nombre o detalle de la tarea:",
                    placeholder="Ej. Estudio Física / Producción Beat",
                )

            tarea_final = (
                f"{cat_tarea}: {detalle_tarea}" if detalle_tarea else cat_tarea
            )
            st.markdown("---")

            col_a, col_b = st.columns(2)
            with col_a:
                energia = st.slider("¿Cómo te sientes de energía? (1-5)", 1, 5, 3)
                lbl_energia = {
                    1: "Energía baja - Recomendado bloque de 15 min",
                    2: "Energía moderada - Recomendado bloque de 25 min",
                    3: "Energía normal - Recomendado bloque de 45 min",
                    4: "Energía alta - Recomendado bloque de 60 min",
                    5: "Energía máxima - Enfoque total (75-90 min)",
                }
                st.markdown(
                    f'<div class="state-label">{lbl_energia[energia]}</div>',
                    unsafe_allow_html=True,
                )

                factor = (
                    10
                    if (
                        "Menos de 5h" in perfil.get("sueño", "")
                        or perfil.get("estres", 1) >= 4
                    )
                    else 15
                )
                tiempo_rec = energia * factor

            with col_b:
                duracion = st.number_input(
                    "Tiempo de la sesión (Minutos)",
                    min_value=1,
                    max_value=180,
                    value=int(tiempo_rec),
                )

            st.markdown("---")

            if "ejecutando" not in st.session_state:
                st.session_state.ejecutando = False
            if "pausado" not in st.session_state:
                st.session_state.pausado = False
            if "confirmar_abortar" not in st.session_state:
                st.session_state.confirmar_abortar = False

            if not st.session_state.ejecutando:
                if st.button("COMENZAR SESIÓN", type="primary"):
                    st.session_state.ejecutando = True
                    st.session_state.pausado = False
                    st.session_state.tiempo_restante = int(duracion * 60)
                    st.session_state.confirmar_abortar = False
                    st.rerun()
            else:
                st.subheader(f"EN CURSO: {tarea_final.upper()}")
                clock_placeholder = st.empty()

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.session_state.pausado:
                        if st.button("REANUDAR"):
                            st.session_state.pausado = False
                            st.rerun()
                    else:
                        if st.button("PAUSAR"):
                            st.session_state.pausado = True
                            st.rerun()

                with col_btn2:
                    if not st.session_state.confirmar_abortar:
                        if st.button("CANCELAR SESIÓN"):
                            st.session_state.confirmar_abortar = True
                            st.rerun()
                    else:
                        st.warning("¿Quieres cancelar la sesión actual?")
                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            if st.button("Sí, Cancelar"):
                                st.session_state.ejecutando = False
                                st.session_state.pausado = False
                                st.session_state.confirmar_abortar = False
                                st.rerun()
                        with col_c2:
                            if st.button("Continuar Trabajando"):
                                st.session_state.confirmar_abortar = False
                                st.rerun()

                while (
                    st.session_state.ejecutando
                    and not st.session_state.pausado
                    and not st.session_state.confirmar_abortar
                    and st.session_state.tiempo_restante > 0
                ):
                    minutos_r, segundos_r = divmod(
                        st.session_state.tiempo_restante, 60
                    )
                    clock_placeholder.markdown(
                        f"""
                        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 30px; text-align: center; margin: 20px 0;">
                            <h1 style="font-family: monospace; font-size: 90px; color: #58a6ff; margin: 0; letter-spacing: 4px;">
                                {minutos_r:02d}:{segundos_r:02d}
                            </h1>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    time.sleep(1)
                    st.session_state.tiempo_restante -= 1

                if (
                    st.session_state.ejecutando
                    and st.session_state.tiempo_restante <= 0
                ):
                    st.session_state.ejecutando = False
                    st.session_state.sesion_para_evaluar = {
                        "duracion": duracion,
                        "tarea": tarea_final,
                        "categoria": cat_tarea,
                    }
                    st.rerun()
                elif (
                    st.session_state.pausado
                    or st.session_state.confirmar_abortar
                ):
                    minutos_r, segundos_r = divmod(
                        st.session_state.tiempo_restante, 60
                    )
                    clock_placeholder.markdown(
                        f"""
                        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 30px; text-align: center; margin: 20px 0;">
                            <h1 style="font-family: monospace; font-size: 90px; color: #8b949e; margin: 0; letter-spacing: 4px;">
                                {minutos_r:02d}:{segundos_r:02d}
                            </h1>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            if "sesion_para_evaluar" in st.session_state:
                st.markdown("---")
                st.subheader("REGISTRO DE RESULTADOS")
                q1 = st.slider(
                    "¿Qué tan concentrado estuviste? (%)", 0, 100, 85
                )

                if st.button("GUARDAR EN EL HISTORIAL"):
                    info_s = st.session_state.sesion_para_evaluar
                    nueva = {
                        "fecha": str(date.today()),
                        "duracion": info_s["duracion"],
                        "tarea": info_s["tarea"],
                        "categoria": info_s["categoria"],
                        "eficiencia_pct": q1,
                    }
                    datos_user["sesiones"].append(nueva)

                    if datos_user.get("ultima_fecha") != str(date.today()):
                        datos_user["racha"] = datos_user.get("racha", 0) + 1
                        datos_user["ultima_fecha"] = str(date.today())

                    n_token = datos_user.get("notion_token", "")
                    n_db = datos_user.get("notion_db_id", "")
                    if n_token and n_db:
                        sincronizar_con_notion(
                            n_token,
                            n_db,
                            info_s["tarea"],
                            info_s["categoria"],
                            info_s["duracion"],
                        )

                    guardar_base_datos(db)
                    del st.session_state["sesion_para_evaluar"]
                    st.rerun()

        # --- PESTAÑA 2: MÉTRICAS Y LOGROS ---
        elif opcion == "Métricas y Logros":
            st.title("PANEL DE MÉTRICAS Y LOGROS")

            sesiones = datos_user.get("sesiones", [])
            racha = datos_user.get("racha", 0)
            insignias, horas_totales, num_sesiones = calcular_insignias(
                sesiones, racha
            )

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Horas Totales", f"{horas_totales:.1f} hrs")
            col_m2.metric("Sesiones Totales", num_sesiones)
            col_m3.metric("Racha Actual", f"{racha} días")

            st.markdown("---")
            st.subheader("INSIGNIAS Y RECOMPENSAS")

            col_b1, col_b2 = st.columns(2)
            for i, badge in enumerate(insignias):
                col_target = col_b1 if i % 2 == 0 else col_b2
                with col_target:
                    estado_class = "" if badge["desbloqueada"] else "locked"
                    texto_estado = (
                        "DESBLOQUEADA" if badge["desbloqueada"] else "BLOQUEADA"
                    )

                    st.markdown(
                        f"""
                        <div class="badge-card {estado_class}">
                            <div class="badge-title">{badge['nombre']} [{texto_estado}]</div>
                            <div class="badge-desc">{badge['requisito']}</div>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )
                    st.progress(badge["progreso"])

            st.markdown("---")
            st.subheader("PROGRESO POR DÍA")
            if sesiones:
                df = pd.DataFrame(sesiones)
                if "fecha" in df.columns and "duracion" in df.columns:
                    st.bar_chart(df.groupby("fecha")["duracion"].sum())
            else:
                st.info("Aún no tienes sesiones registradas.")

        # --- PESTAÑA 3: COMUNIDAD / PERFILES ---
        elif opcion == "Comunidad / Perfiles":
            st.title("EXPLORADOR DE PERFILES Y COMUNIDAD")
            st.caption("Consulta el rendimiento y estado de los usuarios.")

            lista_usuarios = list(db["usuarios"].keys())
            target_user = st.selectbox(
                "Selecciona un perfil para ver:",
                lista_usuarios,
                index=lista_usuarios.index(usuario_actual),
            )

            u_data = db["usuarios"][target_user]
            u_sesiones = u_data.get("sesiones", [])
            u_racha = u_data.get("racha", 0)
            u_insignias, u_horas, u_num = calcular_insignias(u_sesiones, u_racha)

            st.markdown("---")
            col_p1, col_p2 = st.columns([1, 2])

            with col_p1:
                st.markdown('<div class="user-card">', unsafe_allow_html=True)
                if u_data.get("avatar"):
                    st.image(u_data["avatar"], width=150)
                else:
                    st.markdown("### 👤 (Sin Foto)")
                st.markdown(f"### {target_user}")
                if u_data.get("es_admin"):
                    st.markdown(
                        '<span class="admin-badge">ADMINISTRADOR</span>',
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

            with col_p2:
                col_s1, col_s2, col_s3 = st.columns(3)
                col_s1.metric("Horas de Trabajo", f"{u_horas:.1f} hrs")
                col_s2.metric("Sesiones", u_num)
                col_s3.metric("Racha", f"{u_racha} días")

                st.markdown("#### Insignias Obtenidas")
                desbloqueadas = [b for b in u_insignias if b["desbloqueada"]]
                if desbloqueadas:
                    for b in desbloqueadas:
                        st.markdown(f"- **{b['nombre']}**: {b['requisito']}")
                else:
                    st.caption("Aún no ha desbloqueado insignias.")

        # --- PESTAÑA 4: FEEDBACK & VALORACIONES ---
        elif opcion == "Feedback & Valoraciones":
            st.title("CENTRO DE MEJORA Y VALORACIONES")

            tab_val, tab_libreta = st.tabs(
                ["Enviar Feedback / Reseña", "Mi Libreta de Anotaciones"]
            )

            with tab_val:
                st.subheader("Valora la Aplicación")
                puntuacion = st.slider(
                    "Puntuación (1 a 5 Estrellas)", 1, 5, 5
                )
                comentario = st.text_area(
                    "¿Qué te gusta o qué crees que deberíamos mejorar?",
                    placeholder="Escribe aquí tu opinión o reporte de fallos...",
                )

                if st.button("ENVIAR VALORACIÓN"):
                    if comentario.strip():
                        nueva_val = {
                            "usuario": usuario_actual,
                            "fecha": str(date.today()),
                            "puntuacion": puntuacion,
                            "comentario": comentario.strip(),
                        }
                        db["valoraciones"].append(nueva_val)
                        guardar_base_datos(db)
                        st.success(
                            "¡Gracias por tu opinión! Se ha registrado correctamente."
                        )
                        st.rerun()
                    else:
                        st.warning("Por favor, escribe un comentario breve.")

                if datos_user.get("es_admin"):
                    st.markdown("---")
                    st.subheader("PANEL DE REVISIÓN (SOLO ADMINISTRADOR)")
                    val_list = db.get("valoraciones", [])
                    if val_list:
                        for v in reversed(val_list):
                            estrellas = "⭐" * v.get("puntuacion", 5)
                            st.markdown(
                                f"""
                                <div class="review-box">
                                    <div style="font-weight:bold; color:#58a6ff;">{v.get('usuario')} - {estrellas} <span style="font-size:12px; color:#8b949e;">({v.get('fecha')})</span></div>
                                    <div style="margin-top:5px;">{v.get('comentario')}</div>
                                </div>
                            """,
                                unsafe_allow_html=True,
                            )
                    else:
                        st.info("Aún no hay valoraciones de usuarios.")

            with tab_libreta:
                st.subheader("Libreta Digital de Registro Diario")
                st.caption(
                    "Usa este espacio para volcar tus notas físicas, reflexiones o cosas que quieres programar mañana."
                )

                texto_notas = st.text_area(
                    "Mis notas de desarrollo y mejoras personales:",
                    value=datos_user.get("notas_diarias", ""),
                    height=250,
                )

                if st.button("GUARDAR MIS NOTAS"):
                    datos_user["notas_diarias"] = texto_notas
                    guardar_base_datos(db)
                    st.success("Notas guardadas correctamente.")

        # --- PESTAÑA 5: PROTOCOLOS DE ENFOQUE ---
        elif opcion == "Protocolos de Enfoque":
            st.title("GUÍA DE PROTOCOLOS Y HÁBITOS")

            st.markdown("### PROTOCOLOS PRINCIPALES (OBLIGATORIOS)")

            st.markdown(
                """
            <div class="protocol-box">
                <h4 style="color:#58a6ff; margin:0;">1. Regla de los 5 Minutos (Inicio Inmediato)</h4>
                <p>Si sientes pereza para empezar, comprométete a trabajar solo durante 5 minutos contados con el reloj. Una vez que superas la fricción inicial, el cerebro entra en flujo y resulta mucho más fácil continuar.</p>
            </div>
            
            <div class="protocol-box">
                <h4 style="color:#58a6ff; margin:0;">2. Aislamiento Físico del Teléfono</h4>
                <p>Pon el teléfono en otra habitación o fuera de tu vista directa. Mantenerlo en la misma mesa consume energía atencional dividida aunque esté con la pantalla hacia abajo.</p>
            </div>
            
            <div class="protocol-box">
                <h4 style="color:#58a6ff; margin:0;">3. Descanso Visual y Mental (Pausas Reales)</h4>
                <p>Al terminar un bloque de trabajo, descansa 5-10 minutos sin mirar pantallas. Camina, toma agua o simplemente mira a la distancia para permitir que la mente procese la información.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown("---")
            st.markdown("### PROTOCOLOS OPCIONALES")

            st.markdown(
                """
            <div class="protocol-box">
                <h4 style="color:#a371f7; margin:0;">Opcional 1: Técnica NSDR (Descanso Profundo)</h4>
                <p>Túmbate en un lugar cómodo durante 10-15 minutos cerrando los ojos y manteniendo la respiración lenta. Excelente para recuperar claridad cuando estás saturado a mitad del día.</p>
            </div>
            
            <div class="protocol-box">
                <h4 style="color:#a371f7; margin:0;">Opcional 2: Fijación Visual Previa</h4>
                <p>Antes de arrancar la sesión, fija la mirada en un solo punto de la pared o pantalla durante 30 segundos. Ayuda a activar la atención del cerebro antes de empezar la tarea.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown("---")
            st.markdown("### TIPS ADICIONALES Y ESTRATEGIAS PRÁCTICAS")
            st.markdown(
                """
            * **Luz Solar Matutina:** Sal a tomar la luz del sol durante 10-15 minutos nada más levantarte para regular tus niveles de energía y dormir mejor por la noche.
            * **Cafeína Estratégica:** Evita consumir café durante los primeros 60-90 minutos tras despertarte para evitar el bajón de energía de la tarde.
            * **Bloques Claros:** Define exactamente qué vas a hacer antes de activar el temporizador. La indecisión durante el bloque arruina la concentración.
            * **Bloqueadores de Apps:** Usa aplicaciones de bloqueo estricto (como Opal, One Sec o Cold Turkey en PC) durante bloques de estudio profundo.
            * **Ficción de Fricción:** Dificulta el acceso a distracciones (cierra sesión en redes sociales, elimina atajos del navegador, pon la pantalla en escala de grises).
            * **Temperatura del Entorno:** Trabajar en un espacio ligeramente fresco (19°C-21°C) mantiene la alerta mental mejor que los espacios calurosos que inducen somnolencia.
            * **Hidratación y Electrolitos:** Beber agua constante con una pizca de sal o electrolitos al despertar evita la fatiga cerebral prematura.
            * **REGLA DE ORO:** Si te distraes, no abandones la sesión. Solo nota la distracción, vuelve a la tarea y continúa. Entrenar el enfoque es un músculo.
            """
            )

        # --- PESTAÑA 6: CONFIGURACIÓN & CUENTAS ---
        elif opcion == "Configuración & Cuentas":
            st.title("CONFIGURACIÓN Y MI PERFIL")

            st.subheader("Cambiar Foto de Perfil")
            archivo_avatar = st.file_uploader(
                "Sube tu foto de perfil desde tus archivos (PNG o JPG)",
                type=["png", "jpg", "jpeg"],
            )
            if archivo_avatar is not None:
                bytes_img = archivo_avatar.getvalue()
                encoded_img = base64.b64encode(bytes_img).decode("utf-8")
                ext = archivo_avatar.name.split(".")[-1]
                mime_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"
                datos_user["avatar"] = f"data:{mime_type};base64,{encoded_img}"
                guardar_base_datos(db)
                st.success("¡Foto de perfil actualizada correctamente!")
                st.rerun()

            st.markdown("---")
            st.subheader("Conexión con Notion")
            notion_token = st.text_input(
                "Notion API Token (secret_...):",
                value=datos_user.get("notion_token", ""),
                type="password",
            )
            notion_db = st.text_input(
                "Notion Database ID:", value=datos_user.get("notion_db_id", "")
            )

            if st.button("Guardar Configuración de Notion"):
                datos_user["notion_token"] = notion_token.strip()
                datos_user["notion_db_id"] = notion_db.strip()
                guardar_base_datos(db)
                st.success("Configuración guardada.")

            # --- PANEL EXCLUSIVO DE ADMINISTRADOR ---
            if datos_user.get("es_admin"):
                st.markdown("---")
                st.subheader("PANEL DE ADMINISTRACIÓN Y BANEOS")
                st.write(
                    f"Usuarios registrados en el sistema: **{len(db['usuarios'])}**"
                )

                for u_name in list(db["usuarios"].keys()):
                    col_u1, col_u2, col_u3 = st.columns([2, 2, 1])
                    col_u1.write(f"**{u_name}**")
                    is_admin_flag = db["usuarios"][u_name].get(
                        "es_admin", False
                    )
                    col_u2.caption(
                        "Administrador" if is_admin_flag else "Usuario"
                    )

                    if u_name != usuario_actual:
                        if col_u3.button("BANEAR / BORRAR", key=f"ban_{u_name}"):
                            del db["usuarios"][u_name]
                            guardar_base_datos(db)
                            st.success(f"Cuenta de {u_name} eliminada.")
                            st.rerun()

            st.markdown("---")
            st.subheader("Borrar Datos de Cuenta")
            if "confirmar_borrado" not in st.session_state:
                st.session_state.confirmar_borrado = False

            if not st.session_state.confirmar_borrado:
                if st.button("Resetear mi Historial"):
                    st.session_state.confirmar_borrado = True
                    st.rerun()
            else:
                st.error("¿Seguro que deseas borrar todo tu historial?")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    if st.button("Sí, Resetear"):
                        datos_user["onboarding_completado"] = False
                        datos_user["perfil"] = {}
                        datos_user["sesiones"] = []
                        datos_user["racha"] = 0
                        datos_user["ultima_fecha"] = ""
                        datos_user["notion_token"] = ""
                        datos_user["notion_db_id"] = ""
                        guardar_base_datos(db)
                        st.session_state.confirmar_borrado = False
                        st.rerun()
                with col_d2:
                    if st.button("Cancelar"):
                        st.session_state.confirmar_borrado = False
                        st.rerun()
