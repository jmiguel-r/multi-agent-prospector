# CLAUDE.md — Multi-Agent B2B Prospector

## Qué es este proyecto
Sistema multi-agente construido con LangGraph que automatiza la prospección B2B
de PyMEs manufactureras en el Bajío (México) para AIO Strategy.

Dado un criterio de prospección, el sistema:
1. Encuentra empresas físicas en la región (Google Maps)
2. Enriquece cada empresa con el tomador de decisión (Hunter.io — estrategia Zero Cost)
3. Genera mensajes de outreach personalizados "ingeniero a ingeniero" (Gemini 2.5 Pro)

## Arquitectura — Patrón Supervisor Puro (LangGraph)
```
START → Planner → lead_finder → Planner → copywriter → Planner → END
```
El Planner es el ÚNICO punto de decisión. Ningún agente enruta directamente a otro.

## Estado actual de los archivos

| Archivo | Estado | Notas |
|---------|--------|-------|
| `state.py` | ✅ Completo | No modificar — es el contrato de datos de todo el sistema |
| `main.py` | ✅ Completo | Grafo ensamblado y probado end-to-end |
| `planner.py` | ✅ Completo | Routing determinista, no requiere LLM |
| `lead_finder.py` | ✅ Completo | Pipeline completo: Maps → CSE (LinkedIn) → Pre-Hunter → Hunter; solo `_enrich_mock()` como fallback sin API key |
| `copywriter.py` | ✅ Completo | Async, usa Gemini 2.5 Pro, fallback sin API key |
| `app.py` | ✅ Completo | Streamlit UI: tabla de leads, drafts editables, export a HubSpot |
| `integrations/google_maps.py` | ✅ Completo | Places API (New) — single POST, descarta resultados sin website |
| `integrations/hunter.py` | ✅ Completo | `find_public_contact()` (scraping, 0 créditos) + `enrich_with_hunter()` (API real) |
| `integrations/hubspot.py` | ✅ Completo | `push_leads_to_hubspot()`: upsert contacto + nota con draft; tolerante a fallos por lead |
| `integrations/apollo.py` | 🗄 Deprecado | Reemplazado por Hunter.io — conservado como referencia histórica |
| `tests/test_pipeline.py` | ✅ Completo | 17 tests verdes: validación, routing, filtro de calidad, e2e |

## Reglas de arquitectura — NO cambiar sin revisar el diseño

1. **Reducer de `leads`**: usa `Annotated[List[LeadInfo], add]` — acumulación entre
   iteraciones. Si el Copywriter necesita modificar leads existentes, NO devuelva
   la lista completa — usa `outreach_drafts` (campo separado, sin reducer).

2. **`outreach_drafts`**: sin `Annotated` — LangGraph reemplaza el campo completo
   en cada ejecución del Copywriter. Esto es intencional (el Copywriter genera
   todos los drafts en una sola pasada).

3. **Planner como single point of control**: nunca añadir aristas directas entre
   `lead_finder` y `copywriter`. Ambos siempre regresan al Planner.

4. **`copywriter_node` es `async def`**: el grafo se invoca con `app.ainvoke()`.
   No cambiar a `app.invoke()` o se rompe la concurrencia del Copywriter.

5. **Filtro de calidad en Lead Finder**: un lead se descarta si no tiene
   `contact_email` NI `linkedin_profile`. No bajar este umbral.

6. **Anti-loop**: `search_attempts` en el State + `MAX_SEARCH_ATTEMPTS = 3`
   en `planner.py`. Si Lead Finder no encuentra nada en 3 intentos, el Planner
   termina con `error_message`.

## Variables de entorno requeridas

```bash
GEMINI_API_KEY=...        # Copywriter — Gemini 2.5 Pro
GOOGLE_MAPS_API_KEY=...   # integrations/google_maps.py + _find_contact_name() en lead_finder.py
GOOGLE_CSE_ID=...         # lead_finder.py — Custom Search Engine ID (busca en LinkedIn)
HUNTER_API_KEY=...        # integrations/hunter.py  (25 req/mes gratis)
HUBSPOT_ACCESS_TOKEN=...  # integrations/hubspot.py
```

**Nota:** Apollo.io fue reemplazado por Hunter.io (1 jul 2026).
Razones: tier gratuito (25 Email Finder/mes vs Apollo $49+/mes),
endpoint más simple (domain + first_name + last_name → email),
y estrategia "Zero Cost" que protege créditos con scraping previo.

Sin estas claves el sistema degrada graciosamente:
- Sin `GOOGLE_CSE_ID`: `_find_contact_name()` devuelve `(None, None, None)` — el lead puede seguir calificando si Pre-Hunter encuentra un correo público.
- Sin `HUNTER_API_KEY`: se activa `_enrich_mock()` (fallback hard-coded para tests).
- Sin `GEMINI_API_KEY`: el Copywriter usa un template de fallback.

## Único mock restante

| Función | Propósito | Cuándo se activa |
|---------|-----------|-----------------|
| `_enrich_mock(domain)` en `lead_finder.py` | Simula respuesta de Hunter.io | Solo cuando `HUNTER_API_KEY` no está definida |

## Estado del pipeline — todo en producción

Todas las integraciones reales están implementadas y conectadas:

```
Google Maps Places API (New)
    ↓  empresas + dominio + snippet
Pre-Hunter scraping (find_public_contact)
    ↓  correo público si existe (0 créditos)
Google Custom Search → LinkedIn
    ↓  nombre, rol y perfil LinkedIn del tomador de decisión
Hunter.io Email Finder
    ↓  correo corporativo (1 crédito, solo si no hay correo público)
Filtro de calidad (email OR linkedin requerido)
    ↓
HubSpot CRM (upsert contacto + nota con outreach draft)
```
