"""
integrations/hubspot.py — HubSpot CRM (Contacts + Notes)

Contrato público:
    push_leads_to_hubspot(leads, outreach_drafts) -> Dict[str, str]

Devuelve un dict {company_name: hubspot_contact_id} para trazabilidad.

Cuándo se llama:
    Al finalizar el pipeline (cuando Planner decide END con output_type="both"),
    main.py puede invocar esta función opcionalmente para registrar los leads
    en HubSpot y asociar el outreach_draft como nota del contacto.

Flujo de llamadas a HubSpot:
    1. POST /crm/v3/objects/contacts    → crear o actualizar contacto (email como key)
    2. POST /crm/v3/objects/notes       → crear nota con el outreach_draft
    3. POST /crm/v3/associations/...    → asociar nota al contacto

Documentación:
    https://developers.hubspot.com/docs/api/crm/contacts
    https://developers.hubspot.com/docs/api/crm/notes

Autenticación:
    Bearer token: HUBSPOT_ACCESS_TOKEN (Private App token, no OAuth)
    Header: { "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}" }

TODO para Claude Code:
    [ ] Implementar _upsert_contact(lead) -> str  (devuelve contact_id)
    [ ] Implementar _create_note(contact_id, message) -> str  (devuelve note_id)
    [ ] Implementar push_leads_to_hubspot() orquestando ambas llamadas por lead
    [ ] Manejar el caso de contacto duplicado (buscar por email antes de crear)
    [ ] Logging de errores por lead individual sin abortar el resto del batch
"""
import os
import requests
from typing import Dict, List, Any

HUBSPOT_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")
_BASE_URL     = "https://api.hubapi.com"
_HEADERS      = lambda: {
    "Authorization": f"Bearer {HUBSPOT_TOKEN}",
    "Content-Type":  "application/json",
}


def _upsert_contact(lead: Dict[str, Any]) -> str:
    """
    Crea o actualiza un contacto en HubSpot usando email como identificador único.

    Args:
        lead: LeadInfo dict con contact_email, contact_name, contact_role, company_name

    Returns:
        HubSpot contact_id (string)

    TODO: implementar con POST /crm/v3/objects/contacts
    """
    raise NotImplementedError(
        "Implementar _upsert_contact() con HubSpot Contacts API. "
        "Ver: https://developers.hubspot.com/docs/api/crm/contacts"
    )


def _create_note(contact_id: str, message: str, company_name: str) -> str:
    """
    Crea una nota en HubSpot con el outreach draft y la asocia al contacto.

    Args:
        contact_id:   ID del contacto HubSpot
        message:      Outreach draft generado por el Copywriter
        company_name: Para el título de la nota

    Returns:
        HubSpot note_id (string)

    TODO: implementar con POST /crm/v3/objects/notes +
          POST /crm/v3/associations/notes/contacts/batch/create
    """
    raise NotImplementedError(
        "Implementar _create_note() con HubSpot Notes API. "
        "Ver: https://developers.hubspot.com/docs/api/crm/notes"
    )


def push_leads_to_hubspot(
    leads: List[Dict[str, Any]],
    outreach_drafts: Dict[str, str],
) -> Dict[str, str]:
    """
    Registra todos los leads calificados en HubSpot con su outreach draft como nota.

    Args:
        leads:           Lista de LeadInfo dicts (del AgentState)
        outreach_drafts: Dict company_name → mensaje (del AgentState)

    Returns:
        Dict {company_name: hubspot_contact_id} para trazabilidad

    Solo procesa leads que tienen contact_email (requerido por HubSpot como
    identificador único de contacto).

    TODO: implementar llamando a _upsert_contact() y _create_note() por cada lead
    """
    raise NotImplementedError(
        "Implementar push_leads_to_hubspot() orquestando upsert + note por lead."
    )
