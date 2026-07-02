"""
tests/test_pipeline.py — Tests del pipeline multi-agente

Cubre:
    1. Validación del input schema (LeadGenerationTarget)
    2. Lógica de routing del Planner (todos los casos de output_type)
    3. Filtro de calidad del Lead Finder (con y sin contacto)
    4. Test end-to-end del grafo completo (modo mock, sin API keys)
"""
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from state import LeadGenerationTarget, AgentState, LeadInfo
from planner import planner_node, MAX_SEARCH_ATTEMPTS
from lead_finder import lead_finder_node
from main import build_graph

_MOCK_MAPS_RESULTS = [
    {
        "title":   "Metalúrgica El Marqués S.A.",
        "website": "metalurgicamarques.mx",
        "snippet": "Taller de soldadura MIG/TIG y estampado progresivo. "
                   "25 años en El Marqués, Querétaro.",
    },
    {
        "title":   "Maquinados Industriales del Bajío",
        "website": "maquinadosbajio.com",
        "snippet": "Fresado CNC y torno manual. "
                   "Fabricación de refacciones para sector automotriz.",
    },
    {
        "title":   "Aceros y Ensambles del Centro S.C.",
        "website": "aceroscen.mx",
        "snippet": "Ensamble estructural y pintura electrostática.",
    },
]


# ---------------------------------------------------------------------------
# Fixture — Lead de muestra para tests de Planner
# ---------------------------------------------------------------------------

_SAMPLE_LEAD: LeadInfo = {
    "company_name":        "Empresa Test S.A.",
    "website":             "https://empresa-test.mx",
    "estimated_employees": 50,
    "detected_signals":    "Fabricación de partes metálicas",
    "contact_name":        "Juan García",
    "contact_role":        "Director de Operaciones",
    "contact_email":       "jgarcia@empresa-test.mx",
    "linkedin_profile":    None,
}


def _base_initial_state(output_type: str = "both") -> AgentState:
    criteria = LeadGenerationTarget(
        industry="manufactura metalmecánica",
        region="Querétaro",
        pain_point="automatización de procesos",
        output_type=output_type,
    )
    return {
        "target_criteria":  criteria,
        "next_step":        "",
        "plan_logs":        [],
        "leads":            [],
        "outreach_drafts":  {},
        "search_attempts":  0,
        "error_message":    None,
    }


# ---------------------------------------------------------------------------
# 1. INPUT SCHEMA
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_valid_input_all_required_fields(self):
        t = LeadGenerationTarget(
            industry="manufactura",
            region="Querétaro",
            pain_point="automatización",
        )
        assert t.industry == "manufactura"
        assert t.region == "Querétaro"
        assert t.pain_point == "automatización"

    def test_missing_required_field_raises_validation_error(self):
        with pytest.raises(ValidationError):
            LeadGenerationTarget(region="Querétaro", pain_point="automatización")  # falta industry

    def test_default_output_type_is_both(self):
        t = LeadGenerationTarget(
            industry="manufactura",
            region="Querétaro",
            pain_point="automatización",
        )
        assert t.output_type == "both"

    def test_invalid_output_type_raises_error(self):
        with pytest.raises(ValidationError):
            LeadGenerationTarget(
                industry="manufactura",
                region="Querétaro",
                pain_point="automatización",
                output_type="invalid_value",
            )


# ---------------------------------------------------------------------------
# 2. PLANNER ROUTING
# ---------------------------------------------------------------------------

