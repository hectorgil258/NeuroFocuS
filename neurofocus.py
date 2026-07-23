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
    page_title="NEUROFOCUS | High-Performance System",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- INYECCIÓN DE CSS: ESTÉTICA DARK PREMIUM / GLASSMORPHISM ---
st.markdown(
    """
    <style>
    /* Estilos Generales Dark Mode */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Tarjetas y Contenedores */
    div[data-testid="stMetric"] {
        background: rgba(22, 27, 34, 0.7);
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    
    div[data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-weight: 700;
    }
    
    /* Botones Pro */
    .stButton>button {
        border-radius: 6px;
        background-color: #238636;
        color: #ffffff;
        border: 1px solid rgba(240,246,252,0.1);
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        background-color: #2ea043;
        border-color: #8b949e;
        transform: translateY(-1px);
    }
    
    /* Tarjetas de Insignias */
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
        letter-spacing: 0.5px;
    }
    
    .badge-desc {
        font-size: 12px;
        color: #8b949e;
        margin-top: 2px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# --- GESTIÓN DE BASE DE DATOS LOCAL Y MIGRACIÓN AUTOMÁTICA ---
def cargar_base_datos():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Migración automática si el archivo venía de la versión antigua
                    if "usuarios" not in data:
                        return {
                            "usuarios": {
                                "default": data
                            },
                            "usuario_actual": "default"
                        }
                    return data
        except Exception:
            pass
    return {"usuarios": {}, "usuario_actual": "default"}


def guardar_base_datos(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


db = cargar_base_datos()

# Selector / Creador de Usuario
usuario_actual = db.get("usuario_actual", "default")
if "usuarios" not in db:
    db["usuarios"] = {}

if usuario_actual not in db["usuarios"]:
    db["usuarios"][usuario_actual] = {
        "onboarding_completado": False,
        "perfil": {},
        "sesiones": [],
        "racha": 0,
        "ultima_fecha": "",
        "notion_token": "",
        "notion_db_id": "",
    }
    guardar_base_datos(db)

datos_user = db["usuarios"][usuario_actual]


# --- CONEXIÓN CON NOTION API ---
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


# --- SISTEMA DE LOGROS E INSIGNIAS ---
def calcular_insignias(sesiones, racha):
    horas_totales = sum(s.get("duracion", 0) for s in sesiones) / 60.0
    num_sesiones = len(sesiones)

    insignias = [
        {
            "id": "b1",
            "nombre": "Iniciación al Flujo",
            "requisito": "Completa tu primera sesión de enfoque",
            "desbloqueada": num_sesiones >= 1,
            "progreso": min(1.0, num_sesiones / 1),
        },
        {
            "id": "b2",
            "nombre": "Consistencia de Hierro",
            "requisito": "Alcanza una racha de 3 días consecutivos",
            "desbloqueada": racha >= 3,
            "progreso": min(1.0, racha / 3),
        },
        {
            "id": "b3",
            "nombre": "Arquitecto Cognitivo",
            "requisito": "Acumula 10 horas de trabajo profundo",
            "desbloqueada": horas_totales >= 10,
            "progreso": min(1.0, horas_totales / 10),
        },
        {
            "id": "b4",
            "nombre": "Titán del Rendimiento",
            "requisito": "Acumula 50 horas de trabajo profundo",
            "desbloqueada": horas_totales >= 50,
            "progreso": min(1.0, horas_totales / 50),
        },
    ]
    return insignias, horas_totales, num_sesiones


# --- PANTALLA DE CALIBRACIÓN INICIAL ---
if not datos_user.get("onboarding_completado", False):
    st.title("NEUROFOCUS // CALIBRACIÓN DEL SISTEMA")
    st.markdown(
        "Ajuste los parámetros biomecánicos y cognitivos antes de iniciar operaciones."
    )
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        sueño = st.select_slider(
            "Descanso Circadiano (Últimas 24h)",
            options=[
                "< 5h (Déficit Severo)",
                "5-6h (Subóptimo)",
                "7-8h (Fisiológico)",
                "> 8h (Optimizado)",
            ],
            value="7-8h (Fisiológico)",
        )
        distracciones = st.multiselect(
            "Puntos de Fricción Operativa",
            [
                "Dispositivos móviles",
                "Navegación web no estructurada",
                "Saturación cognitiva",
                "Planificación vaga",
            ],
            default=["Dispositivos móviles"],
        )

    with col2:
        val_estres = st.slider("Carga de Estrés Actual (1-5)", 1, 5, 2)
        meta_diaria = st.number_input(
            "Objetivo de Trabajo Neto (Horas/Día)",
            min_value=0.5,
            max_value=12.0,
            value=4.0,
            step=0.5,
        )

    st.markdown("---")
    if st.button("INICIALIZAR PROTOCOLO"):
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
    # --- PANEL LATERAL DE NAVEGACIÓN ---
    st.sidebar.title("NEUROFOCUS")
    st.sidebar.caption(f"Usuario activo: {usuario_actual}")

    # Racha
    racha_val = datos_user.get("racha", 0)
    st.sidebar.metric(label="Racha Consecutiva", value=f"{racha_val} Días")

    st.sidebar.markdown("---")
    st.sidebar.subheader("AISLAMIENTO ACÚSTICO")

    # Mapeo de Playlists de Spotify por Temática
    opciones_audio = {
        "Enfoque Profundo (Alfa)": "https://open.spotify.com/embed/playlist/37i9dQZF1DWWQRwui0ExPn?utm_source=generator&theme=0",
        "Ruido Marrón (Aislamiento)": "https://open.spotify.com/embed/playlist/37i9dQZF1DX4a1R99S3M3z?utm_source=generator&theme=0",
        "Lógica / Matemáticas": "https://open.spotify.com/embed/playlist/37i9dQZF1DX8U239m92Anv?utm_source=generator&theme=0",
        "Lofi Focus": "https://open.spotify.com/embed/playlist/37i9dQZF1DX3qCx5ySpv1M?utm_source=generator&theme=0",
    }

    seleccion_audio = st.sidebar.selectbox(
        "Entorno Sonoro", list(opciones_audio.keys())
    )
    url_embed = opciones_audio[seleccion_audio]

    components.html(
        f'<iframe style="border-radius:8px" src="{url_embed}" width="100%" height="152" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>',
        height=160,
    )

    st.sidebar.markdown("---")
    opcion = st.sidebar.radio(
        "SISTEMA",
        [
            "Ejecución de Bloque",
            "Métricas & Logros",
            "Protocolos de Enfoque",
            "Configuración & Cuentas",
        ],
    )

    perfil = datos_user.get("perfil", {})

    # --- PESTAÑA 1: EJECUCIÓN DE BLOQUE ---
    if opcion == "Ejecución de Bloque":
        st.title("MÓDULO DE TRABAJO PROFUNDO")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            cat_tarea = st.selectbox(
                "Categoría Operativa",
                [
                    "Estudio Avanzado",
                    "Desarrollo / Código",
                    "Diseño & Producción",
                    "Análisis / Lectura",
                    "Otra Actividad",
                ],
            )
        with col_t2:
            detalle_tarea = st.text_input(
                "Especificación del Bloque:",
                placeholder="Ej. Física Tema 3 / Refactorización backend / Mezcla R&B",
            )

        tarea_final = (
            f"{cat_tarea}: {detalle_tarea}" if detalle_tarea else cat_tarea
        )
        st.markdown("---")

        factor_ajuste = (
            10
            if (
                "Déficit" in perfil.get("sueño", "")
                or perfil.get("estres", 1) >= 4
            )
            else 15
        )

        col_a, col_b = st.columns(2)
        with col_a:
            energia = st.slider("Nivel de Energía Fisiológica (1-5)", 1, 5, 3)
            tiempo_recomendado = energia * factor_ajuste

        with col_b:
            duracion = st.number_input(
                "Duración Programada (Minutos)",
                min_value=1,
                max_value=180,
                value=int(tiempo_recomendado),
            )

        st.markdown("---")

        if "ejecutando" not in st.session_state:
            st.session_state.ejecutando = False
        if "pausado" not in st.session_state:
            st.session_state.pausado = False
        if "confirmar_abortar" not in st.session_state:
            st.session_state.confirmar_abortar = False

        if not st.session_state.ejecutando:
            if st.button("INICIAR SESIÓN", type="primary"):
                st.session_state.ejecutando = True
                st.session_state.pausado = False
                st.session_state.tiempo_restante = int(duracion * 60)
                st.session_state.confirmar_abortar = False
                st.rerun()
        else:
            st.subheader(f"EJECUTANDO: {tarea_final.upper()}")

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
                    if st.button("CANCELAR BLOQUE"):
                        st.session_state.confirmar_abortar = True
                        st.rerun()
                else:
                    st.warning("¿Confirmar cancelación? Se perderá el registro.")
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        if st.button("Sí, Abortar"):
                            st.session_state.ejecutando = False
                            st.session_state.pausado = False
                            st.session_state.confirmar_abortar = False
                            st.rerun()
                    with col_c2:
                        if st.button("Volver al Bloque"):
                            st.session_state.confirmar_abortar = False
                            st.rerun()

            # Bucle suave para el temporizador
            while (
                st.session_state.ejecutando
                and not st.session_state.pausado
                and not st.session_state.confirmar_abortar
                and st.session_state.tiempo_restante > 0
            ):
                minutos_r, segundos_r = divmod(st.session_state.tiempo_restante, 60)
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
            elif st.session_state.pausado or st.session_state.confirmar_abortar:
                minutos_r, segundos_r = divmod(st.session_state.tiempo_restante, 60)
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

        # Evaluación Post-Sesión
        if "sesion_para_evaluar" in st.session_state:
            st.markdown("---")
            st.subheader("AUDITORÍA DE RENDIMIENTO")
            q1 = st.slider("Eficiencia Atencional Sostenida (%)", 0, 100, 85)

            if st.button("REGISTRAR Y SINCRONIZAR"):
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

                # Sincronización Automática con Notion
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
    elif opcion == "Métricas & Logros":
        st.title("PANEL DE LOGROS Y ANALÍTICA")

        sesiones = datos_user.get("sesiones", [])
        racha = datos_user.get("racha", 0)
        insignias, horas_totales, num_sesiones = calcular_insignias(
            sesiones, racha
        )

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Volumen Acumulado", f"{horas_totales:.1f} Hrs")
        col_m2.metric("Sesiones Completadas", num_sesiones)
        col_m3.metric("Racha Actual", f"{racha} Días")

        st.markdown("---")
        st.subheader("INSIGNIAS Y RECOMPENSAS DE SISTEMA")

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
                        <div class="badge-title">{badge['nombre'].upper()} [{texto_estado}]</div>
                        <div class="badge-desc">{badge['requisito']}</div>
                    </div>
                """,
                    unsafe_allow_html=True,
                )
                st.progress(badge["progreso"])

        st.markdown("---")
        st.subheader("EVOLUCIÓN TEMPORAL")
        if sesiones:
            df = pd.DataFrame(sesiones)
            if "fecha" in df.columns and "duracion" in df.columns:
                st.bar_chart(df.groupby("fecha")["duracion"].sum())
        else:
            st.info("Sin registros acumulados.")

    # --- PESTAÑA 3: PROTOCOLOS ---
    elif opcion == "Protocolos de Enfoque":
        st.title("FRAMEWORKS NEUROCIENTÍFICOS")

        st.markdown("### 01. PROTOCOLO NSDR")
        st.write(
            "Descanso profundo sin sueño de 10 a 20 minutos para restaurar el pool de dopamina estriatal tras bloques de esfuerzo continuo."
        )

        st.markdown("### 02. REGLA DEL UMBRAL LÍMBICO")
        st.write(
            "Establecer un compromiso estricto de solo 300 segundos de trabajo para anular la resistencia amygdalar inicial."
        )

        st.markdown("### 03. AISLAMIENTO PERIMETRAL")
        st.write(
            "Retirar dispositivos móviles del campo visual primario y secundario para eliminar el consumo atencional pasivo."
        )

        st.markdown("### 04. ANCLAJE FOVEAL PREVIO")
        st.write(
            "Fijar la mirada en un punto estático durante 30 segundos antes de comenzar para inducir activación simpática concentrada."
        )

    # --- PESTAÑA 4: CONFIGURACIÓN Y NOTION ---
    elif opcion == "Configuración & Cuentas":
        st.title("CONFIGURACIÓN DE USUARIO & INTEGRACIONES")

        st.subheader("Gestión de Usuario")
        nuevo_user = st.text_input(
            "Cambiar o Crear Nombre de Usuario:", value=usuario_actual
        )
        if st.button("Cargar / Crear Usuario"):
            if nuevo_user.strip():
                db["usuario_actual"] = nuevo_user.strip()
                guardar_base_datos(db)
                st.rerun()

        st.markdown("---")
        st.subheader("Integración con Notion API")
        st.caption("Sincroniza tus bloques automáticamente con tu base de datos de Notion.")

        notion_token = st.text_input(
            "Notion API Token (secret_...):",
            value=datos_user.get("notion_token", ""),
            type="password",
        )
        notion_db = st.text_input(
            "Notion Database ID:", value=datos_user.get("notion_db_id", "")
        )

        if st.button("Guardar Credenciales de Notion"):
            datos_user["notion_token"] = notion_token.strip()
            datos_user["notion_db_id"] = notion_db.strip()
            guardar_base_datos(db)
            st.success("Credenciales guardadas correctamente.")

        st.markdown("---")
        st.subheader("Zona de Seguridad")
        if "confirmar_borrado" not in st.session_state:
            st.session_state.confirmar_borrado = False

        if not st.session_state.confirmar_borrado:
            if st.button("RESETEAR DATOS DE CUENTA"):
                st.session_state.confirmar_borrado = True
                st.rerun()
        else:
            st.error(
                "¿ESTÁ SEGURO? Esta acción borrará permanentemente todo el historial del usuario actual."
            )
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                if st.button("Sí, Eliminar Todo"):
                    db["usuarios"][usuario_actual] = {
                        "onboarding_completado": False,
                        "perfil": {},
                        "sesiones": [],
                        "racha": 0,
                        "ultima_fecha": "",
                        "notion_token": "",
                        "notion_db_id": "",
                    }
                    guardar_base_datos(db)
                    st.session_state.confirmar_borrado = False
                    st.rerun()
            with col_d2:
                if st.button("Cancelar Borrado"):
                    st.session_state.confirmar_borrado = False
                    st.rerun()
                    
