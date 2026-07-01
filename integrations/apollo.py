"""
integrations/apollo.py — Apollo.io People Match API

Contrato público:
    enrich_with_apollo(domain) -> Dict

Dict devuelto:
    {
        "name":         str | None,   # "Ing. Carlos Mendoza"
        "title":        str | None,   # "Gerente de Planta"
        "email":        str | None,   # "c.mendoza@empresa.mx"
        "linkedin_url": str | None,   # "https://linkedin.com/in/..."
        "headcount":    int,          # empleados (0 si no disponible)
    }

Este contrato es idéntico al mock `_enrich_with_apollo()` en agents/lead_finder.py.
Reemplazar el import allí para activar la integración real.

Endpoint de Apollo:
    POST https://api.apollo.io/v1/people/match
    Headers: { "x-api-key": APOLLO_API_KEY, "Content-Type": "application/json" }
    Body:    { "domain": domain, "titles": DECISION_MAKER_TITLES }

Documentación:
    https://apolloio.github.io/apollo-api-docs/#people-match

TODO para Claude Code:
    [ ] Implementar enrich_with_apollo() con requests.post a /v1/people/match
    [ ] Filtrar por DECISION_MAKER_TITLES — solo tomadores de decisión de Ops/Ingeniería
    [ ] Parsear el response: person.name, person.title, person.email, person.linkedin_url
    [ ] Manejar 404 / empty response (empresa no encontrada en Apollo) → devolver dict vacío
    [ ] Manejar rate limit de Apollo (429) con retry exponencial
"""
import os
import requests
from typing import Dict, Any

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
_PEOPLE_MATCH_URL = "https://api.apollo.io/v1/people/match"

# Títulos de tomadores de decisión relevantes para automatización industrial
DECISION_MAKER_TITLES = [
    "Gerente de Planta",
    "Director de Operaciones",
    "Gerente de Manufactura",
    "Gerente de Ingeniería",
    "Director de Producción",
    "Plant Manager",
    "Operations Director",
    "Manufacturing Engineer",
    "Dueño",
    "Director General",
]


def enrich_with_apollo(domain: str) -> Dict[str, Any]:
    """
    Busca el tomador de decisión de una empresa por dominio web.

    Contrato de salida (igual que el mock en agents/lead_finder.py):
        {
            "name":         str | None,
            "title":        str | None,
            "email":        str | None,
            "linkedin_url": str | None,
            "headcount":    int,
        }

    Args:
        domain: Dominio de la empresa (ej. "metalurgicamarques.mx")

    Returns:
        Dict con datos del contacto. Si Apollo no encuentra nada,
        devuelve el dict con todos los campos en None y headcount=0.

    TODO: implementar con requests.post a _PEOPLE_MATCH_URL
    """
    raise NotImplementedError(
        "Implementar enrich_with_apollo() con POST a Apollo /v1/people/match. "
        "Ver: https://apolloio.github.io/apollo-api-docs/#people-match"
    )
