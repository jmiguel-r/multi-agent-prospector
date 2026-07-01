"""
planner.py — Nodo Supervisor (Planner Agent).

Implementación determinista: aplica el árbol de lógica directamente en Python
en vez de hacer una llamada LLM para el routing. Esto garantiza cero latencia
en las decisiones de control de flujo y eliminina el gasto de tokens en lógica
que no requiere razonamiento lingüístico.

Para extender a routing con LLM (cuando los criterios de decisión sean
ambiguos o requieran razonamiento sobre el contenido de los leads), reemplazar
el cuerpo de `_decide()` por una llamada a Gemini con structured output y
el system prompt del archivo diseño_planner_agent.md.
"""
from typing import Dict, Any

MAX_SEARCH_ATTEMPTS = 3  # guarda contra loop infinito si Lead Finder no encuentra nada


def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("--- EJECUTANDO: PLANNER NODE ---")

    leads           = state.get("leads", [])
    outreach_drafts = state.get("outreach_drafts", {})
    output_type     = state["target_criteria"].output_type
    attempts        = state.get("search_attempts", 0)

    next_step, reasoning = _decide(leads, outreach_drafts, output_type, attempts)

    print(f"  Planner → {next_step} | {reasoning}")

    return {
        "next_step":  next_step,
        "plan_logs":  [reasoning],
    }


def _decide(
    leads: list,
    outreach_drafts: dict,
    output_type: str,
    attempts: int,
) -> tuple[str, str]:
    """Árbol de lógica determinista — ver diseño_planner_agent.md Pieza 3."""

    # GUARDA DE SEGURIDAD: evita loop infinito si Lead Finder no encuentra nada
    if attempts >= MAX_SEARCH_ATTEMPTS and not leads:
        return (
            "END",
            f"Límite de búsquedas alcanzado ({MAX_SEARCH_ATTEMPTS} intentos) sin resultados. "
            "Verificar criterios de prospección o disponibilidad de APIs.",
        )

    # CASO 1: Solo outreach
    if output_type == "outreach_only":
        if not outreach_drafts:
            return "copywriter", "output_type=outreach_only, outreach_drafts vacío → redactar."
        return "END", "output_type=outreach_only, outreach_drafts completo → END."

    # CASO 2: Solo reporte
    if output_type == "report_only":
        if not leads:
            return "lead_finder", f"output_type=report_only, leads vacío (intento {attempts+1}) → buscar."
        return "END", f"output_type=report_only, {len(leads)} lead(s) encontrado(s) → END."

    # CASO 3: Flujo completo (default: "both")
    if not leads:
        return "lead_finder", f"output_type=both, leads vacío (intento {attempts+1}) → buscar empresas."
    if not outreach_drafts:
        return "copywriter", f"output_type=both, {len(leads)} lead(s) listos, outreach_drafts vacío → redactar."
    return "END", f"output_type=both, {len(leads)} lead(s) y {len(outreach_drafts)} draft(s) completos → END."
