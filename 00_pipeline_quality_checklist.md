# 📋 `pipeline.py` – **Master QA & Engineering Checklist**  
*(Project: MLB Player-Performance Prediction Pipeline — **REBOOT: No files audited yet**)*

### 🔧 Purpose  
This document defines the **non-negotiable engineering and QA criteria** for `pipeline.py`, the primary orchestrator of your MLB pipeline. It also tracks audit status for every module **from a clean slate**.

---

## ✅ 1. `pipeline.py` – REQUIRED FINAL CONDITIONS

| Requirement                      | Description                                                                                             | Status |
|----------------------------------|---------------------------------------------------------------------------------------------------------|--------|
| `load_config()` used             | All configuration is loaded via central **`utils/config.py::load_config()`**                           | ❌ |
| No hard-coded paths / magic nums | All file paths & constants live in **`config.yaml`** or global constants                               | ❌ |
| Rotating logging in place        | Use **`utils/logging_utils.py::build_rotating_logger()`**                                              | ❌ |
| Pydantic validation enforced     | Config must validate against a **Pydantic `BaseModel`**                                                | ❌ |
| CLI overrides functional         | CLI args processed via **`argparse` + `apply_cli_overrides()`**                                        | ❌ |
| Correct module sequence          | Submodules run in canonical order (data → features → model → output)                                   | ❌ |
| Idempotency guaranteed           | Re-runs never corrupt outputs or pipeline state                                                        | ❌ |
| Pytest hooks embedded            | Key logic covered by unit tests discoverable by **`pytest`**                                           | ❌ |

---

## 🧩 2. Module Audit Tracker *(all modules = **Pending**)*

| Filename                            | Module Name                    | Module Type | Audit Status |
|-------------------------------------|--------------------------------|-------------|--------------|
| `fetch_starters_api.py`             | E — Fetch Starters             | Core        | ❌ Pending |
| `fetch_true_lines_pinnacle_api.py`  | F — Fetch True Lines           | Core        | ❌ Pending |
| `pipeline.py`                       | J — Orchestrator               | Core        | ❌ Pending |
| `filter_input_data.py`              | F — Filter Data                | Core        | ❌ Pending |
| `consolidate_mlb_data.py`           | G — Consolidate Data           | Core        | ❌ Pending |
| `generate_mlb_context_features.py`  | H — Feature Generation         | Core        | ❌ Pending |
| `download_static_csvs.py`           | C — Static Data Downloader     | Core        | ❌ Pending |
| `fetch_recent_gamelogs_statsapi.py` | A2 — Gamestats via API         | Core        | ❌ Pending |
| `fetch_mlb_gamelogs.py`             | A1 — Historical Gamestats      | Core        | ❌ Pending |
| `combine_predictions.py`            | I — Combine Predictions        | Core        | ❌ Pending |
| `run_mlb_model.py`                  | I — Run Predictive Model       | Core        | ❌ Pending |
| `llm_ensemble_predict.py`           | K — LLM Betting Lines          | Core        | ❌ Pending |
| `global_conventions.py`             | Utility — Logger / Guards      | Utility     | ❌ Pending |
| `common_utils.py`                   | Utility — Shared Helpers       | Utility     | ❌ Pending |
| `utils/config.py`                   | Utility — Config Loader        | Utility     | ❌ Pending |
| `utils/column_aliases.py`           | Utility — Column Mapping       | Utility     | ❌ Pending |

---

## 🛠 3. Git Identity Setup

```bash
git config --global user.name  "Luke Arney"
git config --global user.email "aal.arney@gmail.com"




**⚠️ Attention:**
You must approach this task with **extreme attention to detail, rigorous analytical thinking, and meticulous verification** at every step.

1. **Explicit Step-by-Step Reasoning** – justify every choice.  
2. **Continuous Internal Validation** – check consistency & correctness throughout.  
3. **Proactive Error Prevention** – anticipate and mitigate edge cases.  
4. **Comprehensive Cross-Verification** – prove the output meets all specs.  
5. **Transparency of Uncertainty** – flag any assumptions or missing info.  
6. **Structured Summary** – finish with what you did, confidence level, and next steps.

Do **not** hallucinate or rely on guesses. Deliver **production-grade accuracy** only.
