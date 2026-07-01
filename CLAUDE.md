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
| `agents/planner.py` | ✅ Completo | Routing determinista, no requiere LLM |
| `agents/lead_finder.py` | ✅ Funcional con mocks | Los mocks están claramente marcados — reemplazar con `integrations/` |
| `agents/copywriter.py` | ✅ Completo | Async, usa Gemini 2.5 Pro, fallback sin API key |
| `integrations/google_maps.py` | ⬜ Stub | Implementar llamadas reales a Places API |
| `integrations/hunter.py` | ✅ Completo | `find_public_contact()` (scraping, 0 créditos) + `enrich_with_hunter()` (API real) |
| `integrations/apollo.py` | 🗄 Deprecado | Reemplazado por Hunter.io — conservado como referencia histórica |
| `integrations/hubspot.py` | ⬜ Stub | Push de leads calificados al CRM |
| `tests/test_pipeline.py` | ⬜ Stub | Tests unitarios por nodo + test end-to-end |

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
GOOGLE_MAPS_API_KEY=...   # integrations/google_maps.py
HUNTER_API_KEY=...        # integrations/hunter.py  (25 req/mes gratis)
HUBSPOT_ACCESS_TOKEN=...  # integrations/hubspot.py
```

**Nota:** Apollo.io fue reemplazado por Hunter.io (1 jul 2026).
Razones: tier gratuito (25 Email Finder/mes vs Apollo $49+/mes),
endpoint más simple (domain + first_name + last_name → email),
y estrategia "Zero Cost" que protege créditos con scraping previo.

Sin estas claves el sistema corre en modo mock (ver `copywriter.py` línea ~60
y los mocks en `agents/lead_finder.py`).

## Cómo conectar las integraciones reales

En `agents/lead_finder.py`, reemplazar las dos funciones mock:

```python
# Antes (mock en agents/lead_finder.py):
raw_results = _search_google_maps(criteria.industry, criteria.region)
hunter_result = _enrich_mock(domain)

# Después (real):
from integrations.google_maps import search_companies
# Hunter ya está importado directamente en lead_finder.py:
# from integrations.hunter import find_public_contact, enrich_with_hunter, split_name
# No se requiere cambio de import — basta con definir HUNTER_API_KEY en .env

raw_results = search_companies(criteria.industry, criteria.region)
```

Los contratos de entrada/salida están definidos en `integrations/hunter.py` y
`integrations/google_maps.py` — respetarlos garantiza zero cambios en la lógica
de `lead_finder.py`.

## Siguiente tarea prioritaria
Implementar `integrations/google_maps.py`:
- Función `search_companies(industry, region) -> List[Dict]`
- 2 llamadas a Places API: `textsearch` → `place_details` (para obtener `website`)
- Documentación de referencia: https://developers.google.com/maps/documentation/places/web-service/text-search
