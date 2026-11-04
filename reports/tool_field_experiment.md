# Tool use experiment: an optional search field inside the judgement

Before the planning step was added, the agent-driven retrieval variant gave the judge only the general clauses for the dispute reason and asked it to fill `search_policy` in its judgement if it needed more policy. No model did. These runs were stopped early and kept in `outputs/runs_discarded/` (not used for any reported accuracy).

| Run | Judge | Cases judged | Cases where the judge called search_policy |
|---|---|---|---|
| abl_llama3.1-8b_agentic (optional field) | `llama3.1:8b` | 40 | 0 |
| probe_gemini_agentic (optional field) | `gemini-flash-lite-latest` | 10 | 0 |

With a separate planning step (the current agent-driven design), the tool is used: see `model_comparison.md`.
