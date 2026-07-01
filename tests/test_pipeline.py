"""
tests/test_pipeline.py — Tests del pipeline multi-agente

Cubre:
    1. Validación del input schema (LeadGenerationTarget)
    2. Lógica de routing del Planner (todos los casos de output_type)
    3. Filtro de calidad del Lead Finder (con y sin contacto Apollo)
    4. Test end-to-end del grafo completo (modo mock, sin API keys)

TODO para Claude Code:
    [ ] Implementar test_input_validation_*
    [ ] Implementar test_planner_routing_*
    [ ] Implementar test_lead_finder_quality_filter
    [ ] Implementar test_pipeline_end_to_end
    [ ] Implementar test_pipeline_no_leads_found (verifica anti-loop)
    [ ] Implementar test_pipeline_report_only y test_pipeline_outreach_only
"""
import pytest
import asyncio
from pydantic import ValidationError

from state import LeadGenerationTarget, AgentState
from planner import planner_node, MAX_SEARCH_ATTEMPTS


# ---------------------------------------------------------------------------
# 1. INPUT SCHEMA
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_valid_input_all_required_fields(self):
        """LeadGenerationTarget válido con todos los campos obligatorios."""
        # TODO: implementar
        raise NotImplementedError

    def test_missing_required_field_raises_validation_error(self):
        """Pydantic debe rechazar un input sin `industry`."""
        # TODO: implementar — LeadGenerationTarget(region="Querétaro", pain_point="...")
        raise NotImplementedError

    def test_default_output_type_is_both(self):
        """output_type default debe ser 'both'."""
        # TODO: implementar
        raise NotImplementedError

    def test_invalid_output_type_raises_error(self):
        """output_type con valor fuera del Literal debe fallar."""
        # TODO: implementar — output_type="invalid_value"
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 2. PLANNER ROUTING
# ---------------------------------------------------------------------------

class TestPlannerRouting:

    def _make_state(self, leads=None, outreach_drafts=None, output_type="both", attempts=0):
        """Helper: construye un AgentState mínimo para el Planner."""
        criteria = LeadGenerationTarget(
            industry="manufactura",
            region="Querétaro",
            pain_point="automatización",
            output_type=output_type,
        )
        return {
            "target_criteria":  criteria,
            "next_step":        "",
            "plan_logs":        [],
            "leads":            leads or [],
            "outreach_drafts":  outreach_drafts or {},
            "search_attempts":  attempts,
            "error_message":    None,
        }

    def test_both_empty_routes_to_lead_finder(self):
        """output_type=both, leads vacío → lead_finder"""
        # TODO: implementar
        raise NotImplementedError

    def test_both_leads_ready_routes_to_copywriter(self):
        """output_type=both, leads con datos, drafts vacíos → copywriter"""
        # TODO: implementar
        raise NotImplementedError

    def test_both_complete_routes_to_end(self):
        """output_type=both, leads y drafts completos → END"""
        # TODO: implementar
        raise NotImplementedError

    def test_report_only_leads_empty_routes_to_lead_finder(self):
        """output_type=report_only, leads vacío → lead_finder"""
        # TODO: implementar
        raise NotImplementedError

    def test_report_only_leads_ready_routes_to_end(self):
        """output_type=report_only, leads con datos → END (sin pasar por copywriter)"""
        # TODO: implementar
        raise NotImplementedError

    def test_outreach_only_drafts_empty_routes_to_copywriter(self):
        """output_type=outreach_only, drafts vacíos → copywriter (sin lead_finder)"""
        # TODO: implementar
        raise NotImplementedError

    def test_anti_loop_max_attempts_routes_to_end(self):
        """Si search_attempts >= MAX y leads vacío → END con error_message"""
        # TODO: implementar — attempts=MAX_SEARCH_ATTEMPTS, leads=[]
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 3. LEAD FINDER — Filtro de calidad
# ---------------------------------------------------------------------------

class TestLeadFinderQualityFilter:

    def test_lead_with_email_is_included(self):
        """Lead con contact_email debe incluirse en enriched_leads."""
        # TODO: implementar con lead_finder_node y state mock
        raise NotImplementedError

    def test_lead_without_email_or_linkedin_is_discarded(self):
        """Lead sin email ni linkedin_profile debe descartarse."""
        # TODO: implementar — verificar que aceroscen.mx no aparece en output
        raise NotImplementedError

    def test_search_attempts_increments(self):
        """lead_finder_node debe incrementar search_attempts en 1."""
        # TODO: implementar
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 4. END-TO-END (modo mock, sin API keys)
# ---------------------------------------------------------------------------

class TestPipelineEndToEnd:

    @pytest.mark.asyncio
    async def test_full_pipeline_both_output_type(self):
        """
        Pipeline completo con output_type=both.
        Verifica: 2 leads calificados, 2 outreach drafts, 3 entradas en plan_logs.
        """
        # TODO: implementar — usar build_graph() de main.py con ainvoke
        raise NotImplementedError

    @pytest.mark.asyncio
    async def test_pipeline_report_only_skips_copywriter(self):
        """
        Con output_type=report_only el Copywriter nunca debe ejecutarse.
        """
        # TODO: implementar — verificar que outreach_drafts permanece vacío
        raise NotImplementedError

    @pytest.mark.asyncio
    async def test_pipeline_no_leads_terminates_gracefully(self):
        """
        Si el Lead Finder no encuentra leads en MAX_SEARCH_ATTEMPTS intentos,
        el pipeline termina con error_message, sin loop infinito.
        """
        # TODO: implementar — mockear lead_finder para devolver [] siempre
        raise NotImplementedError
