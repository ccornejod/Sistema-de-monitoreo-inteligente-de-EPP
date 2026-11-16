"""Dashboard académico de EPP: Streamlit + Pandas + Plotly Express.

Los CSV incluidos son una instantánea anonimizada de los registros de prueba.
No consulta n8n ni Google Sheets en tiempo real.
"""

from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Monitoreo preventivo EPP", page_icon="⛑️", layout="wide")

NAVY = "#16365c"
TEAL = "#008c95"
BG = "#f5f8fc"
LABELS = {
    "sin_evento_reportado": "Sin evento reportado",
    "transporte": "Transporte",
    "contacto_objetos": "Contacto con objetos",
    "caidas": "Caídas",
    "exposicion_sustancias": "Exposición a sustancias",
}

st.markdown("""
<style>
.block-container {padding-top:1.6rem; padding-bottom:3rem; max-width:1350px;}
[data-testid="stMetric"] {background:#f3f7fb; border:1px solid #e5ebf3; padding:16px; border-radius:12px;}
h1, h2, h3 {color:#16365c;}
div[data-testid="stAlert"] {border-radius:10px;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def read_builtin():
    root = Path(__file__).resolve().parent / "data"
    return (
        pd.read_csv(root / "inspecciones.csv"),
        pd.read_csv(root / "pronosticos.csv"),
        pd.read_csv(root / "transformer.csv"),
    )

insp, forecast, transformer = read_builtin()

st.sidebar.title("⛑️ Monitoreo EPP")
st.sidebar.caption("Panel académico de apoyo a la supervisión")
st.sidebar.divider()

with st.sidebar.expander("Actualizar datos con CSV (opcional)", expanded=False):
    st.caption("Puedes sustituir la instantánea de demostración por CSV con las mismas columnas, sin datos personales.")
    file_ins = st.file_uploader("Inspecciones", type="csv", key="in")
    file_for = st.file_uploader("Pronósticos", type="csv", key="pr")
    file_tr = st.file_uploader("Transformer", type="csv", key="tr")
    try:
        if file_ins: insp = pd.read_csv(file_ins)
        if file_for: forecast = pd.read_csv(file_for)
        if file_tr: transformer = pd.read_csv(file_tr)
    except Exception as exc:
        st.error(f"No se pudieron leer los CSV: {exc}")
        st.stop()

must_ins = {"fecha", "supervisor", "zona", "trabajadores_detectados", "requieren_revision", "prioridad", "estado_revision", "recomendacion"}
must_forecast = {"fecha_pronostico", "zona_id", "modelo", "trabajadores_revision_estimados"}
must_transformer = {"fecha", "zona_id", "categoria_predicha"}
for frame, required, label in [(insp,must_ins,"inspecciones"), (forecast,must_forecast,"pronósticos"), (transformer,must_transformer,"Transformer")]:
    missing = required - set(frame.columns)
    if missing:
        st.error(f"El CSV de {label} no tiene estas columnas: {', '.join(sorted(missing))}")
        st.stop()

insp["fecha"] = pd.to_datetime(insp["fecha"], errors="coerce")
forecast["fecha_pronostico"] = pd.to_datetime(forecast["fecha_pronostico"], errors="coerce")
transformer["fecha"] = pd.to_datetime(transformer["fecha"], errors="coerce")
for c in ["trabajadores_detectados", "requieren_revision"]:
    insp[c] = pd.to_numeric(insp[c], errors="coerce").fillna(0)
forecast["trabajadores_revision_estimados"] = pd.to_numeric(forecast["trabajadores_revision_estimados"], errors="coerce")
insp = insp.dropna(subset=["fecha"]).copy()
forecast = forecast.dropna(subset=["fecha_pronostico"]).copy()
transformer = transformer.dropna(subset=["fecha"]).copy()

st.sidebar.subheader("Filtros de inspección")
supervisors = sorted(insp["supervisor"].dropna().astype(str).unique())
selected = st.sidebar.multiselect("Supervisor", supervisors, default=supervisors)
ins_min, ins_max = insp["fecha"].min().date(), insp["fecha"].max().date()
interval = st.sidebar.date_input("Fechas de inspección", value=(ins_min, ins_max), min_value=ins_min, max_value=ins_max)
if isinstance(interval,(tuple,list)) and len(interval)==2:
    a,b = interval
elif isinstance(interval,(tuple,list)) and len(interval)==1:
    a,b = interval[0], ins_max
else:
    a,b = ins_min, ins_max
insp_view = insp[(insp["supervisor"].isin(selected)) & (insp["fecha"].dt.date >= a) & (insp["fecha"].dt.date <= b)].copy()

st.title("⛑️ Monitoreo preventivo de EPP")
st.caption("Dashboard de apoyo a la decisión industrial | Series temporales · Visión computacional · Transformer · Gemini")
st.info("**Datos académicos de demostración.** Las inspecciones corresponden a registros de prueba y los pronósticos y clasificaciones son simulados. El panel utiliza una instantánea de Sheets, no datos en vivo.", icon="ℹ️")

tab_ins, tab_fc, tab_tr, tab_llm = st.tabs(["📋 Inspecciones y EPP", "📈 Pronósticos", "🧠 Transformer", "💬 Recomendaciones Gemini"])

with tab_ins:
    st.subheader("Resultados de supervisión")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Inspecciones registradas", f"{len(insp_view):,}".replace(",","."))
    c2.metric("Trabajadores detectados", f"{int(insp_view['trabajadores_detectados'].sum()):,}".replace(",","."))
    c3.metric("Requieren verificación", f"{int(insp_view['requieren_revision'].sum()):,}".replace(",","."))
    pending = (insp_view["estado_revision"].fillna("").astype(str).str.lower().str.strip()=="pendiente").sum()
    c4.metric("Inspecciones pendientes", int(pending))
    if insp_view.empty:
        st.warning("No hay inspecciones para los filtros seleccionados.")
    else:
        col1,col2=st.columns([1.5,1])
        with col1:
            daily=insp_view.groupby(insp_view["fecha"].dt.date).agg(inspecciones=("fecha","size"),requieren_revision=("requieren_revision","sum")).reset_index()
            daily.columns=["Fecha","Inspecciones","Trabajadores a verificar"]
            long=daily.melt("Fecha",var_name="Indicador",value_name="Cantidad")
            fig=px.line(long,x="Fecha",y="Cantidad",color="Indicador",markers=True,title="Evolución diaria de inspecciones y verificaciones")
            fig.update_layout(legend_title_text="",margin=dict(l=10,r=10,t=50,b=10),height=350)
            st.plotly_chart(fig,use_container_width=True)
        with col2:
            counts=insp_view.assign(prioridad=insp_view["prioridad"].fillna("Sin definir").str.capitalize()).groupby("prioridad",as_index=False).size()
            fig=px.pie(counts,names="prioridad",values="size",hole=.55,title="Distribución de prioridades")
            fig.update_layout(margin=dict(l=10,r=10,t=50,b=10),height=350)
            st.plotly_chart(fig,use_container_width=True)
        st.caption("La detección por imagen identifica elementos no confirmados; estos resultados no prueban por sí solos un incumplimiento normativo.")
        st.markdown("**Detalle filtrado de inspecciones**")
        cols=[c for c in ["fecha","supervisor","zona","trabajadores_detectados","requieren_revision","prioridad","estado_revision"] if c in insp_view]
        st.dataframe(insp_view[cols].sort_values("fecha",ascending=False),hide_index=True,use_container_width=True)

with tab_fc:
    st.subheader("Pronósticos de carga potencial de verificación de EPP")
    st.write("Los modelos estiman trabajadores que **podrían requerir revisión de EPP** en cada zona y fecha. No son incumplimientos comprobados ni mediciones del día.")
    zonas=sorted(forecast["zona_id"].dropna().unique())
    forecast_select=st.multiselect("Seleccionar zona(s)",zonas,default=zonas,key="forecast_z")
    fc=forecast[forecast["zona_id"].isin(forecast_select)].copy()
    fc["Serie"] = fc["zona_id"].astype(str).str.replace("zona_","Zona ",regex=False) + " · " + fc["modelo"].astype(str)
    if not fc.empty:
        fig=px.line(fc,x="fecha_pronostico",y="trabajadores_revision_estimados",color="Serie",markers=True,
                    labels={"fecha_pronostico":"Fecha de pronóstico","trabajadores_revision_estimados":"Trabajadores estimados"},
                    title="Evolución de estimaciones por zona y modelo")
        fig.update_layout(margin=dict(l=10,r=10,t=50,b=10),height=420,hovermode="x unified",legend_title_text="Zona / Modelo")
        st.plotly_chart(fig,use_container_width=True)
        last=fc.sort_values("fecha_pronostico").groupby(["zona_id","modelo"],as_index=False).tail(1)
        last=last[["fecha_pronostico","zona_id","modelo","trabajadores_revision_estimados"]]
        st.markdown("**Último pronóstico disponible por serie**")
        st.dataframe(last,hide_index=True,use_container_width=True)
    else:
        st.warning("Selecciona al menos una zona.")
    st.caption("Fuente: serie de pronósticos simulados calculados previamente y guardados en Sheets. LSTM y Holt-Winters se muestran en zonas diferentes: no corresponde comparar directamente su precisión ni el riesgo de las zonas a partir de las magnitudes.")

with tab_tr:
    st.subheader("Clasificación de reportes con Transformer")
    st.write("Distribución de las **categorías predichas** por el clasificador de texto sobre una muestra histórica simulada. No son incidentes reales.")
    trans=transformer.copy()
    trans["Categoría"] = trans["categoria_predicha"].astype(str).map(LABELS).fillna(trans["categoria_predicha"].astype(str))
    trans["Zona"] = trans["zona_id"].astype(str).str.replace("zona_","Zona ",regex=False)
    no_events=st.checkbox("Mostrar categoría 'Sin evento reportado'",value=True)
    display=trans.copy() if no_events else trans[trans["categoria_predicha"]!="sin_evento_reportado"].copy()
    if not display.empty:
        grouped=display.groupby(["Zona","Categoría"],as_index=False).size().rename(columns={"size":"Registros"})
        fig=px.bar(grouped,x="Zona",y="Registros",color="Categoría",barmode="group",title="Registros clasificados por categoría y zona")
        fig.update_layout(margin=dict(l=10,r=10,t=50,b=10),height=400,legend_title_text="Categoría")
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.warning("Sin categorías para mostrar.")
    counts=trans.groupby(["Zona","Categoría"],as_index=False).size().rename(columns={"size":"Registros"})
    st.markdown("**Resumen de clasificaciones por zona**")
    st.dataframe(counts,hide_index=True,use_container_width=True)
    st.markdown("**Evolución temporal de categorías diferentes de 'sin evento'**")
    events=trans[trans["categoria_predicha"]!="sin_evento_reportado"].copy()
    if len(events):
        events_daily=events.groupby([events["fecha"].dt.date,"Categoría"],as_index=False).size().rename(columns={"fecha":"Fecha","size":"Registros"})
        fig=px.bar(events_daily,x="Fecha",y="Registros",color="Categoría",title="Clasificaciones en la muestra a lo largo del tiempo")
        fig.update_layout(margin=dict(l=10,r=10,t=50,b=10),height=300)
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.caption("No hay reportes de otras categorías en el intervalo disponible.")
    st.caption("Categorías predichas por un modelo Transformer sobre textos simulados. Los conteos no equivalen a tasas de incidentes ni permiten medir la siniestralidad real.")

with tab_llm:
    st.subheader("Registro histórico de recomendaciones de Gemini")
    st.write("Recomendaciones registradas en las inspecciones y utilizadas para orientar verificaciones presenciales. Se muestran según los filtros de fecha y supervisor del menú lateral.")
    if insp_view.empty:
        st.warning("No hay recomendaciones para los filtros seleccionados.")
    else:
        if "recomendacion" in insp_view.columns:
            out=insp_view.copy().sort_values("fecha",ascending=False)
            cols=[c for c in ["fecha","supervisor","prioridad","diagnostico","recomendacion","justificacion","estado_revision"] if c in out.columns]
            st.dataframe(out[cols],hide_index=True,use_container_width=True,height=440)
            st.caption(f"{len(out)} registros de inspección en la selección. Esta tabla incluye recomendaciones por inspección; las recomendaciones del cierre diario enviadas por Gmail aún no se almacenan en esta instantánea.")
        else:
            st.info("No se encontró la columna de recomendaciones en el archivo de inspecciones.")

st.divider()
st.caption("Proyecto académico · IA generativa para la gestión industrial. Requiere supervisión humana. Datos de prueba anonimizados; el panel no utiliza cámaras ni datos en tiempo real.")
