"""
integrations/google_maps.py — Google Maps Places API (New)

Contrato público:
    search_companies(industry, region, max_results) -> List[Dict]

Cada Dict devuelto tiene la forma:
    {
        "title":   str,   # nombre de la empresa
        "website": str,   # dominio (sin https://)
        "snippet": str,   # descripción del lugar
    }

Documentación:
    https://developers.google.com/maps/documentation/places/web-service/text-search
"""
import os
import re
from typing import List, Dict, Any

import requests

_TEXTSEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELD_MASK = "places.displayName,places.websiteUri,places.editorialSummary"
_HTTPS_PREFIX = re.compile(r"^https?://", re.IGNORECASE)


def search_companies(
    industry: str,
    region: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    Busca empresas físicas de una industria en una región usando Google Maps Places API (New).

    Contrato de salida (igual que el mock en agents/lead_finder.py):
        [
            {
                "title":   "Metalúrgica El Marqués S.A.",
                "website": "metalurgicamarques.mx",
                "snippet": "Taller de soldadura y estampado.",
            },
            ...
        ]

    Args:
        industry:    Sector a buscar (ej. "manufactura metalmecánica")
        region:      Región geográfica (ej. "Querétaro")
        max_results: Máximo de empresas a devolver (máx. 20 por límite de la API)

    Returns:
        Lista de dicts con title, website, snippet.
        Empresas sin website son descartadas (no se pueden enriquecer con Hunter).

    Raises:
        EnvironmentError: Si GOOGLE_MAPS_API_KEY no está definida.
        requests.HTTPError: Si la API responde con un error HTTP.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_MAPS_API_KEY no está definida en el entorno.")

    payload = {
        "textQuery": f"{industry} en {region}",
        "maxResultCount": min(max_results, 20),
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": _FIELD_MASK,
    }

    response = requests.post(_TEXTSEARCH_URL, json=payload, headers=headers, timeout=10)
    response.raise_for_status()

    places = response.json().get("places", [])

    results: List[Dict[str, Any]] = []
    for place in places:
        website_raw = place.get("websiteUri")
        if not website_raw:
            continue

        domain = _HTTPS_PREFIX.sub("", website_raw).rstrip("/")
        title = place.get("displayName", {}).get("text", "")
        snippet = place.get("editorialSummary", {}).get("text", "")

        results.append({"title": title, "website": domain, "snippet": snippet})

    return results
