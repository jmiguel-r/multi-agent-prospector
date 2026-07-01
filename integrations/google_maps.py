"""
integrations/google_maps.py — Google Maps Places API

Contrato público:
    search_companies(industry, region, max_results) -> List[Dict]

Cada Dict devuelto tiene la forma:
    {
        "title":   str,   # nombre de la empresa
        "website": str,   # dominio (sin https://)
        "snippet": str,   # descripción del lugar
    }

Este contrato es idéntico al mock `_search_google_maps()` en agents/lead_finder.py.
Reemplazar el import allí para activar la integración real.

Flujo de llamadas a la API:
    1. textsearch  → obtiene place_id de cada resultado
    2. place_details → obtiene website, name, editorial_summary por place_id

Documentación:
    https://developers.google.com/maps/documentation/places/web-service/text-search
    https://developers.google.com/maps/documentation/places/web-service/details

TODO para Claude Code:
    [ ] Implementar _textsearch(query) -> List[str]  (devuelve place_ids)
    [ ] Implementar _place_details(place_id) -> Dict  (devuelve name, website, snippet)
    [ ] Implementar search_companies() llamando a ambas en secuencia
    [ ] Manejar el caso donde place_details no devuelve "website" (campo opcional en Maps)
    [ ] Respetar rate limits: 1 QPS en el tier básico de Places API
"""
import os
import requests
from typing import List, Dict, Any

MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
_TEXTSEARCH_URL  = "https://maps.googleapis.com/maps/api/place/textsearch/json"
_DETAILS_URL     = "https://maps.googleapis.com/maps/api/place/details/json"
_DETAILS_FIELDS  = "name,website,editorial_summary"


def _textsearch(query: str) -> List[str]:
    """
    Busca lugares en Google Maps y devuelve sus place_ids.

    Args:
        query: Ej. "manufactura metalmecánica Querétaro"

    Returns:
        Lista de place_ids (strings)

    TODO: implementar
    """
    raise NotImplementedError(
        "Implementar llamada a Places API textsearch. "
        "Ver: https://developers.google.com/maps/documentation/places/web-service/text-search"
    )


def _place_details(place_id: str) -> Dict[str, Any]:
    """
    Obtiene detalles de un lugar a partir de su place_id.
    Campos solicitados: name, website, editorial_summary.

    Args:
        place_id: ID devuelto por textsearch

    Returns:
        Dict con keys: name (str), website (str | None), snippet (str)

    TODO: implementar
    """
    raise NotImplementedError(
        "Implementar llamada a Places API place_details. "
        "Ver: https://developers.google.com/maps/documentation/places/web-service/details"
    )


def search_companies(
    industry: str,
    region: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    Busca empresas físicas de una industria en una región usando Google Maps.

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
        max_results: Máximo de empresas a devolver

    Returns:
        Lista de dicts con title, website, snippet.
        Empresas sin website son descartadas (no se pueden enriquecer con Apollo).

    TODO: implementar llamando a _textsearch() y _place_details()
    """
    raise NotImplementedError(
        "Implementar search_companies() orquestando _textsearch() → _place_details()."
    )
