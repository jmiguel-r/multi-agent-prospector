# Multi-Agent B2B Prospector — AIO Strategy
> **Bootcamp agai-04 · Project 3: Multi-Agent Research & Task Automation System**  
> Instructor: Satyajit Pattnaik | Cohort: May–July 2026

A production-grade multi-agent AI system that automates B2B prospecting for manufacturing SMBs in Mexico's Bajío region. Given a natural-language brief, the system finds qualified leads, enriches them with decision-maker contact data, and generates personalized cold outreach using a consultative sales technique called **Contextual Relevance** — making it feel less like a pitch, more like an engineer noticing an inefficiency in your plant.

---

## Architecture

The system follows a **pure Supervisor pattern** built on LangGraph: a Planner Agent acts as the single decision-maker, routing work to specialized sub-agents and receiving control back after each step. No agent ever routes directly to another.

```
User Brief (LeadGenerationTarget)
         │
         ▼
   ┌─────────────┐
   │   PLANNER   │  ← Single point of control
   │  (Supervisor)│    Reads state → decides next step
   └──────┬──────┘    Logs every decision to plan_logs
          │
    ┌─────┴──────┐
    │            │
    ▼            ▼
┌──────────┐  ┌───────────┐
│   LEAD   │  │COPYWRITER │
│  FINDER  │  │  AGENT    │
└────┬─────┘  └─────┬─────┘
     │               │
     └───────┬───────┘
             │ (always returns to Planner)
             ▼
          [END]
```

### Enrichment Pipeline (Lead Finder)
```
[Google Maps API] ──▶ Physical company + website domain
                              │
                              ▼
[Apollo.io API]   ──▶ Decision-maker: name, role, direct email
                              │
                              ▼
[LinkedIn URL]    ──▶ Profile URL saved for structured outreach
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Orchestration | LangGraph `StateGraph` | Native support for cyclic state graphs with reducers |
| Input validation | Pydantic `BaseModel` | Type safety + auto-documentation at system boundary |
| State management | `TypedDict` + `Annotated[List, add]` | Accumulation-safe reducer for multi-pass lead collection |
| Routing | Deterministic Python (Supervisor pattern) | Zero-latency control flow; LLM reserved for generative tasks |
| Copy generation | Gemini 2.5 Pro (async) | Superior linguistic reasoning for "engineer-to-engineer" tone |
| Concurrency | `asyncio.gather` | O(1) latency regardless of lead count — all Gemini calls in parallel |

---

## Project Structure

```
multi_agent_prospector/
├── main.py           # Entry point — graph builder + invocation
├── state.py          # Data contracts: LeadGenerationTarget, LeadInfo, AgentState
├── planner.py        # Supervisor node — deterministic routing logic
├── lead_finder.py    # Lead Finder node — Maps + Apollo + LinkedIn pipeline
├── copywriter.py     # Copywriter node — async Gemini generation
└── requirements.txt
```

---

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set environment variables (optional — system runs in mock mode without them)
```bash
export GEMINI_API_KEY="your-key-here"
# Production extensions:
# export GOOGLE_MAPS_API_KEY="..."
# export APOLLO_API_KEY="..."
```

### 3. Run
```bash
python main.py
```

If `GEMINI_API_KEY` is not set, the Copywriter falls back to a deterministic template — the full agent pipeline still executes and all routing/enrichment logic is demonstrated.

---

## Example Output

```
============================================================
   MULTI-AGENT PROSPECTOR — AIO Strategy
   Domain: Manufactura metalmecánica, Querétaro
============================================================

--- PLANNER NODE ---
  Planner → lead_finder | leads empty (attempt 1) → search companies.
--- LEAD FINDER NODE (Maps + Apollo + LinkedIn) ---
  ✓ Qualified: Metalúrgica El Marqués S.A. → Ing. Carlos Mendoza
  ✓ Qualified: Maquinados Industriales del Bajío → Alejandro Ruiz Torres
  ✗ Discarded (no contact found): Aceros y Ensambles del Centro S.C.
--- PLANNER NODE ---
  Planner → copywriter | 2 leads ready, outreach_drafts empty → generate copy.
--- COPYWRITER NODE (concurrent processing) ---
  2 messages generated.
--- PLANNER NODE ---
  Planner → END | 2 leads and 2 drafts complete → END.

AUDIT LOG:
  [1] output_type=both, leads empty (attempt 1) → search companies.
  [2] output_type=both, 2 lead(s) ready, outreach_drafts empty → generate copy.
  [3] output_type=both, 2 lead(s) and 2 draft(s) complete → END.
```

---

## Key Design Decisions

**Why LangGraph over CrewAI?**  
State accumulates across iterations (`leads` list grows with each Lead Finder pass). LangGraph's `Annotated` reducer pattern handles this natively. CrewAI's YAML-defined static task flow cannot model a pipeline where the Planner may need to re-run the Lead Finder if results are insufficient.

**Why separate `outreach_drafts: Dict` from `leads: List[LeadInfo]`?**  
`leads` uses an `add` reducer (accumulation semantics). The Copywriter *updates* existing records rather than *appending* new ones — if it wrote back into `leads`, LangGraph would duplicate every lead. A separate dict field with no reducer (replace semantics) resolves the conflict cleanly.

**Why deterministic Planner instead of LLM routing?**  
The routing logic is fully expressible as a decision tree. Non-determinism should be isolated to tasks that require it (natural language generation in the Copywriter). Using an LLM for `if/else` routing would add latency, token cost, and failure modes with no benefit.

**Loop-infinity protection:**  
`search_attempts` counter in the State caps Lead Finder execution at `MAX_SEARCH_ATTEMPTS = 3`. If no leads are found after 3 passes, the Planner writes to `error_message` and routes to `END` gracefully.

---

## Planned Extensions

- Replace mock APIs with real Google Maps Places + Apollo.io calls
- Add HubSpot MCP integration — push qualified leads directly to CRM on END
- Add Gmail/Lemlist integration — schedule outreach send from `outreach_drafts`
- Streamlit UI — single-page interface matching the "Tuesday" pattern from class
- Qualifier Agent — filter leads by ICP score before reaching Copywriter

---

## Author

**JMiguel Ramírez** — AI Engineer / AIO Strategy  
GitHub: [github.com/jmiguel-r](https://github.com/jmiguel-r)
