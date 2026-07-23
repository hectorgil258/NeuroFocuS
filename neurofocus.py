import json
import os
import time
from datetime import date, timedelta
import pandas as pd
import streamlit as st

DATA_FILE = "neurofocus_data.json"

st.set_page_config(
    page_title="NeuroFocus - Rendimiento Real",
    page_icon="🧠",
    layout="wide",
)


# --- GESTIÓN DE DATOS E HISTORIAL ---
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

CONSEJOS_DISTRACCION = {
    "Móvil y redes sociales": "📱 Deja el móvil en otra habitación o en modo no molestar.",
    "Abrir pestañas de YouTube / Buscar mierdas en internet": "🌐 Cierra las pestañas innecesarias o usa un bloqueador de webs.",
    "Cansancio acumulado y niebla mental": "💧 Bebe un vaso de agua antes de empezar y no forces más de la cuenta.",
    "No tener claro por dónde empezar": "📝 Tómate los primeros 2 minutos solo para definir la subtarea exacta.",
}

ETIQUETAS_ENERGIA = {
    1: "🔴 1 - Exhausto / Bajo mínimos",
    2: "🟠 2 - Regular / Cansado",
    3: "🟡 3 - Neutro / Normal",
    4: "🟢 4 - Bien / Con ganas",
    5: "⚡ 5 - A tope / Con máxima energía",
}

ETIQUETAS_ESTRES = {
    1: "🧘 1 - Muy tranquilo / Relajado",
    2: "🟢 2 - Normal / Bajo control",
    3: "🟡 3 - Algo agitado / Estrés moderado",
    4: "🟠 4 - Bastante saturado",
    5: "🔴 5 - Al límite / Sobrecargado",
}

# --- PANTALLA 1: ONBOARDING ---
if not datos["onboarding_completado"]:
    st.title("🧠 Bienvenido a NeuroFocus")
    st.write(
        "Antes de empezar a meter horas como un loco, vamos a calibrar la app según tu situación actual."
    )
    st.write("Cero rodeos: responde a esto para que el sistema se adapte a ti.")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        sueño = st.select_slider(
            "¿Cómo has dormido hoy?",
            options=[
                "Fatal (< 5h)",
                "Regular (5-6h)",
                "Bien (7-8h)",
                "Como un rey (> 8h)",
            ],
            value="Bien (7-8h)",
        )

        distracciones_seleccionadas = st.multiselect(
            "¿Cuáles de estas cosas te frenan normalmente?",
            list(CONSEJOS_DISTRACCION.keys()),
            default=["Móvil y redes sociales"],
        )

    with col2:
        val_estres = st.slider("¿Cómo de saturado te sientes hoy mentalmente?", 1, 5, 2)
        st.caption(f"Estado actual: **{ETIQUETAS_ESTRES[val_estres]}**")

        meta_diaria = st.number_input(
            "¿Cuántas horas reales de trabajo enfocado quieres sacar hoy?",
            min_value=0.5,
            max_value=10.0,
            value=3.0,
            step=0.5,
        )

    st.markdown("---")

    if st.button("🔥 Guardar y empezar"):
        datos["onboarding_completado"] = True
        datos["perfil"] = {
            "sueño": sueño,
            "distracciones": distracciones_seleccionadas,
            "estres": val_estres,
            "meta_diaria": meta_diaria,
        }
        guardar_datos(datos)
        st.rerun()

