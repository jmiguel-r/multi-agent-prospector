"""
agents/lead_finder.py — Lead Finder Node

Pipeline de enriquecimiento en cascada con estrategia "Zero Cost":

    [Google Maps API]
        ↓  empresa física + dominio + snippet
    [Pre-Hunter: scraping público]
        ↓  si hay correo público → usarlo directamente (0 créditos Hunter)
    [Nombre del contacto: búsqueda web / LLM]
        ↓  solo si el lead califica y no hay correo público
    [Hunter.io Email Finder]
        ↓  correo corporativo del tomador de decisión (1 crédito)
    [Filtro de calidad]
        → descarta leads sin email ni LinkedIn

Los mocks están claramente marcados para reemplazar con integrations/
cuando se activen las API keys reales.
"""
from typing import Dict, Any, List, Optional
from state import AgentState, LeadInfo
from integrations.google_maps import search_companies
from integrations.hunter import (
    find_public_contact,
    enrich_with_hunter,
    split_name,
)



# ---------------------------------------------------------------------------
# MOCK — Nombre del tomador de decisión (fuente: búsqueda web / LLM)
# En producción: usar Google Custom Search API o Tavily con query:
#   f"Gerente Planta OR Director Operaciones site:{domain}"
# ---------------------------------------------------------------------------

_CONTACT_NAME_DB: Dict[str, Optional[str]] = {
    "metalurgicamarques.mx": "Carlos Mendoza",
    "maquinadosbajio.com":   "Alejandro Ruiz Torres",
    "aceroscen.mx":          None,  # no se encontró nombre público
}

_CONTACT_ROLE_DB: Dict[str, Optional[str]] = {
    "metalurgicamarques.mx": "Gerente de Planta e Ingeniería",
    "maquinadosbajio.com":   "Director de Operaciones",
    "aceroscen.mx":          None,
}


def _find_contact_name(domain: str) -> tuple[Optional[str], Optional[str]]:
    """
    Mock: devuelve (nombre_completo, rol) del tomador de decisión.
    En producción: búsqueda web con query f"Gerente Planta site:{domain}"
    o llamada a un LLM con tool de búsqueda.
    """
    return _CONTACT_NAME_DB.get(domain), _CONTACT_ROLE_DB.get(domain)


# ---------------------------------------------------------------------------
# MOCK — Hunter.io (solo activo en tests sin HUNTER_API_KEY)
# ---------------------------------------------------------------------------

_HUNTER_MOCK_DB: Dict[str, Dict[str, Any]] = {
    "metalurgicamarques.mx": {
        "email":      "c.mendoza@metalurgicamarques.mx",
        "confidence": 92,
        "linkedin":   "https://linkedin.com/in/carlos-mendoza-qro",
    },
    "maquinadosbajio.com": {
        "email":      "aruiz@maquinadosbajio.com",
        "confidence": 85,
        "linkedin":   "https://linkedin.com/in/alejandro-ruiz-bajio",
    },
}


def _enrich_mock(domain: str) -> Dict[str, Any]:
    """Fallback mock cuando HUNTER_API_KEY no está disponible."""
    return _HUNTER_MOCK_DB.get(domain, {"email": None, "confidence": 0, "linkedin": None})


# ---------------------------------------------------------------------------
# NODO PRINCIPAL
# ---------------------------------------------------------------------------

def lead_finder_node(state: AgentState) -> Dict[str, Any]:
    print("--- EJECUTANDO: LEAD FINDER NODE (Maps + Pre-Hunter + Hunter.io) ---")

    import os
    criteria    = state["target_criteria"]
    use_mock    = not bool(os.getenv("HUNTER_API_KEY"))

    # PASO 1 — Descubrir empresas en la región
    raw_results = search_companies(criteria.industry, criteria.region)

    enriched_leads: List[LeadInfo] = []

    for company in raw_results:
        domain  = company["website"]
        snippet = company["snippet"]

        # PASO 2 — Pre-Hunter: buscar correo público (0 créditos)
        public_email = find_public_contact(domain, snippet)
        hunter_result: Dict[str, Any] = {}

        # PASO 3 — Si no hay correo público, buscar el nombre del contacto
        #          y llamar a Hunter (1 crédito)
        full_name, role = _find_contact_name(domain)

        if not public_email and full_name:
            first, last = split_name(full_name)
            if first and last:
                if use_mock:
                    hunter_result = _enrich_mock(domain)
                else:
                    hunter_result = enrich_with_hunter(domain, first, last)

        # Resolver email final: público > Hunter (si confidence >= 70) > None
        final_email    = public_email
        final_linkedin = hunter_result.get("linkedin")

        if not final_email:
            if hunter_result.get("confidence", 0) >= 70:
                final_email = hunter_result.get("email")
            elif hunter_result.get("email"):
                # Confianza baja — guardar pero advertir
                print(f"  ⚠ Hunter: {domain} — email con baja confianza "
                      f"({hunter_result['confidence']}%), incluido con cautela.")
                final_email = hunter_result.get("email")

        # PASO 4 — Construir LeadInfo
        lead: LeadInfo = {
            "company_name":       company["title"],
            "website":            f"https://{domain}",
            "estimated_employees": 0,  # TODO: fuente adicional (Clearbit, LinkedIn)
            "detected_signals":   snippet,
            "contact_name":       full_name,
            "contact_role":       role,
            "contact_email":      final_email,
            "linkedin_profile":   final_linkedin,
        }

        # PASO 5 — Filtro de calidad
        if lead["contact_email"] or lead["linkedin_profile"]:
            enriched_leads.append(lead)
            print(f"  ✓ Lead calificado: {lead['company_name']} → "
                  f"{lead['contact_name']} <{lead['contact_email']}>")
        else:
            print(f"  ✗ Descartado (sin contacto): {lead['company_name']}")

    return {
        "leads":           enriched_leads,
        "search_attempts": state.get("search_attempts", 0) + 1,
    }
