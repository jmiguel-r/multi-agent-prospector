"""
copywriter.py — Copywriter Node.

Genera mensajes de prospección en frío estilo "ingeniero a ingeniero"
usando la técnica de Relevancia Contextual: no vende, señala una
ineficiencia real detectada en la planta del contacto.

Procesamiento concurrente: todas las llamadas a Gemini se lanzan en
paralelo con asyncio.gather — la latencia total ≈ la de una sola llamada,
independientemente del número de leads.

Requiere: GEMINI_API_KEY en variables de entorno.
Si no se detecta la clave, el nodo usa un template determinista de fallback
(útil para tests y demos sin acceso a internet).
"""
import os
import asyncio
from typing import Dict, Any, Optional

from state import AgentState


# ---------------------------------------------------------------------------
# GENERACIÓN — Una llamada asíncrona por lead
# ---------------------------------------------------------------------------

async def _generate_single_outreach(
    lead: Dict[str, Any],
    pain_point: str,
    use_mock: bool = False,
) -> tuple[str, str]:
    """Genera el copy para UN lead. Devuelve (company_name, mensaje)."""

    saludo = lead["contact_name"] or f"Equipo de Ingeniería de {lead['company_name']}"
    role_ctx = f"en su rol de {lead['contact_role']}" if lead.get("contact_role") else ""

    if use_mock:
        # Template determinista — no requiere API key
        message = (
            f"{saludo},\n\n"
            f"Le escribo tras revisar los indicadores de manufactura en plantas dedicadas a "
            f"{lead['detected_signals'].lower()} en la región de Querétaro. "
            f"Específicamente, {pain_point.lower()} es un desafío recurrente que impacta "
            f"directamente en los tiempos de ciclo y en el índice de scrap en líneas como la suya.\n\n"
            f"Actualmente apoyamos a plantas metalmecánicas en el Bajío a reducir estos desvíos "
            f"mediante integración modular de automatización de procesos. "
            f"¿Tiene sentido que le comparta una hoja técnica con casos de éxito "
            f"implementados en plantas similares en Querétaro?\n\n"
            f"Saludos, AIO Strategy"
        )
        return lead["company_name"], message

    # Llamada real a Gemini 2.5 Pro
    from google import genai
    from google.genai import types

    prompt = f"""
Eres un Ingeniero de Soluciones de Automatización Industrial Senior.
Redacta un mensaje de prospección en frío, técnico y de alta relevancia.

DATOS DEL CONTACTO:
- Nombre: {saludo}
- Puesto: {role_ctx}
- Empresa: {lead['company_name']}
- Contexto técnico detectado: {lead['detected_signals']}
- Problema a resolver: {pain_point}

REGLAS ESTRICTAS (Estilo "Ingeniero a Ingeniero"):
1. TONO: Profesional, pragmático. Sin adjetivos corporativos exagerados.
   Habla de procesos, scrap, tiempos de ciclo, uptime, repetibilidad.
2. ESTRUCTURA:
   - Saludo directo personalizado.
   - Referencia inmediata al contexto técnico de su planta.
   - Planteamiento del problema y su impacto operativo.
   - CTA de bajo impacto (compartir hoja técnica, no pedir reunión de 30 min).
3. EXTENSIÓN: Máximo 3 párrafos cortos.
4. IDIOMA: Español de México, industrial y profesional.
"""

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.6,
                max_output_tokens=800,
            ),
        ),
    )
    return lead["company_name"], response.text


# ---------------------------------------------------------------------------
# NODO PRINCIPAL (async — compatible con app.ainvoke de LangGraph)
# ---------------------------------------------------------------------------

async def copywriter_node(state: AgentState) -> Dict[str, Any]:
    print("--- EJECUTANDO: COPYWRITER NODE (procesamiento concurrente) ---")

    leads      = state["leads"]
    pain_point = state["target_criteria"].pain_point
    use_mock   = not bool(os.getenv("GEMINI_API_KEY"))

    if not leads:
        print("  Sin leads en el estado — omitiendo generación.")
        return {"outreach_drafts": {}}

    if use_mock:
        print("  GEMINI_API_KEY no detectada → usando template de fallback.")

    # Lanzar todas las generaciones en paralelo
    tasks = [
        _generate_single_outreach(lead, pain_point, use_mock=use_mock)
        for lead in leads
    ]
    results = await asyncio.gather(*tasks)

    outreach_drafts = {company: message for company, message in results}

    print(f"  {len(outreach_drafts)} mensaje(s) generado(s).")
    return {"outreach_drafts": outreach_drafts}
