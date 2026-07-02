"""
app.py — Interfaz Streamlit para Multi-Agent B2B Prospector

Uso:
    streamlit run app.py

Deploy:
    1. Push al repo de GitHub (ya existente).
    2. Conectar en streamlit.io/cloud → seleccionar repo → main file: app.py
    3. Agregar secrets en Streamlit Cloud (Settings → Secrets):
       GEMINI_API_KEY = "..."
       GOOGLE_MAPS_API_KEY = "..."
       HUNTER_API_KEY = "..."
       HUBSPOT_ACCESS_TOKEN = "..."
"""
import asyncio
import os
import pandas as pd
import streamlit as st

from main import build_graph
from state import LeadGenerationTarget, AgentState
from integrations.hubspot import push_leads_to_hubspot

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AIO Strategy — Prospector",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inyectar secrets de Streamlit Cloud a variables de entorno (solo si existe secrets.toml)
try:
    for key in ["GEMINI_API_KEY", "GOOGLE_MAPS_API_KEY", "HUNTER_API_KEY", "HUBSPOT_ACCESS_TOKEN"]:
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except Exception:
    pass  # Local sin secrets.toml — usa variables de entorno del sistema o modo mock

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🏭 Multi-Agent B2B Prospector")
st.caption("AIO Strategy · Prospección automatizada para PyMEs del Bajío")
st.divider()

# ---------------------------------------------------------------------------
# Sidebar — Criterios de búsqueda
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Criterios de Prospección")

    industry = st.text_input(
        "Industria",
        value="manufactura metalmecánica",
        help="Sector industrial a prospectar.",
    )
    region = st.text_input(
        "Región",
        value="Querétaro",
        help="Ciudad o zona geográfica.",
    )
    pain_point = st.text_area(
        "Pain Point",
        value="automatización de procesos de soldadura y control de calidad en línea",
        help="Problema operativo que AIO Strategy resuelve.",
        height=100,
    )
    output_type = st.selectbox(
        "Tipo de output",
        options=["both", "report_only", "outreach_only"],
        format_func=lambda x: {
            "both":          "Leads + Outreach",
            "report_only":   "Solo Leads (sin outreach)",
            "outreach_only": "Solo Outreach (sin búsqueda)",
        }[x],
    )

    st.divider()
    run_btn = st.button("🚀 Iniciar Prospección", type="primary", width='stretch')

    st.divider()
    st.caption("**API Keys activas**")
    for key, label in [
        ("GEMINI_API_KEY",        "Gemini (Copywriter)"),
        ("GOOGLE_MAPS_API_KEY",   "Google Maps"),
        ("HUNTER_API_KEY",        "Hunter.io"),
        ("HUBSPOT_ACCESS_TOKEN",  "HubSpot"),
    ]:
        icon = "🟢" if os.getenv(key) else "🔴"
        st.caption(f"{icon} {label}")

# ---------------------------------------------------------------------------
# Lógica de ejecución
# ---------------------------------------------------------------------------

def _run_pipeline(industry, region, pain_point, output_type) -> AgentState:
    criteria = LeadGenerationTarget(
        industry=industry,
        region=region,
        pain_point=pain_point,
        output_type=output_type,
    )
    initial_state: AgentState = {
        "target_criteria":  criteria,
        "next_step":        "",
        "plan_logs":        [],
        "leads":            [],
        "outreach_drafts":  {},
        "search_attempts":  0,
        "error_message":    None,
    }
    app = build_graph()
    return asyncio.run(app.ainvoke(initial_state))


if run_btn:
    with st.spinner("Buscando empresas, enriqueciendo contactos y generando outreach..."):
        try:
            result = _run_pipeline(industry, region, pain_point, output_type)
            st.session_state["result"] = result
            # Inicializar drafts editables con los generados
            st.session_state["edited_drafts"] = dict(result.get("outreach_drafts", {}))
            # Auto-push a HubSpot al finalizar pipeline
            if os.getenv("HUBSPOT_ACCESS_TOKEN") and result.get("leads"):
                pushed = push_leads_to_hubspot(
                    result["leads"], result.get("outreach_drafts", {})
                )
                st.session_state["hubspot_pushed"] = pushed
        except Exception as e:
            st.error(f"Error al ejecutar el pipeline: {e}")
            st.stop()

# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------

if "result" in st.session_state:
    result: AgentState = st.session_state["result"]

    # --- Métricas ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Leads calificados",   len(result["leads"]))
    col2.metric("Outreach generados",  len(result.get("outreach_drafts", {})))
    col3.metric("Decisiones Planner",  len(result["plan_logs"]))

    if st.session_state.get("hubspot_pushed"):
            pushed = st.session_state["hubspot_pushed"]
            st.success(f"✅ HubSpot: {len(pushed)} contacto(s) sincronizados — {', '.join(pushed.keys())}")

    if result.get("error_message"):
        st.warning(f"⚠️ {result['error_message']}")

    st.divider()

    # --- Tabs ---
    tab_leads, tab_outreach, tab_audit = st.tabs(["📋 Leads", "✉️ Outreach Drafts", "🔍 Audit Log"])

    # TAB 1 — LEADS
    with tab_leads:
        leads = result["leads"]
        if not leads:
            st.info("No se encontraron leads calificados con los criterios actuales.")
        else:
            df = pd.DataFrame(leads).rename(columns={
                "company_name":        "Empresa",
                "website":             "Web",
                "estimated_employees": "Empleados",
                "detected_signals":    "Señales detectadas",
                "contact_name":        "Contacto",
                "contact_role":        "Puesto",
                "contact_email":       "Email",
                "linkedin_profile":    "LinkedIn",
            })
            st.dataframe(df, width='stretch', hide_index=True)

            # Descarga CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Descargar CSV",
                data=csv,
                file_name="leads_aio_strategy.csv",
                mime="text/csv",
            )

    # TAB 2 — OUTREACH DRAFTS
    with tab_outreach:
        drafts = st.session_state.get("edited_drafts", {})

        if not drafts:
            st.info("No hay outreach generados (output_type=report_only o pipeline sin leads).")
        else:
            st.caption("Los mensajes son editables antes de exportar a HubSpot.")

            for company in drafts:
                with st.expander(f"📨 {company}", expanded=True):
                    st.session_state["edited_drafts"][company] = st.text_area(
                        label="Mensaje",
                        value=drafts[company],
                        height=220,
                        key=f"draft_{company}",
                        label_visibility="collapsed",
                    )

            st.divider()

            hubspot_btn = st.button("📤 Exportar a HubSpot", type="primary")
            if hubspot_btn:
                if not os.getenv("HUBSPOT_ACCESS_TOKEN"):
                    st.warning("HUBSPOT_ACCESS_TOKEN no configurado. Agrega la clave en Secrets.")
                else:
                    with st.spinner("Exportando a HubSpot..."):
                        edited = st.session_state.get("edited_drafts", drafts)
                        pushed = push_leads_to_hubspot(result["leads"], edited)
                    if pushed:
                        st.success(f"✅ {len(pushed)} contacto(s) exportados a HubSpot.")
                        for company, cid in pushed.items():
                            st.caption(f"• {company} → ID `{cid}`")
                    else:
                        st.warning("Ningún lead fue exportado. Revisa los logs en la consola.")

    # TAB 3 — AUDIT LOG
    with tab_audit:
        st.caption("Cada línea es una decisión del Planner Supervisor.")
        for i, log in enumerate(result["plan_logs"], 1):
            st.write(f"**[{i}]** {log}")
