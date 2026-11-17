"""Dashboard EPP | V5: inspecciones en Google Sheets con respaldo CSV.

La hoja Inspecciones es la fuente primaria cuando se configura en Streamlit Secrets.
Pronósticos y Transformer mantienen resultados de experimentos en CSV.
No se infieren zonas inexistentes ni se ejecutan modelos en este tablero.
"""
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Centro de control EPP", page_icon="🦺", layout="wide", initial_sidebar_state="expanded")
BASE = Path(__file__).resolve().parent / "data"
NAVY, BLUE, CYAN, AMBER, RED, MUTE = "#142943", "#2B66A2", "#14A4AC", "#D99B41", "#C45259", "#687789"
PALETTE = {"Alta": RED, "Media": AMBER, "Baja": BLUE}
VERSION = "V5 · INSPECCIONES DESDE GOOGLE SHEETS"
# Fecha local de Chile: Streamlit Community Cloud puede estar configurado en UTC.
HOY_CHILE = datetime.now(ZoneInfo("America/Santiago")).date()
MANANA_CHILE = HOY_CHILE + timedelta(days=1)
CATEGORIES = {
    "sin_evento_reportado": "Sin evento reportado", "transporte": "Transporte",
    "contacto_objetos": "Contacto con objetos", "caidas": "Caídas",
    "exposicion_sustancias": "Exposición a sustancias",
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
html, body, [data-testid="stAppViewContainer"] {font-family:Manrope,Arial,sans-serif;}
[data-testid="stAppViewContainer"] {background:#F6F8FC;}
[data-testid="stSidebar"] {background:#EEF3F9;border-right:1px solid #DCE5EF;}
.block-container {max-width:1420px;padding-top:1.2rem;padding-bottom:4rem;}
h1,h2,h3 {color:#142943;letter-spacing:-.035em;}
[data-testid="stTabs"] button {font-size:15px;font-weight:700;padding:13px 17px;}
.hero {background:linear-gradient(112deg,#142943,#184D78 70%,#126A7C);border-radius:18px;
 padding:30px 36px 29px;color:white;box-shadow:0 10px 24px #14294322;margin-bottom:18px;}
.hero .eyebrow {color:#A6DBF0;font-size:11px;letter-spacing:2.5px;font-weight:800;}
.hero h1 {color:white!important;font-size:37px;margin:9px 0 7px!important;line-height:1.1;}
.hero .subtitle {color:#D9EBF4;font-size:14px;max-width:840px;line-height:1.7;}
.version {display:inline-block;background:#ffffff20;border:1px solid #ffffff30;border-radius:99px;
 font-size:11px;font-weight:750;padding:7px 11px;margin-top:14px;letter-spacing:1.1px;}
.kpi {background:#FFF;border-radius:15px;border:1px solid #DFE7F0;padding:19px 22px 16px;
 box-shadow:0 4px 16px #0E25450A;min-height:140px;}
.kpi .eyebrow {font-size:11px;text-transform:uppercase;color:#69798B;letter-spacing:1.1px;font-weight:800;}
.kpi .number {font-size:38px;font-weight:800;letter-spacing:-1.3px;color:#142943;margin:5px 0 2px;}
.kpi .detail {font-size:12px;color:#657589;line-height:1.4;}
.kpi.urgent {border-top:4px solid #C45259;}
.kpi.info {border-top:4px solid #14A4AC;}
.section-head {font-weight:800;font-size:17px;color:#142943;margin-bottom:3px;}
.help {color:#67798D;font-size:13px;margin-bottom:17px;}
.notice {padding:14px 18px;background:#E7F4F7;color:#28546A;border-radius:10px;
 border-left:4px solid #14A4AC;font-size:13px;line-height:1.7;margin:15px 0;}
.warn {padding:14px 18px;background:#FFF4E7;color:#77572F;border-radius:10px;
 border-left:4px solid #D99B41;font-size:13px;line-height:1.7;margin:15px 0;}
.empty {padding:25px;border:1px dashed #ADC3D3;border-radius:13px;color:#69798B;text-align:center;}
.footer {font-size:12px;color:#778397;border-top:1px solid #DAE4EE;margin-top:28px;padding-top:18px;}
</style>
""", unsafe_allow_html=True)


# Actualizar la página mientras está abierta. La consulta remota mantiene caché
# corta para evitar solicitudes innecesarias a Google Sheets.
st_autorefresh(interval=5 * 60 * 1000, key="actualizacion_inspecciones")


@st.cache_data(show_spinner=False)
def load_saved_data():
    """Copia de seguridad histórica + resultados simulados de otros modelos."""
    return (pd.read_csv(BASE / "inspecciones.csv"),
            pd.read_csv(BASE / "pronosticos.csv"),
            pd.read_csv(BASE / "transformer.csv"))


def has_gsheets_settings():
    """La URL y, si procede, las credenciales van en Streamlit Secrets."""
    try:
        return bool(st.secrets.get("connections", {}).get("gsheets", {}).get("spreadsheet"))
    except Exception:
        return False


def load_inspections(csv_backup):
    """Lee directamente la primera pestaña (gid=0) de la hoja original de n8n.

    En modo público se necesita acceso 'Cualquier persona con el enlace: Lector'.
    En modo privado se usa una cuenta de servicio configurada en Secrets.
    En ambos casos la aplicación solicita lectura solamente.
    """
    if not has_gsheets_settings():
        return csv_backup.copy(), "CSV de respaldo", "Conexión aún no configurada en Streamlit Secrets."

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # worksheet=0: primera hoja; coincide con la pestaña Inspecciones (gid=0)
        # del documento que ya usa el flujo n8n.
        datos = conn.read(worksheet=0, ttl=240)
        if not isinstance(datos, pd.DataFrame):
            raise ValueError("La lectura de Inspecciones no devolvió una tabla.")
        necesarios = {"supervisor", "prioridad", "trabajadores_detectados",
                      "requieren_revision", "recomendacion"}
        if not necesarios.issubset(datos.columns):
            raise ValueError("La hoja no contiene las columnas principales de Inspecciones.")
        if not ({"fecha_inspeccion", "fecha_local_inspeccion", "fecha"} & set(datos.columns)):
            raise ValueError("La hoja no contiene una fecha de inspección.")
        return datos, "Google Sheets (directo)", ""
    except Exception:
        # No mostrar detalles internos de autenticación al público.
        return csv_backup.copy(), "CSV de respaldo", (
            "No se pudo consultar Google Sheets. Comprueba permisos, Secrets y "
            "que la primera pestaña sea Inspecciones. Se mantiene la copia de respaldo."
        )


def zone_label(zone):
    """¡Nunca inferir el número de zona a partir de la descripción antigua!"""
    zone = str(zone).strip()
    if zone == "zona_1":
        return "Zona 1 · casco y chaleco"
    if zone == "zona_2":
        return "Zona 2 · calzado, guantes y lentes"
    return "Histórico sin zona homologada"


def prep_inspections(df):
    df = df.copy()
    if "fecha" not in df.columns:
        if "fecha_local_inspeccion" in df.columns:
            df["fecha"] = df["fecha_local_inspeccion"]
        elif "fecha_inspeccion" in df.columns:
            dt = pd.to_datetime(df["fecha_inspeccion"], errors="coerce", utc=True)
            df["fecha"] = dt.dt.tz_convert("America/Santiago").dt.strftime("%Y-%m-%d")
    if "zona_id" not in df.columns:
        df["zona_id"] = df.get("zona", "")
    if "zona_original" not in df.columns:
        df["zona_original"] = df["zona_id"]
    if "id_inspeccion" not in df.columns:
        df["id_inspeccion"] = df.get("registro", pd.Series(range(1,len(df)+1)))
    required = ["fecha","supervisor","prioridad","trabajadores_detectados","requieren_revision","recomendacion"]
    missing = [k for k in required if k not in df.columns]
    if missing:
        st.error("El CSV de inspecciones no contiene: " + ", ".join(missing))
        st.stop()
    # Conservar los nombres tal como figuran en la fuente; no atribuir alias antiguos.
    df["supervisor"] = df["supervisor"].fillna("Sin supervisor").astype(str).str.strip()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"]).copy()
    df["zona_id"] = df["zona_id"].astype(str).str.strip().apply(
        lambda z: z if z in ("zona_1","zona_2") else "sin_homologar"
    )
    df["zona_etiqueta"] = df["zona_id"].apply(zone_label)
    for col in ("trabajadores_detectados","requieren_revision"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(lower=0).astype(int)
    for col in ("prioridad","estado_revision","diagnostico","recomendacion","justificacion"):
        if col not in df.columns: df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["prioridad"] = df["prioridad"].str.capitalize()
    return df


def prep_forecasts(df):
    df = df.copy()
    req = ["fecha_pronostico", "zona_id", "modelo", "trabajadores_revision_estimados"]
    if any(k not in df.columns for k in req):
        st.error("Faltan columnas en pronosticos.csv")
        st.stop()
    df["fecha_pronostico"] = pd.to_datetime(df["fecha_pronostico"], errors="coerce")
    df["trabajadores_revision_estimados"] = pd.to_numeric(df["trabajadores_revision_estimados"], errors="coerce")
    df = df.dropna(subset=["fecha_pronostico","trabajadores_revision_estimados"])
    df["zona_etiqueta"] = df["zona_id"].apply(zone_label)
    return df


def prep_transformer(df):
    df = df.copy()
    req = ["fecha", "zona_id", "categoria_predicha"]
    if any(k not in df.columns for k in req):
        st.error("Faltan columnas en transformer.csv")
        st.stop()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"])
    df["categoria"] = df["categoria_predicha"].map(CATEGORIES).fillna(df["categoria_predicha"].astype(str))
    df["zona_etiqueta"] = df["zona_id"].apply(zone_label)
    return df


def figure_style(fig, height=340):
    fig.update_layout(template="plotly_white", height=height,
                      font=dict(family="Manrope,Arial,sans-serif",size=12,color="#33475A"),
                      margin=dict(l=5,r=15,t=20,b=20),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h",y=1.12,x=0,title_text=""),
                      hovermode="closest")
    fig.update_yaxes(gridcolor="#E6EDF3",zerolinecolor="#E6EDF3")
    fig.update_xaxes(gridcolor="#EEF3F7")
    return fig


def kpi(label, number, detail, kind=""):
    return (f'<div class="kpi {kind}"><div class="eyebrow">{escape(label)}</div>'
            f'<div class="number">{escape(str(number))}</div>'
            f'<div class="detail">{escape(detail)}</div></div>')


csv_i, raw_p, raw_t = load_saved_data()
raw_i, fuente_inspecciones, error_fuente = load_inspections(csv_i)
i = prep_inspections(raw_i)
p = prep_forecasts(raw_p)
t = prep_transformer(raw_t)

# Los filtros SOLO afectan los resultados históricos de inspecciones.
# Los modelos simulados se presentan por zona/fecha por separado.
st.sidebar.markdown("### 🦺 Monitoreo EPP")
st.sidebar.caption("Panel de supervisión · Hito 2")
st.sidebar.divider()
st.sidebar.markdown("**Filtros de inspección**")
people = sorted(i["supervisor"].unique().tolist())
selected_people = st.sidebar.multiselect("Supervisor", people, default=people)

if not i.empty:
    min_d, max_d = i["fecha"].min().date(), i["fecha"].max().date()
    # Si el usuario tenía seleccionado el último día disponible, incluir las
    # nuevas fechas automáticamente sin perder otros filtros elegidos.
    prev_max_d = st.session_state.get("_inspecciones_max_fecha")
    if "periodo_inspecciones" not in st.session_state:
        st.session_state["periodo_inspecciones"] = (min_d, max_d)
    elif prev_max_d is not None and max_d > prev_max_d:
        current = st.session_state["periodo_inspecciones"]
        if isinstance(current, (tuple, list)) and len(current) == 2 and current[1] >= prev_max_d:
            st.session_state["periodo_inspecciones"] = (current[0], max_d)
    st.session_state["_inspecciones_max_fecha"] = max_d
    period = st.sidebar.date_input("Período", min_value=min_d, max_value=max_d,
                                   key="periodo_inspecciones")
    if isinstance(period, (tuple, list)) and len(period) == 2:
        date_a, date_b = period
    else:
        date_a, date_b = min_d, max_d
else:
    date_a = date_b = HOY_CHILE

# Las zonas del proyecto son únicamente Zona 1 y Zona 2.
# Los datos antiguos no se eliminan: pueden incluirse opcionalmente en la vista.
zone_options = ["Zona 1 · casco y chaleco", "Zona 2 · calzado, guantes y lentes"]
selected_zone = st.sidebar.multiselect("Zona", zone_options, default=zone_options)
incluir_historicos = st.sidebar.checkbox(
    "Incluir registros antiguos sin zona identificada", value=False,
    help="Conserva los registros de prueba antiguos, pero no los asigna a Zona 1 ni Zona 2."
)
selected_priority = st.sidebar.multiselect("Prioridad", ["Alta", "Media", "Baja"], default=["Alta", "Media", "Baja"])
mascara_zona = i["zona_etiqueta"].isin(selected_zone)
if incluir_historicos:
    mascara_zona = mascara_zona | i["zona_id"].eq("sin_homologar")
subset = i[(i["supervisor"].isin(selected_people)) &
           (i["fecha"].dt.date >= date_a) & (i["fecha"].dt.date <= date_b) &
           mascara_zona &
           (i["prioridad"].isin(selected_priority))].copy()

st.sidebar.divider()
st.sidebar.caption(f"Fuente de inspecciones: {fuente_inspecciones}.")
if fuente_inspecciones == "Google Sheets (directo)":
    st.sidebar.caption("Se consulta de nuevo automáticamente cada 5 minutos mientras el tablero esté abierto.")
else:
    st.sidebar.warning(error_fuente)
if st.sidebar.button("Actualizar datos ahora", help="Vacía la caché para volver a consultar la hoja"):
    st.cache_data.clear()
    st.rerun()
with st.sidebar.expander("Origen y actualización"):
    st.caption("Inspecciones y recomendaciones Gemini: hoja Inspecciones de Google Sheets, si está conectada. Pronósticos y Transformer: resultados de prueba en CSV.")
    st.info("Para habilitar la conexión, configura el enlace y los permisos en Streamlit Secrets. Si la conexión falla se usa el CSV de respaldo; ese respaldo puede contener registros antiguos.")

st.markdown(f'''<div class="hero"><div class="eyebrow">SEGURIDAD INDUSTRIAL · SISTEMA DE APOYO A LA DECISIÓN</div>
<h1>Centro de control de EPP</h1><div class="subtitle">Inspecciones con YOLO + recomendaciones de Gemini + planificación con LSTM / Holt-Winters + clasificación de reportes con Transformer.</div>
<div class="version">{VERSION}</div></div>''',unsafe_allow_html=True)

old = int((i["zona_id"]=="sin_homologar").sum())
st.markdown(f'''<div class="notice"><strong>Fuente: {escape(fuente_inspecciones)}.</strong> {len(i)} inspecciones históricas · {len(p)} pronósticos · {len(t)} reportes Transformer. 
Los <strong>{old} registros sin zona_1/zona_2 explícita</strong> se muestran separados. Los valores de zona se leen de la fuente sin asignarlos por suposición. 
Los modelos predictivos utilizan datos simulados y no están ejecutándose en vivo en este panel.</div>''',unsafe_allow_html=True)

n_high = int((subset["prioridad"]=="Alta").sum())
need = int(subset["requieren_revision"].sum())
rows = st.columns(4,gap="medium")
for column, info in zip(rows,[
    ("Inspecciones",len(subset),"Registros del período seleccionado","info"),
    ("Trabajadores detectados",int(subset["trabajadores_detectados"].sum()),"Observaciones del modelo de visión",""),
    ("Revisiones potenciales",need,"Suma de trabajadores con EPP requerido no confirmado por inspección (no necesariamente únicos)","info"),
    ("Prioridad alta",n_high,"Inspecciones con revisión más urgente","urgent")]):
    with column:
        st.markdown(kpi(*info),unsafe_allow_html=True)

section_ops, section_forecasts, section_transformer, section_gemini = st.tabs([
    "01 · Operación", "02 · Pronósticos", "03 · Transformer", "04 · Gemini"
])

with section_ops:
    st.write("")
    st.markdown('<div class="section-head">Seguimiento operacional</div><p class="help">Los filtros laterales aplican a esta vista y al historial Gemini.</p>',unsafe_allow_html=True)
    if subset.empty:
        st.warning("Sin inspecciones para los filtros elegidos.")
    else:
        a,b = st.columns([1.4,1],gap="large")
        with a:
            st.markdown("##### Actividad diaria")
            daily = subset.groupby(subset["fecha"].dt.date).agg(
                Inspecciones=("id_inspeccion","size"),
                **{"Revisiones potenciales":("requieren_revision","sum")}
            ).reset_index().rename(columns={"fecha":"Fecha"})
            flat = daily.melt(id_vars="Fecha",value_vars=["Inspecciones","Revisiones potenciales"],
                              var_name="Indicador",value_name="Cantidad")
            fig=px.bar(flat,x="Fecha",y="Cantidad",color="Indicador",barmode="group",
                       color_discrete_map={"Inspecciones":BLUE,"Revisiones potenciales":CYAN})
            fig.update_layout(bargap=.3)
            st.plotly_chart(figure_style(fig,355),use_container_width=True)
        with b:
            st.markdown("##### Prioridad por supervisor")
            agg = subset.groupby(["supervisor","prioridad"]).size().reset_index(name="Inspecciones")
            fig=px.bar(agg,x="Inspecciones",y="supervisor",color="prioridad",orientation="h",barmode="stack",
                       category_orders={"prioridad":["Alta","Media","Baja"]},
                       color_discrete_map=PALETTE, labels={"supervisor":"Supervisor","prioridad":"Prioridad"})
            st.plotly_chart(figure_style(fig,355),use_container_width=True)

        st.markdown("##### Inspecciones que necesitan atención")
        # Orden clínico/operacional de prioridad, no orden alfabético.
        urgent = subset[subset["requieren_revision"] > 0].copy()
        urgent["_orden_prioridad"] = urgent["prioridad"].map({"Alta": 0, "Media": 1, "Baja": 2}).fillna(3)
        urgent = urgent.sort_values(["_orden_prioridad", "fecha"], ascending=[True, False])
        if urgent.empty:
            st.info("No hay casos con EPP requerido no confirmado en la selección.")
        else:
            urgent["Fecha"] = urgent["fecha"].dt.strftime("%d/%m/%Y")
            view = urgent[["Fecha","supervisor","zona_etiqueta","trabajadores_detectados","requieren_revision","prioridad","recomendacion"]].head(12)
            st.dataframe(view.rename(columns={"supervisor":"Supervisor","zona_etiqueta":"Zona",
                "trabajadores_detectados":"Detectados","requieren_revision":"Revisiones potenciales",
                "prioridad":"Prioridad","recomendacion":"Acción sugerida"}),
                use_container_width=True,hide_index=True)
        st.markdown('''<div class="warn"><strong>Interpretación:</strong> «Revisiones potenciales» suma, por inspección, los trabajadores para quienes YOLO no confirmó visualmente algún EPP requerido. No cuenta EPP ni identifica personas únicas y no prueba infracciones. En n8n, la revisión humana se registra inicialmente como pendiente, sin un mecanismo automático verificado de cierre.</div>''',unsafe_allow_html=True)
        with st.expander("Ver detalle de todas las inspecciones"):
            table=subset.sort_values("fecha",ascending=False)[["fecha","supervisor","zona_etiqueta","zona_original","trabajadores_detectados","requieren_revision","prioridad","estado_revision"]]
            st.dataframe(table,hide_index=True,use_container_width=True)

with section_forecasts:
    st.write("")
    st.markdown('<div class="section-head">Planificación de la jornada siguiente</div><p class="help">Resultados previamente calculados; muestran estimaciones, no hallazgos de inspección.</p>',unsafe_allow_html=True)
    if p.empty:
        st.warning("Sin pronósticos disponibles.")
    else:
        days=sorted(p["fecha_pronostico"].dt.date.unique().tolist())
        # Mostrar primero mañana según America/Santiago; usar otra fecha si falta ese dato.
        upcoming=[d for d in days if d>=MANANA_CHILE]
        default_day = MANANA_CHILE if MANANA_CHILE in days else (upcoming[0] if upcoming else days[-1])
        chosen_day=st.select_slider("Fecha de planificación",options=days,
                                    value=default_day,
                                    format_func=lambda d:d.strftime("%d/%m/%Y"))
        st.caption(
            f"Fecha seleccionada: {chosen_day.strftime('%d/%m/%Y')} · "
            f"Horizonte disponible: {days[0].strftime('%d/%m/%Y')} al {days[-1].strftime('%d/%m/%Y')}."
        )
        if chosen_day != MANANA_CHILE:
            st.caption(f"Esta fecha no corresponde a mañana ({MANANA_CHILE.strftime('%d/%m/%Y')}).")
        snap=p[p["fecha_pronostico"].dt.date==chosen_day].sort_values("zona_id")
        if len(snap):
            c1,c2=st.columns(2,gap="medium")
            for col,(_,r) in zip([c1,c2],snap.iterrows()):
                with col:
                    # Mostrar decimales permite apreciar cambios menores a una persona.
                    st.markdown(kpi(str(r['zona_etiqueta']),f"≈ {r['trabajadores_revision_estimados']:.2f}",
                                     f"Estimación para {chosen_day.strftime('%d/%m/%Y')} · {r['modelo']}","info"),
                                     unsafe_allow_html=True)
        st.markdown('<div class="notice"><strong>Decisión de gestión:</strong> usar estas estimaciones como referencia para planificar rondas, personal y tiempos de verificación. LSTM corresponde a la Zona 1 y Holt-Winters a la Zona 2. No es una comparación válida del riesgo relativo entre ambas zonas.</div>',unsafe_allow_html=True)
        fig=px.line(p,x="fecha_pronostico",y="trabajadores_revision_estimados",
                    color="zona_etiqueta",markers=True,
                    color_discrete_map={zone_label('zona_1'):CYAN,zone_label('zona_2'):BLUE},
                    labels={"fecha_pronostico":"Fecha","trabajadores_revision_estimados":"Trabajadores estimados","zona_etiqueta":"Zona"})
        fig.update_traces(line=dict(width=3),marker=dict(size=6))
        # Señalar sobre el gráfico completo la fecha movida en la barra.
        if not snap.empty:
            fig.add_scatter(
                x=snap["fecha_pronostico"],
                y=snap["trabajadores_revision_estimados"],
                mode="markers",
                marker=dict(size=15, symbol="diamond", color=AMBER),
                name="Fecha seleccionada",
                hovertemplate="%{x|%d/%m/%Y}: %{y:.2f} trabajadores<extra></extra>"
            )
        st.plotly_chart(figure_style(fig,400),use_container_width=True)
        st.caption("Pronósticos sobre datos simulados. No se deben confundir con trabajadores observados, incumplimientos o resultados individuales de un supervisor.")

with section_transformer:
    st.write("")
    st.markdown('<div class="section-head">Reportes de seguridad clasificados</div><p class="help">Transformer identifica categorías en reportes de prueba simulados, no incidentes observados hoy.</p>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    non=t["categoria_predicha"]!="sin_evento_reportado"
    a.metric("Reportes analizados",len(t))
    b.metric("Sin evento reportado",int((~non).sum()))
    c.metric("Otras categorías",int(non.sum()))
    show_all=st.toggle("Incluir 'Sin evento reportado' en el gráfico",value=False)
    plot_t=t if show_all else t[non]
    counts=plot_t.groupby(["zona_etiqueta","categoria"]).size().reset_index(name="Reportes")
    if not counts.empty:
        fig=px.bar(counts,x="Reportes",y="categoria",color="zona_etiqueta",orientation="h",barmode="group",
                   color_discrete_map={zone_label('zona_1'):CYAN,zone_label('zona_2'):BLUE},
                   labels={"categoria":"Categoría","zona_etiqueta":"Zona"},text="Reportes")
        fig.update_traces(textposition="outside")
        st.plotly_chart(figure_style(fig,390),use_container_width=True)
    st.markdown('<div class="notice"><strong>Lectura correcta:</strong> las categorías permiten organizar el contenido de reportes. Sus cantidades son frecuencias de una muestra artificial, no tasas de accidentes ni una medición del riesgo real.</div>',unsafe_allow_html=True)
    with st.expander("Distribución completa por zona"):
        st.dataframe(t.groupby(["zona_etiqueta","categoria"]).size().reset_index(name="Reportes"),hide_index=True,use_container_width=True)

with section_gemini:
    st.write("")
    st.markdown('<div class="section-head">Historial de recomendaciones de Gemini</div><p class="help">Diagnósticos y acciones generadas en inspecciones individuales; sujetos a verificación por el supervisor.</p>',unsafe_allow_html=True)
    if subset.empty:
        st.info("No hay recomendaciones para estos filtros.")
    else:
        records=subset.sort_values(["fecha","id_inspeccion"],ascending=False)
        st.caption(f"{len(records)} recomendaciones disponibles con los filtros activos")
        num=st.select_slider("Cantidad de recomendaciones visibles",options=[5,10,20,40,60],value=10)
        for _,r in records.head(num).iterrows():
            header=f"{r['fecha'].strftime('%d/%m/%Y')} · {r['supervisor']} · {r['prioridad']} · {zone_label(r['zona_id'])}"
            with st.expander(header):
                st.markdown("**Diagnóstico:** " + escape(r["diagnostico"]))
                st.markdown("**Acción recomendada:** " + escape(r["recomendacion"]))
                st.markdown("**Justificación:** " + escape(r["justificacion"]))
                st.caption("Registro de prueba. Acción sujeta a validación humana.")
        st.download_button("Descargar historial filtrado (CSV)",
                           records[["fecha","supervisor","zona_id","prioridad","diagnostico","recomendacion","justificacion"]].to_csv(index=False).encode("utf-8-sig"),
                           file_name="historial_recomendaciones_epp.csv",mime="text/csv")
        st.caption("Las recomendaciones del cierre diario se notifican por Gmail; el flujo actual no las conserva en una hoja histórica.")

st.markdown('''<div class="footer">Dashboard EPP · Hito 2 · V5. Las inspecciones se leen desde Google Sheets si está conectado; si no, desde el respaldo CSV. Pronósticos y Transformer son resultados de prueba simulados. Los resultados requieren revisión humana.</div>''',unsafe_allow_html=True)
