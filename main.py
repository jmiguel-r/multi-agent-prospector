"""
main.py — Punto de entrada del Multi-Agent Prospector.

Ensambla el grafo LangGraph con patrón Supervisor puro:
  START → Planner → (Lead Finder | Copywriter | END)
                ↑______________|_______________|

Uso:
  python main.py                          # demo con mocks (sin API keys)
  GEMINI_API_KEY=xxx python main.py       # con generación real de Gemini
"""
import asyncio
import json
from langgraph.graph import StateGraph, START, END

from state import AgentState, LeadGenerationTarget
from planner import planner_node
from lead_finder import lead_finder_node
from copywriter import copywriter_node


# ---------------------------------------------------------------------------
# ROUTER — Lee next_step del estado y devuelve el nombre del nodo destino
# ---------------------------------------------------------------------------

def router(state: AgentState) -> str:
    return state["next_step"]


# ---------------------------------------------------------------------------
# BUILDER — Ensambla y compila el grafo
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(AgentState)

    # Registrar nodos
    graph.add_node("planner",     planner_node)
    graph.add_node("lead_finder", lead_finder_node)
    graph.add_node("copywriter",  copywriter_node)

    # Arista de entrada
    graph.add_edge(START, "planner")

    # Routing condicional desde el Supervisor
    graph.add_conditional_edges("planner", router, {
        "lead_finder": "lead_finder",
        "copywriter":  "copywriter",
        "END":         END,
    })

    # Todos los agentes regresan al Supervisor (patrón Supervisor puro)
    graph.add_edge("lead_finder", "planner")
    graph.add_edge("copywriter",  "planner")

    return graph.compile()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

async def main():
    # Criterio de prueba — AIO Strategy, Bajío real
    criteria = LeadGenerationTarget(
        industry="manufactura metalmecánica",
        region="Querétaro",
        pain_point="automatización de procesos de soldadura y control de calidad en línea",
        company_size_category="Pequeña",
        min_employees=15,
        max_employees=80,
        output_type="both",
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

    print("\n" + "="*60)
    print("   MULTI-AGENT PROSPECTOR — AIO Strategy")
    print("   Dominio: Manufactura metalmecánica, Querétaro")
    print("="*60 + "\n")

    final_state = await app.ainvoke(initial_state)

    # --------------- REPORTE FINAL ---------------
    print("\n" + "="*60)
    print("   RESULTADOS FINALES")
    print("="*60)

    print(f"\n📋 Leads calificados:   {len(final_state['leads'])}")
    print(f"✉️  Outreach generados: {len(final_state['outreach_drafts'])}")

    print("\n--- AUDIT LOG (Decisiones del Planner) ---")
    for i, log in enumerate(final_state["plan_logs"], 1):
        print(f"  [{i}] {log}")

    print("\n--- LEADS CALIFICADOS ---")
    for lead in final_state["leads"]:
        print(f"\n  🏭 {lead['company_name']}")
        print(f"     Web:      {lead['website']}")
        print(f"     Empleados: ~{lead['estimated_employees']}")
        print(f"     Contacto:  {lead.get('contact_name')} — {lead.get('contact_role')}")
        print(f"     Email:     {lead.get('contact_email')}")
        print(f"     LinkedIn:  {lead.get('linkedin_profile')}")
        print(f"     Señales:   {lead['detected_signals']}")

    print("\n--- OUTREACH DRAFTS ---")
    for company, message in final_state["outreach_drafts"].items():
        print(f"\n  📨 [{company}]")
        print("  " + "\n  ".join(message.splitlines()))

    if final_state.get("error_message"):
        print(f"\n⚠️  Error registrado: {final_state['error_message']}")

    return final_state


if __name__ == "__main__":
    asyncio.run(main())