else:
    # --- APLICACIÓN PRINCIPAL ---
    st.sidebar.title("🧠 NeuroFocus")

    racha_val = datos.get("racha", 0)
    texto_racha = f"{racha_val} día" if racha_val == 1 else f"{racha_val} días"
    st.sidebar.metric(label="🔥 Racha Actual", value=texto_racha)

    # --- AMBIENTE SONORO RECURSOS STREAM REALES ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎧 Ambiente Sonoro")
    sonido_opt = st.sidebar.selectbox(
        "Audio para aislarte:",
        [
            "Sin Audio",
            "Lluvia Continua",
            "Ondas Binaurales Alfa (Focus)",
            "Ruido Marrón Profundo",
        ],
    )

    if sonido_opt == "Lluvia Continua":
        st.sidebar.audio("https://stream.zeno.fm/21rtr3sz8rhuv")
    elif sonido_opt == "Ondas Binaurales Alfa (Focus)":
        st.sidebar.audio("https://stream.zeno.fm/u8490a07138uv")
    elif sonido_opt == "Ruido Marrón Profundo":
        st.sidebar.audio("https://stream.zeno.fm/v935398q8rhuv")

    st.sidebar.markdown("---")

    opcion = st.sidebar.radio(
        "Navegación",
        [
            "🎯 Iniciar Bloque de Trabajo",
            "💡 Consejos de Verdad",
            "📊 Tus Métricas",
            "⚙️ Ajustes",
        ],
    )

    perfil = datos.get("perfil", {})

    # --- PESTAÑA 1: SESIÓN DE TRABAJO ---
    if opcion == "🎯 Iniciar Bloque de Trabajo":
        st.title("🎯 Sesión de Enfoque Profundo")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            cat_tarea = st.selectbox(
                "¿Qué tipo de actividad vas a realizar?",
                ["Estudiar", "Trabajar", "Programar", "Crear / Diseñar", "Leer", "Otra"],
            )
        with col_t2:
            detalle_tarea = st.text_input(
                "Especifica la tarea concreta:",
                placeholder="Ej. Tema 3 de Física / Ajuste de mezcla / Resumen",
            )

        tarea_final = (
            f"{cat_tarea}: {detalle_tarea}" if detalle_tarea else cat_tarea
        )

        st.markdown("---")

        if "Fatal" in perfil.get("sueño", "") or perfil.get("estres", 1) >= 4:
            st.warning(
                "⚠️ Ojo: Has marcado que estás cansado o saturado. Hemos reducido la intensidad recomendada."
            )
            factor_ajuste = 10
        else:
            factor_ajuste = 15

        col_a, col_b = st.columns(2)
        with col_a:
            energia = st.slider("¿Cómo te notas de energía justo ahora?", 1, 5, 3)
            st.caption(f"Nivel de energía: **{ETIQUETAS_ENERGIA[energia]}**")

        with col_b:
            tiempo_recomendado = energia * factor_ajuste
            st.info(
                f"💡 Duración recomendada para esta sesión: **{tiempo_recomendado} minutos**."
            )
            duracion = st.number_input(
                "Ajusta los minutos a tu gusto:",
                min_value=1,
                max_value=180,
                value=tiempo_recomendado,
            )

        dist_list = perfil.get("distracciones", [])
        if dist_list:
            st.markdown("##### 📌 Recordatorios personalizados para esta sesión:")
            for d in dist_list:
                if d in CONSEJOS_DISTRACCION:
                    st.write(f"- {CONSEJOS_DISTRACCION[d]}")

        st.markdown("---")

        if "ejecutando" not in st.session_state:
            st.session_state.ejecutando = False
        if "pausado" not in st.session_state:
            st.session_state.pausado = False

        if not st.session_state.ejecutando:
            if st.button("🚀 Arrancar Sesión"):
                st.session_state.ejecutando = True
                st.session_state.pausado = False
                st.session_state.tiempo_restante = duracion * 60
                st.rerun()
        else:
            st.subheader(f"📌 Tarea actual: **{tarea_final}**")
            minutos_r, segundos_r = divmod(st.session_state.tiempo_restante, 60)
            st.header(f"⏱️ {minutos_r:02d}:{segundos_r:02d}")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.session_state.pausado:
                    if st.button("▶️ Reanudar"):
                        st.session_state.pausado = False
                        st.rerun()
                else:
                    if st.button("⏸️ Pausar"):
                        st.session_state.pausado = True
                        st.rerun()

            with col_btn2:
                if st.button("🛑 Cancelar Sesión"):
                    st.session_state.ejecutando = False
                    st.session_state.pausado = False
                    st.rerun()

            if not st.session_state.pausado:
                time.sleep(1)
                st.session_state.tiempo_restante -= 1

                if st.session_state.tiempo_restante <= 0:
                    st.session_state.ejecutando = False
                    st.success("🎉 ¡Bloque terminado! Buen trabajo.")
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
            st.subheader("📝 ¿Cómo ha ido la sesión realmente?")
            q1 = st.slider(
                "Del 0 al 100%, ¿cuánto tiempo has estado enfocado de verdad?",
                0,
                100,
                80,
            )
            q2 = st.radio(
                "¿Has caído en la tentación de mirar el móvil o distracciones?",
                ["Para nada", "Alguna miradita rápida", "Sí, me he distraído bastante"],
            )

            if st.button("💾 Guardar resultados"):
                info_s = st.session_state.sesion_para_evaluar
                nueva = {
                    "fecha": str(date.today()),
                    "duracion": info_s["duracion"],
                    "tarea": info_s["tarea"],
                    "categoria": info_s["categoria"],
                    "enfoque_pct": q1,
                    "distracciones": q2,
                }
                datos["sesiones"].append(nueva)

                if datos.get("ultima_fecha") != str(date.today()):
                    datos["racha"] = datos.get("racha", 0) + 1
                    datos["ultima_fecha"] = str(date.today())

                guardar_datos(datos)
                del st.session_state["sesion_para_evaluar"]
                st.success("¡Registrado!")
                st.rerun()

    # --- PESTAÑA 2: CONSEJOS DEFINITIVOS ---
    elif opcion == "💡 Consejos de Verdad":
        st.title("💡 Protocolos de Rendimiento Cognitivo")
        st.write(
            "Estrategias validadas para exprimir tu foco sin quemar tu cerebro:"
        )

        st.markdown("---")
        st.subheader("Protocolo NSDR (Non-Sleep Deep Rest)")
        st.write(
            "Si terminas una sesión agotado o sufres un bajón a mitad del día, realiza una pausa de 10 a 20 minutos con los ojos cerrados en silencio o escuchando una guía NSDR. Este descanso sin estímulos restaura los niveles de dopamina en el cerebro y recarga la capacidad atencional mejor que dormir una siesta pesada."
        )

        st.subheader("La regla de los 5 minutos")
        st.write(
            "Cuando sientas fricción antes de empezar, comprométete a trabajar únicamente durante 5 minutos con el trato de poder parar al terminar. El cerebro busca evitar la incomodidad inicial; una vez superada la barrera de arranque, la inercia te mantendrá enfocado sin esfuerzo."
        )

        st.subheader("Eliminación de la presencia visual del móvil")
        st.write(
            "Tener el teléfono sobre la mesa, incluso boca abajo o apagado, consume recursos atencionales de manera subconsciente. Guardarlo en otra habitación reduce la tentación a cero al añadir fricción física para ir a buscarlo."
        )

        st.subheader("Retraso estratégico de la cafeína")
        st.write(
            "Ingerir cafeína inmediatamente al despertar bloquea los receptores de adenosina antes de que el cuerpo la limpie de forma natural, provocando el desplome de energía por la tarde. Esperar entre 90 y 120 minutos tras levantarte optimiza la alerta durante todo el día."
        )

        st.subheader("Ciclos ultradianos de trabajo")
        st.write(
            "El cerebro no está diseñado para mantener atención máxima continua durante más de 90 minutos. Estructurar el día en bloques intensos de 45 a 90 minutos seguidos de descansos reales maximiza la producción total sin acumular fatiga cognitiva."
        )

        st.subheader("Anclaje visual previo al bloque")
        st.write(
            "Fijar la mirada en un punto concreto durante 30 segundos antes de comenzar activa el sistema nervioso simpático y contrae el campo visual, preparando al cerebro para la concentración profunda."
        )

        st.subheader("Descompresión con visión panorámica")
        st.write(
            "Al finalizar cada bloque de estudio o trabajo, enfoca la vista hacia el horizonte o espacios abiertos. La visión panorámica relaja los músculos oculares e indica a la amígdala que el periodo de esfuerzo ha terminado, previniendo el agotamiento."
        )

        st.subheader("Abono de distracciones o hoja de descargas")
        st.write(
            "Mantener un papel al lado del teclado para anotar pensamientos intrusivos o tareas pendientes que surjan durante el bloque permite 'liberar' la memoria de trabajo inmediatamente y retomar la tarea sin romper el estado de flujo."
        )

        st.subheader("Luz solar matutina")
        st.write(
            "Exponerse a la luz del sol en las dos primeras horas del día activa un pico de cortisol natural que regula el reloj circadiano, eleva el estado de ánimo e incrementa la energía para las sesiones del día."
        )

        st.subheader("Gestión de la temperatura del entorno")
        st.write(
            "Trabajar en ambientes ligeramente frescos (entre 19°C y 21°C) estimula el estado de alerta del organismo. Los entornos demasiado cálidos activan respuestas de somnolencia y reducen drásticamente la velocidad de procesamiento mental."
        )

    # --- PESTAÑA 3: MÉTRICAS Y GRÁFICOS ---
    elif opcion == "📊 Tus Métricas":
        st.title("📊 Tu Progreso Real")
        sesiones = datos.get("sesiones", [])

        if not sesiones:
            st.warning("Aún no hay datos guardados. Completa tu primer bloque.")
        else:
            total_min = sum(s["duracion"] for s in sesiones)
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Horas Totales", f"{total_min / 60:.2f} hrs")
            col_m2.metric("Sesiones Hechas", len(sesiones))
            promedio = sum(s.get("enfoque_pct", 80) for s in sesiones) / len(
                sesiones
            )
            col_m3.metric("Enfoque Medio", f"{promedio:.0f}%")

            st.markdown("---")
            st.subheader("📈 Gráficos de Evolución Temporal")

            df = pd.DataFrame(sesiones)

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.write("**Minutos Invertidos por Fecha:**")
                chart_data = df.groupby("fecha")["duracion"].sum()
                st.bar_chart(chart_data)

            with col_g2:
                if "categoria" in df.columns:
                    st.write("**Minutos por Categoría de Tarea:**")
                    cat_data = df.groupby("categoria")["duracion"].sum()
                    st.bar_chart(cat_data)

            st.subheader("Historial Detallado")
            st.dataframe(df)

    # --- PESTAÑA 4: AJUSTES ---
    elif opcion == "⚙️ Ajustes":
        st.title("⚙️ Ajustes del Sistema")

        if st.button("🔴 Borrar Todo (Cero absoluto)"):
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
            st.success("¡Todo reseteado con éxito!")
            st.rerun()