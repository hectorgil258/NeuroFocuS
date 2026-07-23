import json
import os
import time
from datetime import date
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

DATA_FILE = "neurofocus_data.json"

st.set_page_config(
    page_title="NeuroFocus | Rendimiento Cognitivo",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO MINIMALISTA PERSONALIZADO ---
st.markdown("""
    <style>
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    .metric-container {
        border-left: 3px solid #4CAF50;
        padding-left: 10px;
    }
    </style>
""", unsafe_allow_html=True)

def cargar_datos():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "onboarding_completado": False,
        "perfil": {},
        "sesiones": [],
        "racha": 0,
        "ultima_fecha": "",
    }

def guardar_datos(datos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

datos = cargar_datos()

# --- PANTALLA 1: CALIBRACIÓN INICIAL ---
if not datos["onboarding_completado"]:
    st.title("Calibración del Sistema")
    st.markdown("Defina los parámetros base para adaptar los ciclos de trabajo a su estado actual.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        sueño = st.select_slider(
            "Horas de descanso (Últimas 24h)",
            options=["< 5h (Crítico)", "5-6h (Déficit)", "7-8h (Óptimo)", "> 8h (Recuperación)"],
            value="7-8h (Óptimo)"
        )
        distracciones = st.multiselect(
            "Fricciones operativas habituales",
            ["Dispositivos móviles", "Navegación web no estructurada", "Fatiga cognitiva", "Falta de planificación previa"],
            default=["Dispositivos móviles"]
        )

    with col2:
        val_estres = st.slider("Carga cognitiva actual (1: Mínima - 5: Sobrecarga)", 1, 5, 2)
        meta_diaria = st.number_input("Objetivo de trabajo profundo (Horas netas)", min_value=0.5, max_value=10.0, value=3.0, step=0.5)

    st.markdown("---")
    if st.button("Inicializar Entorno"):
        datos["onboarding_completado"] = True
        datos["perfil"] = {
            "sueño": sueño,
            "distracciones": distracciones,
            "estres": val_estres,
            "meta_diaria": meta_diaria,
        }
        guardar_datos(datos)
        st.rerun()

else:
    # --- APLICACIÓN PRINCIPAL ---
    st.sidebar.title("NeuroFocus")
    
    racha_val = datos.get("racha", 0)
    st.sidebar.metric(label="Días consecutivos", value=racha_val)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Aislamiento Acústico")
    
    # Widget de Spotify Integrado (Profesional y sin bugs de Streamlit)
    components.html(
        '<iframe style="border-radius:12px" src="https://open.spotify.com/embed/playlist/37i9dQZF1DWWQRwui0ExPn?utm_source=generator&theme=0" width="100%" height="152" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>',
        height=160,
    )
    
    st.sidebar.markdown("---")
    opcion = st.sidebar.radio(
        "Panel de Control",
        ["Modo Enfoque", "Protocolos Clínicos", "Análisis de Datos", "Configuración / Pro"]
    )

    perfil = datos.get("perfil", {})

    # --- PESTAÑA 1: MODO ENFOQUE ---
    if opcion == "Modo Enfoque":
        st.title("Ejecución de Tarea")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            cat_tarea = st.selectbox(
                "Categoría operativa",
                ["Estudio", "Desarrollo de Software", "Diseño / Creatividad", "Gestión", "Lectura", "Personalizado"]
            )
        with col_t2:
            detalle_tarea = st.text_input("Especificación técnica de la tarea:", placeholder="Ej. Tema 3 de Física, Refactorización de código...")

        tarea_final = f"{cat_tarea}: {detalle_tarea}" if detalle_tarea else cat_tarea
        st.markdown("---")

        factor_ajuste = 10 if ("Crítico" in perfil.get("sueño", "") or perfil.get("estres", 1) >= 4) else 15

        col_a, col_b = st.columns(2)
        with col_a:
            energia = st.slider("Nivel de energía actual (1-5)", 1, 5, 3)
            tiempo_recomendado = energia * factor_ajuste
            
        with col_b:
            duracion = st.number_input(
                "Duración del bloque (Minutos)",
                min_value=1,
                max_value=180,
                value=tiempo_recomendado,
            )

        st.markdown("---")

        if "ejecutando" not in st.session_state:
            st.session_state.ejecutando = False
        if "pausado" not in st.session_state:
            st.session_state.pausado = False

        if not st.session_state.ejecutando:
            if st.button("Iniciar Bloque", type="primary"):
                st.session_state.ejecutando = True
                st.session_state.pausado = False
                st.session_state.tiempo_restante = duracion * 60
                st.rerun()
        else:
            st.subheader(f"En ejecución: {tarea_final}")
            minutos_r, segundos_r = divmod(st.session_state.tiempo_restante, 60)
            st.markdown(f"<h1 style='text-align: center; font-size: 80px; color: #2e7d32;'>{minutos_r:02d}:{segundos_r:02d}</h1>", unsafe_allow_html=True)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.session_state.pausado:
                    if st.button("Reanudar Operación"):
                        st.session_state.pausado = False
                        st.rerun()
                else:
                    if st.button("Pausar Operación"):
                        st.session_state.pausado = True
                        st.rerun()

            with col_btn2:
                if st.button("Abortar Sesión"):
                    st.session_state.ejecutando = False
                    st.session_state.pausado = False
                    st.rerun()

            if not st.session_state.pausado:
                time.sleep(1)
                st.session_state.tiempo_restante -= 1

                if st.session_state.tiempo_restante <= 0:
                    st.session_state.ejecutando = False
                    st.session_state.sesion_para_evaluar = {
                        "duracion": duracion,
                        "tarea": tarea_final,
                        "categoria": cat_tarea,
                    }
                    st.rerun()
                else:
                    st.rerun()

        if "sesion_para_evaluar" in st.session_state:
            st.markdown("---")
            st.subheader("Auditoría de la Sesión")
            q1 = st.slider("Eficiencia atencional sostenida (%)", 0, 100, 80)
            q2 = st.selectbox("Interrupciones externas o internas", ["Ninguna", "Leve (Menos de 2 min)", "Grave (Pérdida de flujo)"])

            if st.button("Registrar Datos"):
                info_s = st.session_state.sesion_para_evaluar
                nueva = {
                    "fecha": str(date.today()),
                    "duracion": info_s["duracion"],
                    "tarea": info_s["tarea"],
                    "categoria": info_s["categoria"],
                    "eficiencia_pct": q1,
                    "interrupciones": q2,
                }
                datos["sesiones"].append(nueva)

                if datos.get("ultima_fecha") != str(date.today()):
                    datos["racha"] = datos.get("racha", 0) + 1
                    datos["ultima_fecha"] = str(date.today())

                guardar_datos(datos)
                del st.session_state["sesion_para_evaluar"]
                st.rerun()

    # --- PESTAÑA 2: PROTOCOLOS ---
    elif opcion == "Protocolos Clínicos":
        st.title("Frameworks de Optimización Cognitiva")
        st.markdown("Basados en literatura neurocientífica actual para la modulación de la atención.")

        st.markdown("### Protocolo NSDR (Non-Sleep Deep Rest)")
        st.write("Periodo de 10 a 20 minutos de inactividad sensorial para la reestabilización dopaminérgica tras bloques de alta carga.")

        st.markdown("### Umbral de los 5 minutos")
        st.write("Superación de la fricción límbica inicial al comprometerse a una carga de trabajo de solo 300 segundos, induciendo inercia conductual.")

        st.markdown("### Retraso de Adenosina")
        st.write("Abstención de consumo de cafeína durante los primeros 90-120 minutos post-vigilia para evitar el bloqueo prematuro de receptores y el colapso energético vespertino.")

        st.markdown("### Visión Panorámica Post-Esfuerzo")
        st.write("Expansión del campo visual hacia el horizonte para desactivar el sistema nervioso simpático tras periodos de enfoque ocular convergente continuado.")

        st.markdown("### Aislamiento de Dispositivos")
        st.write("Separación física de hardware no esencial para anular la carga de procesamiento en segundo plano que el cerebro utiliza para inhibir el impulso de revisión.")

    # --- PESTAÑA 3: ANÁLISIS DE DATOS ---
    elif opcion == "Análisis de Datos":
        st.title("Métricas de Rendimiento")
        sesiones = datos.get("sesiones", [])

        if not sesiones:
            st.info("Sistema a la espera de recolección de datos.")
        else:
            total_min = sum(s["duracion"] for s in sesiones)
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Volumen Total", f"{total_min / 60:.2f} hrs")
            col_m2.metric("Sesiones Completadas", len(sesiones))
            promedio = sum(s.get("eficiencia_pct", 80) for s in sesiones) / len(sesiones)
            col_m3.metric("Eficiencia Media", f"{promedio:.1f}%")

            st.markdown("---")
            df = pd.DataFrame(sesiones)
            
            # --- FUNCIÓN PREMIUM: EXPORTAR A CSV ---
            st.download_button(
                label="Descargar Informe Analítico (CSV)",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name='neurofocus_datos.csv',
                mime='text/csv',
            )

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.write("Volumen Operativo por Fecha")
                st.bar_chart(df.groupby("fecha")["duracion"].sum())

            with col_g2:
                if "categoria" in df.columns:
                    st.write("Distribución por Categoría")
                    st.bar_chart(df.groupby("categoria")["duracion"].sum())

            st.dataframe(df, use_container_width=True)

    # --- PESTAÑA 4: CONFIGURACIÓN ---
    elif opcion == "Configuración / Pro":
        st.title("Administración del Sistema")
        
        st.markdown("### Suscripción NeuroFocus Pro (Mockup)")
        st.info("Funciones comerciales bloqueadas en esta demo. (Ejemplo de cómo se vería la monetización)")
        st.checkbox("Integración Avanzada con Notion API (Requiere Pro)", disabled=True)
        st.checkbox("Gráficos avanzados de correlación sueño/eficiencia (Requiere Pro)", disabled=True)
        
        st.markdown("---")
        st.markdown("### Zona de Riesgo")
        if st.button("Formatear Base de Datos"):
            datos_vacios = {
                "onboarding_completado": False,
                "perfil": {},
                "sesiones": [],
                "racha": 0,
                "ultima_fecha": "",
            }
            guardar_datos(datos_vacios)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
