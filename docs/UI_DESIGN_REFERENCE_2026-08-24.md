# v0.4 UI design reference — 2026-08-24

This note records the public GitHub projects reviewed before the v0.4 Streamlit workspace redesign. The goal is to borrow durable information-architecture patterns, not copy assets, CSS, branding, or implementation code.

## Reference projects

Star counts are a point-in-time snapshot from GitHub on 2026-08-24.

| Project | Approx. stars | Why it is relevant | Pattern adopted |
| --- | ---: | --- | --- |
| `langflow-ai/langflow` | 153.6k | Agent/workflow product with a strong workbench mental model | Keep the workflow visible as compact status stages while moving detailed engineering state out of the main decision view |
| `langgenius/dify` | 153.4k | Agent + RAG + workflow platform with strong workspace hierarchy and observability | One primary task entry, modular result workspaces, clear separation between user-facing output and runtime/observability detail |
| `open-webui/open-webui` | 149.8k | Mature AI interface optimized for low-friction use and progressive disclosure | Reduce front-page chrome, keep the main view sparse, hide diagnostics until explicitly opened, preserve responsive layout |
| `AI4Finance-Foundation/FinGPT` | 21.1k | High-star financial AI project | Put financial/risk semantics and explainability ahead of engineering implementation detail |

## Problems in the previous Streamlit layout

1. Seven pipeline tabs plus roadmap and diagnostics produced a wide engineering navigation bar rather than a product workspace.
2. IPO profile, risk status, pipeline state and Final Supervisor were repeated in multiple places.
3. Raw JSON and engineering metadata were too close to the primary decision path.
4. Evidence existed, but users had to scan large expanders rather than progressively drill from conclusion → Evidence → Calculation → metadata.
5. The interface looked like a validation harness even when running a real governed case.

## Adopted workspace architecture

The new presentation shell uses six stable workspaces:

1. **Overview** — case identity, domain coverage, risk inventory and governed pipeline.
2. **Risks & Evidence** — Financial / Legal / Business risk cards with progressive Evidence and Calculation drill-down.
3. **Market & Model** — governed Market-X, explicit missingness, frozen model signal when available, deterministic rule signal.
4. **Supervisor & Report** — Final Supervisor synthesis, preserved conflicts, 13-section report and downloads.
5. **Roadmap** — CH-1 through CH-6 presentation slots, all explicitly marked planned until governed outputs exist.
6. **System** — component modes, stage limitations, provenance, governance, structured errors and Agent logs.

The landing page keeps only the primary analysis form. A real result then renders:

`Case identity → executive snapshot → four channel states → workspace tabs`

The seven formal v0.4 stages remain visible as a compact progress strip and in System diagnostics, so visual simplification does not remove governance information.

## Non-negotiable UI rules

- The presentation layer never manufactures a market value, model score, SHAP driver, Evidence reference, risk or completion claim.
- Unavailable and disabled channels remain visibly unavailable/disabled.
- Rule scores are never labelled as probabilities or return forecasts.
- Missing Market-X values remain explicit rather than zero-filled.
- CH-* roadmap cards are placeholders only until governed implementations land.
- `IPOAnalysisService` remains the sole runtime entry point used by Streamlit.
