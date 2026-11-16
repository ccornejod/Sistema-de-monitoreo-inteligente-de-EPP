"""Centro de monitoreo preventivo de EPP.

Dashboard académico con los resultados de n8n, YOLO, modelos de series,
Transformer y recomendaciones individuales de Gemini.

Fuente inicial: copias CSV de las hojas de Google Sheets.
No hay una conexión en vivo con n8n/Sheets. No se incluyen imágenes ni correos.
"""
from datetime import date
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Centro de Supervisión | EPP",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta del proyecto: contraste alto, sin gráficos decorativos innecesarios.
NAVY = "#173354"
INK = "#273949"
MUTED = "#6B7B8D"
TURQUOISE = "#138E9B"
ORANGE = "#DD883E"
RED = "#BA4B51"
BLUE = "#4B7DB3"
COLORS = [NAVY, TURQUOISE, ORANGE, BLUE, RED]

CATEGORY_NAMES = {
    "sin_evento_reportado": "Sin evento reportado",
    "transporte": "Transporte",
    "contacto_objetos": "Contacto con objetos",
    "caidas": "Caídas",
    "exposicion_sustancias": "Exposición a sustancias",
}

# Formato visual, sin ocultar las funciones de navegación ni los controles.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp {font-family:'DM Sans',Arial,sans-serif;}
[data-testid="stAppViewContainer"] {background:#FAFBFD;}
.block-container {max-width:1320px; padding-top:1.4rem; padding-bottom:3rem;}
[data-testid="stSidebar"] {background:#F2F5F9; border-right:1px solid #E2E8F0;}
[data-testid="stSidebar"] .block-container {padding-top:2rem;}
h1, h2, h3 {color:#173354 !important; letter-spacing:-.025em;}
[data-testid="stMetric"] {background:#FFFFFF; border:1px solid #E0E8F1;
    border-radius:13px; padding:18px 20px; box-shadow:0 4px 14px rgba(20,42,74,.035);}
[data-testid="stMetricLabel"] {font-size:13px; color:#56677B;}
[data-testid="stMetricValue"] {font-size:29px; color:#173354; font-weight:750;}
[data-testid="stTabs"] button {font-weight:600;}
[data-testid="stDataFrame"] {border:1px solid #E4EAF1;border-radius:10px;}
.hero {background:linear-gradient(110deg,#122B49,#234B70);color:white;padding:27px 32px;
    border-radius:15px; margin-bottom:18px;box-shadow:0 8px 22px rgba(17,41,68,.13);}
.hero .eyebrow {font-size:12px;letter-spacing:1.5px;text-transform:uppercase;
    color:#B8D8E4;font-weight:700;margin-bottom:8px;}
.hero h1 {color:#FFFFFF!important;margin:0;font-size:32px;line-height:1.18;}
.hero p {margin:11px 0 0;color:#DCE9F1;font-size:14px;}
.section-intro {font-size:14px;color:#66788A;margin-top:-4px;margin-bottom:15px;}
.note {border:1px solid #DFE8F1; border-left:4px solid #138E9B;
    background:#F1F8FB;padding:15px 17px;border-radius:9px;margin:14px 0;color:#304457;font-size:14px;}
.note strong {color:#173354;}
.warn {border-left:4px solid #DD883E;background:#FEF6ED;border-radius:8px;
    padding:13px 16px;color:#654C32;margin:13px 0;font-size:14px;}
.mini-label {font-size:12px;letter-spacing:1px;text-transform:uppercase;font-weight:800;color:#138E9B;}
.kicker {font-size:13px;color:#6A7A8C;margin-bottom:10px;}
.footer {font-size:12px;color:#66788A;border-top:1px solid #DDE5ED;padding-top:17px;margin-top:24px;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def get_saved_data():
    """Leer los tres CSV incluidos en el proyecto (sin credenciales)."""
    folder = Path(__file__).resolve().parent / "data"
    return (
        pd.read_csv(folder / "inspecciones.csv"),
        pd.read_csv(folder / "pronosticos.csv"),
        pd.read_csv(folder / "transformer.csv"),
    )


def prepare_inspections(frame):
    """Admite CSV de la app y el CSV bruto de la hoja Inspecciones de n8n."""
    df = frame.copy()
    if "fecha" not in df:
        if "fecha_local_inspeccion" in df:
            df["fecha"] = df["fecha_local_inspeccion"]
        elif "fecha_inspeccion" in df:
            # Convertir ISO con zona horaria a fecha local de Santiago.
            parsed = pd.to_datetime(df["fecha_inspeccion"], errors="coerce", utc=True)
            df["fecha"] = parsed.dt.tz_convert("America/Santiago").dt.strftime("%Y-%m-%d")
    if "zona" not in df and "zona_id" in df:
        df["zona"] = df["zona_id"]
    if "registro" not in df:
        if "id_inspeccion" in df:
            df["registro"] = df["id_inspeccion"]
        else:
            df["registro"] = range(1, len(df) + 1)
    required = ["fecha", "supervisor", "trabajadores_detectados", "requieren_revision",
                "prioridad", "estado_revision", "recomendacion"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error("Faltan columnas en Inspecciones: " + ", ".join(missing))
        st.stop()
    for c in ["diagnostico", "justificacion", "zona"]:
        if c not in df:
            df[c] = ""
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"]).copy()
    for c in ["trabajadores_detectados", "requieren_revision"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).clip(lower=0)
    for c in ["supervisor", "prioridad", "estado_revision", "zona"]:
        df[c] = df[c].fillna("Sin información").astype(str).str.strip()
    return df


def prepare_forecasts(frame):
    df = frame.copy()
    required = ["fecha_pronostico", "zona_id", "modelo", "trabajadores_revision_estimados"]
    if any(c not in df for c in required):
        st.error("El CSV Pronósticos no tiene el formato esperado.")
        st.stop()
    df["fecha_pronostico"] = pd.to_datetime(df["fecha_pronostico"], errors="coerce")
    df["trabajadores_revision_estimados"] = pd.to_numeric(
        df["trabajadores_revision_estimados"], errors="coerce"
    )
    return df.dropna(subset=["fecha_pronostico", "trabajadores_revision_estimados"]).copy()


def prepare_transformer(frame):
    df = frame.copy()
    needed = ["fecha", "zona_id", "categoria_predicha"]
    if any(c not in df for c in needed):
        st.error("El CSV Transformer no tiene el formato esperado.")
        st.stop()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"]).copy()
    df["categoria_nombre"] = df["categoria_predicha"].fillna("Sin clasificación").map(
        CATEGORY_NAMES
    ).fillna(df["categoria_predicha"].astype(str).str.replace("_", " "))
    df["zona_nombre"] = df["zona_id"].astype(str).str.replace("zona_", "Zona ", regex=False)
    return df


def clean_plot(fig, height=340):
    """Aplicar formato consistente a gráficos Plotly."""
    fig.update_layout(
        template="plotly_white", height=height,
        margin=dict(l=8, r=15, t=20, b=8),
        font=dict(family="DM Sans, Arial, sans-serif", color=INK, size=13),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="#173354", font_color="white"),
    )
    fig.update_yaxes(gridcolor="#ECF0F4", zerolinecolor="#ECF0F4", rangemode="tozero")
    fig.update_xaxes(showgrid=False)
    return fig


def as_int(v):
    return f"{int(v):,}".replace(",", ".")


def label_zone(z):
    txt = str(z)
    return txt.replace("zona_", "Zona ") if txt.startswith("zona_") else txt


# Lectura inicial y actualización manual opcional.
inspections_raw, forecasts_raw, transformer_raw = get_saved_data()

st.sidebar.markdown("### 🦺 Centro de supervisión")
st.sidebar.caption("Sistema de monitoreo preventivo de EPP")
st.sidebar.divider()
with st.sidebar.expander("Actualizar datos desde CSV", expanded=False):
    st.caption("Opcional: descarga CSV de las hojas y súbelos aquí. Los cambios no se guardan en GitHub.")
    uploaded_ins = st.file_uploader("Inspecciones", type="csv", key="up_i")
    uploaded_fc = st.file_uploader("Pronósticos", type="csv", key="up_f")
    uploaded_tr = st.file_uploader("Transformer", type="csv", key="up_t")
    try:
        if uploaded_ins is not None:
            inspections_raw = pd.read_csv(uploaded_ins)
        if uploaded_fc is not None:
            forecasts_raw = pd.read_csv(uploaded_fc)
        if uploaded_tr is not None:
            transformer_raw = pd.read_csv(uploaded_tr)
    except Exception as error:
        st.error(f"No se pudo abrir el CSV: {error}")
        st.stop()

inspections = prepare_inspections(inspections_raw)
forecasts = prepare_forecasts(forecasts_raw)
transformer = prepare_transformer(transformer_raw)

st.sidebar.markdown("#### Filtros del historial")
supervisors = sorted(inspections["supervisor"].dropna().unique().tolist())
chosen_supervisors = st.sidebar.multiselect("Supervisor responsable", supervisors, default=supervisors)

if not inspections.empty:
    first_day = inspections["fecha"].min().date()
    last_day = inspections["fecha"].max().date()
    dates = st.sidebar.date_input("Período de inspección", (first_day, last_day),
                                  min_value=first_day, max_value=last_day)
    if isinstance(dates, (list, tuple)) and len(dates) == 2:
        start_date, end_date = dates
    elif isinstance(dates, (list, tuple)) and len(dates) == 1:
        start_date, end_date = dates[0], last_day
    else:
        start_date, end_date = first_day, last_day
else:
    start_date = end_date = date.today()

zones = sorted(inspections["zona"].dropna().unique().tolist())
selected_zones = st.sidebar.multiselect("Zona inspeccionada", zones, default=zones)

chosen = inspections[
    inspections["supervisor"].isin(chosen_supervisors)
    & inspections["zona"].isin(selected_zones)
    & (inspections["fecha"].dt.date >= start_date)
    & (inspections["fecha"].dt.date <= end_date)
].copy()

st.markdown('''
<div class="hero">
  <div class="eyebrow">IA GENERATIVA · GESTIÓN INDUSTRIAL</div>
  <h1>Centro de supervisión de EPP</h1>
  <p>Seguimiento de inspecciones, planificación preventiva y recomendaciones basadas en modelos de IA.</p>
</div>
''', unsafe_allow_html=True)

st.caption(
    "Datos académicos de demostración · Inspecciones de prueba · "
    "Pronósticos y clasificaciones simulados · Instantánea de Sheets (no actualización en vivo)"
)

summary_tab, forecasts_tab, transformer_tab, ai_tab = st.tabs([
    "▣  Vista general", "◫  Pronósticos", "▤  Transformer", "✦  Recomendaciones"
])

with summary_tab:
    st.markdown("### Panorama operacional")
    st.markdown('<p class="section-intro">Resultados correspondientes al período y supervisores seleccionados.</p>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    high = (chosen["prioridad"].str.lower() == "alta")
    waiting = (chosen["estado_revision"].str.lower() == "pendiente")
    high_pending = int((high & waiting).sum())
    k1.metric("Inspecciones registradas", as_int(len(chosen)))
    k2.metric("Trabajadores detectados", as_int(chosen["trabajadores_detectados"].sum()))
    k3.metric("Trabajadores para verificar", as_int(chosen["requieren_revision"].sum()))
    k4.metric("Prioridad alta + pendiente", as_int(high_pending))

    st.markdown(
        '<div class="note"><strong>Lectura del panel:</strong> los trabajadores para verificar son casos '
        'en los que el sistema no confirmó algún EPP requerido. No son infracciones comprobadas. '
        'La revisión presencial y la decisión final corresponden al supervisor.</div>',
        unsafe_allow_html=True,
    )

    if chosen.empty:
        st.warning("No hay inspecciones con los filtros seleccionados.")
    else:
        left, right = st.columns([1.45, 1], gap="large")
        with left:
            st.markdown("#### Actividad diaria")
            st.caption("Inspecciones ejecutadas por fecha")
            daily = chosen.groupby(chosen["fecha"].dt.date).agg(
                Inspecciones=("registro", "size"),
            ).reset_index().rename(columns={"fecha": "Fecha"})
            # Nombre de la columna de fecha según la versión de Pandas.
            daily = daily.rename(columns={daily.columns[0]: "Fecha"})
            fig = px.bar(daily, x="Fecha", y="Inspecciones", color_discrete_sequence=[NAVY],
                         text="Inspecciones")
            fig.update_traces(textposition="outside")
            fig.update_yaxes(title_text="N.º de inspecciones", dtick=1)
            st.plotly_chart(clean_plot(fig, 325), use_container_width=True)
        with right:
            st.markdown("#### Priorización")
            st.caption("Número de inspecciones por prioridad asignada")
            priorities = chosen["prioridad"].str.lower().value_counts()
            pframe = pd.DataFrame({
                "Prioridad": ["Alta", "Media", "Baja"],
                "Inspecciones": [int(priorities.get(p, 0)) for p in ["alta", "media", "baja"]],
            })
            fig = px.bar(pframe, x="Prioridad", y="Inspecciones", color="Prioridad",
                         color_discrete_map={"Alta":RED, "Media":ORANGE, "Baja":TURQUOISE},
                         text="Inspecciones")
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False)
            fig.update_yaxes(title_text="N.º de inspecciones", dtick=1)
            st.plotly_chart(clean_plot(fig, 325), use_container_width=True)

        st.markdown("#### Casos para seguimiento")
        st.caption("Inspecciones de prioridad alta aún marcadas como pendientes en el historial")
        urgent = chosen[high & waiting].sort_values("fecha", ascending=False).head(6)
        if urgent.empty:
            st.success("No hay registros de prioridad alta pendientes en el período seleccionado.")
        else:
            st.dataframe(
                urgent[["fecha", "supervisor", "zona", "trabajadores_detectados", "requieren_revision", "recomendacion"]]
                .rename(columns={"fecha":"Fecha", "supervisor":"Supervisor", "zona":"Zona",
                                 "trabajadores_detectados":"Detectados", "requieren_revision":"Por verificar",
                                 "recomendacion":"Acción sugerida"}),
                hide_index=True, use_container_width=True, height=248,
            )
        st.markdown(
            '<div class="warn"><strong>Estado de revisión:</strong> n8n marca inicialmente las inspecciones como '
            '«pendiente». El flujo exportado no muestra una actualización automática después de la revisión humana. '
            'Por eso no debe interpretarse el total pendiente como incumplimientos efectivos.</div>',
            unsafe_allow_html=True,
        )

        with st.expander("Ver historial completo de inspecciones"):
            st.dataframe(
                chosen.sort_values("fecha", ascending=False)[[
                    "fecha", "supervisor", "zona", "trabajadores_detectados", "requieren_revision",
                    "prioridad", "estado_revision"
                ]].rename(columns={
                    "fecha":"Fecha", "supervisor":"Supervisor", "zona":"Zona",
                    "trabajadores_detectados":"Detectados", "requieren_revision":"Por verificar",
                    "prioridad":"Prioridad", "estado_revision":"Revisión humana"
                }),
                hide_index=True, use_container_width=True,
            )

with forecasts_tab:
    st.markdown("### Pronósticos para planificar inspecciones")
    st.markdown('<p class="section-intro">Cantidad estimada de trabajadores que podrían requerir verificación de EPP por fecha y zona.</p>', unsafe_allow_html=True)
    if forecasts.empty:
        st.warning("No hay pronósticos disponibles.")
    else:
        available_dates = sorted(forecasts["fecha_pronostico"].dt.date.unique().tolist())
        next_dates = [d for d in available_dates if d >= date.today()]
        default_date = next_dates[0] if next_dates else available_dates[-1]
        plan_date = st.selectbox("Fecha para planificar", available_dates,
                                 index=available_dates.index(default_date),
                                 format_func=lambda d: d.strftime("%d/%m/%Y"))
        snapshot = forecasts[forecasts["fecha_pronostico"].dt.date == plan_date]
        cols = st.columns(max(1, min(len(snapshot), 3)))
        for idx, (_, row) in enumerate(snapshot.sort_values("zona_id").iterrows()):
            with cols[idx % len(cols)]:
                st.metric(f"{label_zone(row['zona_id'])} · {row['modelo']}",
                          f"≈ {round(row['trabajadores_revision_estimados'])} trabajadores")
        st.markdown('<div class="note"><strong>¿Para qué sirve?</strong> Permite estimar la carga potencial de verificaciones y organizar recorridos y tiempo de supervisión. Las cifras no equivalen a incumplimientos ni a trabajadores observados.</div>', unsafe_allow_html=True)
        st.markdown("#### Evolución de estimaciones")
        forecast_graph = forecasts.copy()
        forecast_graph["Serie"] = forecast_graph.apply(
            lambda r: f"{label_zone(r['zona_id'])} · {r['modelo']}", axis=1
        )
        fig = px.line(forecast_graph, x="fecha_pronostico", y="trabajadores_revision_estimados",
                      color="Serie", markers=True, color_discrete_sequence=[TURQUOISE, BLUE],
                      labels={"fecha_pronostico":"Fecha de pronóstico",
                              "trabajadores_revision_estimados":"Trabajadores estimados"})
        fig.update_traces(line_width=3, marker_size=6)
        fig.update_layout(hovermode="x unified", legend_title_text="")
        st.plotly_chart(clean_plot(fig, 385), use_container_width=True)
        st.caption("Los pronósticos fueron calculados previamente sobre datos simulados y se obtienen de Sheets. LSTM y Holt-Winters corresponden a zonas diferentes: no permiten comparar directamente riesgo ni precisión entre zonas.")

with transformer_tab:
    st.markdown("### Clasificación de reportes con Transformer")
    st.markdown('<p class="section-intro">Resumen de categorías predichas en 220 textos simulados. Son clasificaciones de prueba, no incidentes reales.</p>', unsafe_allow_html=True)
    if transformer.empty:
        st.warning("No hay resultados Transformer disponibles.")
    else:
        no_events = transformer["categoria_predicha"] == "sin_evento_reportado"
        t1, t2, t3 = st.columns(3)
        t1.metric("Reportes clasificados", as_int(len(transformer)))
        t2.metric("Sin evento reportado", as_int(no_events.sum()))
        t3.metric("Otras categorías", as_int((~no_events).sum()))
        st.markdown('<div class="note"><strong>Interpretación:</strong> el Transformer organiza las descripciones según su categoría. En esta muestra de prueba predominan los textos clasificados como «sin evento reportado». Las demás categorías sirven para ilustrar posibles focos de revisión documental.</div>', unsafe_allow_html=True)
        st.markdown("#### Otras categorías identificadas por zona")
        show_noevent = st.toggle("Incluir también «Sin evento reportado» en el gráfico", value=False)
        visible = transformer if show_noevent else transformer[~no_events]
        if visible.empty:
            st.info("No hay categorías para graficar con el filtro actual.")
        else:
            freq = visible.groupby(["categoria_nombre", "zona_nombre"], as_index=False).size().rename(
                columns={"size":"Registros", "categoria_nombre":"Categoría", "zona_nombre":"Zona"}
            )
            fig = px.bar(freq, x="Registros", y="Categoría", color="Zona", orientation="h",
                         barmode="group", color_discrete_sequence=[TURQUOISE, BLUE],
                         text="Registros")
            fig.update_traces(textposition="outside")
            fig.update_yaxes(title_text="", categoryorder="total ascending")
            fig.update_xaxes(title_text="Cantidad de reportes de prueba")
            st.plotly_chart(clean_plot(fig, 380), use_container_width=True)
        with st.expander("Ver resumen completo por zona"):
            table = transformer.groupby(["zona_nombre", "categoria_nombre"], as_index=False).size().rename(
                columns={"zona_nombre":"Zona", "categoria_nombre":"Categoría", "size":"Registros"}
            )
            st.dataframe(table, hide_index=True, use_container_width=True)
        st.caption("Los datos son históricos y simulados. Los conteos no miden siniestralidad ni permiten concluir qué riesgos predominan en la operación real.")

with ai_tab:
    st.markdown("### Historial de diagnósticos y recomendaciones")
    st.markdown('<p class="section-intro">Respuestas de Gemini guardadas por inspección en Google Sheets; se aplican los filtros del menú lateral.</p>', unsafe_allow_html=True)
    if chosen.empty:
        st.warning("No hay recomendaciones con estos filtros.")
    else:
        choices = ["Todas", "Alta", "Media", "Baja"]
        priority = st.selectbox("Filtrar por prioridad", choices, index=0)
        records = chosen if priority == "Todas" else chosen[
            chosen["prioridad"].str.lower() == priority.lower()
        ]
        records = records.sort_values(["fecha", "registro"], ascending=False)
        st.caption(f"{len(records)} recomendaciones registradas en el período.")
        for _, row in records.head(10).iterrows():
            zone = label_zone(row["zona"])
            tag = f"{row['fecha'].strftime('%d/%m/%Y')} · {row['supervisor']} · {row['prioridad'].upper()}"
            with st.expander(tag):
                st.markdown(f"**Zona:** {escape(zone)}")
                st.markdown(f"**Diagnóstico:** {escape(str(row['diagnostico']))}")
                st.markdown(f"**Recomendación:** {escape(str(row['recomendacion']))}")
                st.markdown(f"**Justificación:** {escape(str(row['justificacion']))}")
                st.caption("Sugerencia automática sujeta a revisión humana.")
        if len(records) > 10:
            st.caption("Se muestran las 10 más recientes; el resto se encuentra en la tabla descargable.")
        with st.expander("Ver todas las recomendaciones y exportar"):
            view = records[["fecha", "supervisor", "zona", "prioridad", "diagnostico", "recomendacion", "justificacion"]].copy()
            st.dataframe(view, hide_index=True, use_container_width=True)
            st.download_button("Descargar CSV filtrado", view.to_csv(index=False).encode("utf-8-sig"),
                               file_name="recomendaciones_epp.csv", mime="text/csv")
    st.caption("Las recomendaciones de cierre diario se envían por Gmail, pero el flujo n8n actual no las guarda en una hoja histórica; por eso aquí se muestran las recomendaciones individuales de las inspecciones.")

st.markdown('''<div class="footer">Proyecto académico · IA generativa para la gestión industrial · n8n + YOLO + LSTM/Holt-Winters + Transformer + Gemini. La decisión de seguridad debe pasar por validación humana. Datos de prueba; actualización manual por CSV.</div>''', unsafe_allow_html=True)