class TestPlannerRouting:

    def _make_state(self, leads=None, outreach_drafts=None, output_type="both", attempts=0):
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
        result = planner_node(self._make_state(leads=[], output_type="both"))
        assert result["next_step"] == "lead_finder"

    def test_both_leads_ready_routes_to_copywriter(self):
        result = planner_node(self._make_state(
            leads=[_SAMPLE_LEAD], outreach_drafts={}, output_type="both"
        ))
        assert result["next_step"] == "copywriter"

    def test_both_complete_routes_to_end(self):
        result = planner_node(self._make_state(
            leads=[_SAMPLE_LEAD],
            outreach_drafts={"Empresa Test S.A.": "Hola Juan..."},
            output_type="both",
        ))
        assert result["next_step"] == "END"

    def test_report_only_leads_empty_routes_to_lead_finder(self):
        result = planner_node(self._make_state(leads=[], output_type="report_only"))
        assert result["next_step"] == "lead_finder"

    def test_report_only_leads_ready_routes_to_end(self):
        result = planner_node(self._make_state(leads=[_SAMPLE_LEAD], output_type="report_only"))
        assert result["next_step"] == "END"

    def test_outreach_only_drafts_empty_routes_to_copywriter(self):
        result = planner_node(self._make_state(outreach_drafts={}, output_type="outreach_only"))
        assert result["next_step"] == "copywriter"

    def test_anti_loop_max_attempts_routes_to_end(self):
        result = planner_node(self._make_state(leads=[], attempts=MAX_SEARCH_ATTEMPTS))
        assert result["next_step"] == "END"


# ---------------------------------------------------------------------------
# 3. LEAD FINDER — Filtro de calidad
# ---------------------------------------------------------------------------

class TestLeadFinderQualityFilter:

    @pytest.fixture(autouse=True)
    def patch_maps(self, monkeypatch):
        monkeypatch.setattr("lead_finder.search_companies", lambda *a, **kw: _MOCK_MAPS_RESULTS)

    def _make_state(self):
        return _base_initial_state("both")

    def test_lead_with_email_is_included(self):
        result = lead_finder_node(self._make_state())
        company_names = [l["company_name"] for l in result["leads"]]
        assert "Metalúrgica El Marqués S.A." in company_names

    def test_lead_without_email_or_linkedin_is_discarded(self):
        result = lead_finder_node(self._make_state())
        company_names = [l["company_name"] for l in result["leads"]]
        assert "Aceros y Ensambles del Centro S.C." not in company_names

    def test_search_attempts_increments(self):
        state = self._make_state()
        state["search_attempts"] = 0
        result = lead_finder_node(state)
        assert result["search_attempts"] == 1


# ---------------------------------------------------------------------------
# 4. END-TO-END (modo mock, sin API keys)
# ---------------------------------------------------------------------------

class TestPipelineEndToEnd:

    @pytest.fixture(autouse=True)
    def patch_maps(self, monkeypatch):
        monkeypatch.setattr("lead_finder.search_companies", lambda *a, **kw: _MOCK_MAPS_RESULTS)

    @pytest.mark.asyncio
    async def test_full_pipeline_both_output_type(self):
        """Pipeline completo: 2 leads, 2 drafts, 3 decisiones del Planner."""
        app = build_graph()
        final_state = await app.ainvoke(_base_initial_state("both"))

        assert len(final_state["leads"]) == 2
        assert len(final_state["outreach_drafts"]) == 2
        assert len(final_state["plan_logs"]) == 3  # lead_finder → copywriter → END

    @pytest.mark.asyncio
    async def test_pipeline_report_only_skips_copywriter(self):
        """Con report_only el Copywriter nunca corre: outreach_drafts debe quedar vacío."""
        app = build_graph()
        final_state = await app.ainvoke(_base_initial_state("report_only"))

        assert len(final_state["leads"]) == 2
        assert final_state["outreach_drafts"] == {}

    @pytest.mark.asyncio
    async def test_pipeline_no_leads_terminates_gracefully(self):
        """Si Lead Finder no encuentra nada en MAX intentos, el pipeline termina sin loop."""
        call_count = 0

        def mock_lead_finder(state):
            nonlocal call_count
            call_count += 1
            return {"leads": [], "search_attempts": call_count}

        with patch("main.lead_finder_node", side_effect=mock_lead_finder):
            app = build_graph()
            final_state = await app.ainvoke(_base_initial_state("both"))

        assert final_state["leads"] == []
        assert call_count == MAX_SEARCH_ATTEMPTS
        assert final_state.get("error_message") is not None
