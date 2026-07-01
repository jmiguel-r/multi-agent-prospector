"""
integrations/hunter.py — Hunter.io Email Finder API

Contrato público:
    enrich_with_hunter(domain, first_name, last_name) -> Dict
    find_public_contact(domain) -> str | None  (Pre-Hunter, zero créditos)

Estrategia "Zero Cost" (Defensa de Créditos):
    1. find_public_contact()  — scraping básico del sitio web / snippet de Maps.
       Si encuentra un correo público (contacto@, info@, gerencia@...) lo usa
       directamente. Costo: 0 créditos de Hunter.
    2. enrich_with_hunter()   — solo si el lead está calificado Y no hay correo
       público. Costo: 1 crédito del tier gratuito de Hunter (25/mes en free tier).

Documentación Hunter.io:
    https://hunter.io/api-documentation/v2#email-finder

Tier gratuito: 25 Email Finder requests / mes.
"""
import os
import re
import requests
from typing import Dict, Any, Optional

HUNTER_API_KEY   = os.getenv("HUNTER_API_KEY")
_EMAIL_FINDER_URL = "https://api.hunter.io/v2/email-finder"
_DOMAIN_SEARCH_URL = "https://api.hunter.io/v2/domain-search"

# Patrones de correo genérico que no valen para outreach personalizado
_GENERIC_PREFIXES = {"contacto", "info", "ventas", "admin", "hola", "soporte", "contact"}


# ---------------------------------------------------------------------------
# PASO 1 — Pre-Hunter: buscar correo público sin gastar créditos
# ---------------------------------------------------------------------------

def find_public_contact(domain: str, snippet: str = "") -> Optional[str]:
    """
    Intenta encontrar un correo de contacto directo sin llamar a Hunter.

    Estrategias (en orden de costo cero):
    1. Extraer emails del snippet de Google Maps (texto ya disponible).
    2. Hacer un GET al sitio web y buscar emails en el HTML.
    3. Probar patrones comunes: contacto@domain, info@domain, gerencia@domain.

    Args:
        domain:  Dominio de la empresa (ej. "metalurgicamarques.mx")
        snippet: Texto descriptivo del snippet de Google Maps (ya disponible, costo 0)

    Returns:
        Email encontrado, o None si no hay correo público fácil de extraer.
        Los correos genéricos (info@, contacto@) se devuelven como fallback —
        el Copywriter los puede usar aunque no sean del tomador de decisión.
    """
    email_pattern = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

    # Estrategia 1: buscar en el snippet de Maps (gratis, ya lo tenemos)
    if snippet:
        matches = email_pattern.findall(snippet)
        if matches:
            return matches[0]

    # Estrategia 2: GET al sitio web y extraer emails del HTML
    try:
        resp = requests.get(f"https://{domain}", timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            emails = email_pattern.findall(resp.text)
            # Filtrar emails de terceros (gmail, hotmail, etc.)
            own_emails = [e for e in emails if domain.split(".")[0] in e]
            if own_emails:
                return own_emails[0]
    except Exception:
        pass  # Sitio caído o sin email visible en HTML

    return None


# ---------------------------------------------------------------------------
# PASO 2 — Hunter Email Finder (solo si el lead califica y no hay correo público)
# ---------------------------------------------------------------------------

def enrich_with_hunter(
    domain: str,
    first_name: str,
    last_name: str,
) -> Dict[str, Any]:
    """
    Consulta la API oficial de Hunter.io para encontrar el correo corporativo
    de un tomador de decisión específico.

    Documentación: https://hunter.io/api-documentation/v2#email-finder

    Args:
        domain:     Dominio de la empresa (ej. "metalurgicamarques.mx")
        first_name: Nombre del contacto  (ej. "Carlos")
        last_name:  Apellido del contacto (ej. "Mendoza")

    Returns:
        {
            "email":      str | None,  # correo encontrado
            "confidence": int,         # score 0-100 (usar solo si >= 70)
            "linkedin":   str | None,  # perfil LinkedIn si Hunter lo extrae
        }
    """
    api_key = os.getenv("HUNTER_API_KEY")
    url = (
        f"{_EMAIL_FINDER_URL}"
        f"?domain={domain}"
        f"&first_name={first_name}"
        f"&last_name={last_name}"
        f"&api_key={api_key}"
    )

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json().get("data", {})
            return {
                "email":      data.get("email"),
                "confidence": data.get("score", 0),
                "linkedin":   data.get("linkedin"),
            }
        if response.status_code == 429:
            print("Hunter.io: límite de créditos alcanzado (429). Usando None.")
    except Exception as e:
        print(f"Error de conexión con Hunter.io: {e}")

    return {"email": None, "confidence": 0, "linkedin": None}


# ---------------------------------------------------------------------------
# HELPER — Dividir nombre completo en first/last para Hunter
# ---------------------------------------------------------------------------

def split_name(full_name: str) -> tuple[str, str]:
    """
    Divide un nombre completo en first_name y last_name para Hunter.

    Maneja prefijos comunes en México: "Ing.", "Lic.", "Dr.", "M.C.", etc.

    Examples:
        "Ing. Carlos Mendoza Torres" → ("Carlos", "Mendoza Torres")
        "Alejandro Ruiz"             → ("Alejandro", "Ruiz")
    """
    PREFIXES = {"ing.", "lic.", "dr.", "dra.", "m.c.", "mtro.", "mtra.", "c."}
    parts = full_name.strip().split()
    # Eliminar prefijo profesional si existe
    if parts and parts[0].lower() in PREFIXES:
        parts = parts[1:]
    if not parts:
        return ("", "")
    first = parts[0]
    last  = " ".join(parts[1:]) if len(parts) > 1 else ""
    return first, last
