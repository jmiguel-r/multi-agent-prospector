"""
integrations/hubspot.py — HubSpot CRM (Contacts + Notes)

Contrato público:
    push_leads_to_hubspot(leads, outreach_drafts) -> Dict[str, str]

Devuelve un dict {company_name: hubspot_contact_id} para trazabilidad.

Cuándo se llama:
    Al finalizar el pipeline (cuando Planner decide END con output_type="both"),
    app.py invoca esta función para registrar los leads en HubSpot y asociar
    el outreach_draft como nota del contacto.

Flujo de llamadas a HubSpot por cada lead:
    1. POST /crm/v3/objects/contacts    → crea el contacto (email como key)
       Si 409 (ya existe) → POST /crm/v3/objects/contacts/search para obtener el ID
    2. POST /crm/v3/objects/notes       → crea nota con el outreach_draft
       (la asociación al contacto se incluye inline en el body de creación)

Documentación:
    https://developers.hubspot.com/docs/api/crm/contacts
    https://developers.hubspot.com/docs/api/crm/notes

Autenticación:
    Bearer token: HUBSPOT_ACCESS_TOKEN (Private App token, no OAuth)
"""
import os
import datetime
import requests
from typing import Dict, List, Any

_BASE_URL = "https://api.hubapi.com"

# associationTypeId 202 = note → contact (HUBSPOT_DEFINED)
_NOTE_TO_CONTACT_TYPE = {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {os.getenv('HUBSPOT_ACCESS_TOKEN', '')}",
        "Content-Type": "application/json",
    }


def _upsert_contact(lead: Dict[str, Any]) -> str:
    """
    Crea o actualiza un contacto en HubSpot usando email como identificador único.

    Returns:
        HubSpot contact_id (string)

    Raises:
        requests.HTTPError: En errores de API distintos de 409.
    """
    name_parts = (lead.get("contact_name") or "").split(" ", 1)
    properties = {
        "email":         lead.get("contact_email", ""),
        "firstname":     name_parts[0] if name_parts else "",
        "lastname":      name_parts[1] if len(name_parts) > 1 else "",
        "jobtitle":      lead.get("contact_role") or "",
        "company":       lead.get("company_name") or "",
        "website":       lead.get("website") or "",
        "hs_lead_status": "NEW",
    }

    resp = requests.post(
        f"{_BASE_URL}/crm/v3/objects/contacts",
        json={"properties": properties},
        headers=_headers(),
        timeout=10,
    )

    if resp.status_code == 201:
        return resp.json()["id"]

    # 409 = contacto ya existe — buscar por email y devolver el ID
    if resp.status_code == 409:
        search = requests.post(
            f"{_BASE_URL}/crm/v3/objects/contacts/search",
            json={
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator":     "EQ",
                        "value":        lead.get("contact_email", ""),
                    }]
                }],
                "limit": 1,
            },
            headers=_headers(),
            timeout=10,
        )
        search.raise_for_status()
        results = search.json().get("results", [])
        if results:
            return results[0]["id"]

    resp.raise_for_status()
    return resp.json()["id"]  # unreachable, satisface type checker


def _create_note(contact_id: str, message: str, company_name: str) -> str:
    """
    Crea una nota con el outreach draft y la asocia inline al contacto.

    Returns:
        HubSpot note_id (string)
    """
    timestamp_ms = str(int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000))

    resp = requests.post(
        f"{_BASE_URL}/crm/v3/objects/notes",
        json={
            "properties": {
                "hs_note_body": f"[{company_name}] Outreach draft:\n\n{message}",
                "hs_timestamp": timestamp_ms,
            },
            "associations": [{
                "to":    {"id": contact_id},
                "types": [_NOTE_TO_CONTACT_TYPE],
            }],
        },
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


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
        Dict {company_name: hubspot_contact_id} para trazabilidad.
        Los leads que fallan se omiten del resultado pero no abortan el batch.

    Raises:
        EnvironmentError: Si HUBSPOT_ACCESS_TOKEN no está definida.
    """
    if not os.getenv("HUBSPOT_ACCESS_TOKEN"):
        raise EnvironmentError("HUBSPOT_ACCESS_TOKEN no está definida en el entorno.")

    pushed: Dict[str, str] = {}

    for lead in leads:
        company = lead.get("company_name", "")

        if not lead.get("contact_email"):
            print(f"  ⚠ HubSpot: {company} — sin email, omitido.")
            continue

        try:
            contact_id = _upsert_contact(lead)
            print(f"  ✓ HubSpot contacto: {company} → ID {contact_id}")

            draft = outreach_drafts.get(company)
            if draft:
                _create_note(contact_id, draft, company)
                print(f"  ✓ HubSpot nota asociada a {company}")

            pushed[company] = contact_id

        except Exception as exc:
            print(f"  ✗ HubSpot error en {company}: {exc}")

    return pushed
