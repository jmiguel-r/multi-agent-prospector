"""
state.py — Modelos de datos del sistema multi-agente.
Define el contrato de datos entre todos los nodos del grafo.
"""
from typing import TypedDict, List, Dict, Annotated, Optional, Literal
from operator import add
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# INPUT SCHEMA — Validado por Pydantic en el borde del sistema
# ---------------------------------------------------------------------------

class LeadGenerationTarget(BaseModel):
    """Briefing de prospección que el usuario entrega al sistema."""

    # Obligatorios
    industry: str = Field(
        ..., description="Sector industrial (ej. 'metalmecánica', 'inyección de plástico')."
    )
    region: str = Field(
        ..., description="Ubicación geográfica (ej. 'Querétaro', 'Bajío')."
    )
    pain_point: str = Field(
        ..., description="Problema a resolver (ej. 'automatización de soldadura')."
    )

    # Opcionales con defaults sensatos
    company_size_category: Literal["Micro", "Pequeña", "Mediana", "Gran Empresa", "Cualquiera"] = Field(
        default="Cualquiera"
    )
    min_employees: int = Field(default=10)
    max_employees: int = Field(default=250)
    exclusion_keywords: list[str] = Field(default_factory=list)
    output_type: Literal["report_only", "outreach_only", "both"] = Field(
        default="both",
        description="Qué debe producir el sistema."
    )


# ---------------------------------------------------------------------------
# INTERNAL DATA MODEL — Un lead calificado con enriquecimiento en cascada
# ---------------------------------------------------------------------------

class LeadInfo(TypedDict):
    company_name: str
    website: str
    estimated_employees: int           # fuente: Apollo headcount
    detected_signals: str              # fuente: Google Maps snippet + señales
    # Enriquecimiento Maps → Apollo → LinkedIn
    contact_name: Optional[str]        # "Ing. Carlos Mendoza" (Apollo)
    contact_role: Optional[str]        # "Gerente de Planta" (Apollo)
    contact_email: Optional[str]       # email directo del tomador de decisión (Apollo)
    linkedin_profile: Optional[str]    # URL perfil LinkedIn (Apollo)


# ---------------------------------------------------------------------------
# GRAPH STATE — Contrato de estado compartido entre todos los nodos
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    # 1. Input (inmutable durante la ejecución)
    target_criteria: LeadGenerationTarget

    # 2. Control del Planner (Supervisor)
    next_step: str                            # "lead_finder" | "copywriter" | "END"
    plan_logs: Annotated[list[str], add]      # auditoría de cada decisión

    # 3. Datos compartidos entre agentes
    leads: Annotated[List[LeadInfo], add]     # Lead Finder acumula aquí
    outreach_drafts: Dict[str, str]           # Copywriter escribe aquí (company → mensaje)

    # 4. Control de errores y límites
    search_attempts: int                      # guarda contra loop infinito
    error_message: Optional[str]


# ---------------------------------------------------------------------------
# PLANNER OUTPUT — Structured output del LLM (enum constrained)
# ---------------------------------------------------------------------------

class PlannerDecision(BaseModel):
    next: Literal["lead_finder", "copywriter", "END"]
    reasoning: str  # se añade a plan_logs
