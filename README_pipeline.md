# 🧬 Module J — `pipeline.py`  
**MLB Player-Performance Prediction Pipeline Orchestrator**

---

## 🎯 Purpose  
`pipeline.py` is the **execution hub** for the modular MLB Player-Performance Prediction pipeline. It intelligently coordinates Modules **A → L**, enforces config policies, handles concurrency, and ensures reproducible, fault-tolerant runs across environments.

---

## ⚙️ CLI Flags & Config Keys  

| **Flag**                     | **Description**                                                   |
|-----------------------------|-------------------------------------------------------------------|
| `--config-path <file>`      | YAML config location (default: `config.yaml`)                     |
| `--overwrite-policy`        | One-time policy override: `force`, `warn`, `error`                |
| `--set key=value`           | Dotted YAML override (repeatable)                                 |
| `--modules A,B,...`         | Restrict run to specified modules                                 |
| `--start-from <MODULE>`     | Skip preceding modules                                            |
| `--stop-after <MODULE>`     | Stop after this module                                            |
| `--concurrency <N>`         | Run up to `N` modules in parallel                                 |
| `--continue-on-failure`     | Proceed with later modules even if some fail                      |
| `--dry-run`                 | Show plan, do not execute                                         |
| `--debug`                   | Enable verbose output                                             |

---

## 🧾 Logging Behavior  

- Rotating log: `logs/pipeline_<timestamp>.log`
- Log entries:
  - Parsed config, CLI flags, overrides
  - Module execution order
  - Execution time per module
  - Failures (traceback or subprocess return code)
  - Completion summary

---

## 🔁 Module Execution Logic  

- **Default Order:** `A → B → C → ... → L`
- **Custom Runs:** via `--modules`, `--start-from`, `--stop-after`
- **Parallelization:**
  - Modules run concurrently via `ThreadPoolExecutor` if `--concurrency > 1`
  - Each module attempts direct import; falls back to subprocess on failure or incompatibility

---

## 🧪 Output Behavior  

- `pipeline.py` does not write any datasets
- Produces real-time stdout + log output
- Terminal + log summary table:
  ```bash
  📊 Pipeline Summary:
   - Module A: ✅ SUCCESS
   - Module B: ⚠️  SKIPPED
   - Module C: ❌ FAILED
  ```
- Optional structured output (e.g., `pipeline_summary_YYYYMMDD.json`)

---

## 🚀 Example Usage  

```bash
python pipeline.py \
  --config-path config/prod.yaml \
  --modules A,B,C,D,E,F,G,H,I,J,K,L \
  --concurrency 4 \
  --overwrite-policy warn \
  --continue-on-failure
```

---

## ✅ Implementation Checklist  

- [x] YAML config parsing + CLI override support  
- [x] Enforces overwrite policy hierarchy  
- [x] Dry-run mode functional  
- [x] Threaded execution verified  
- [x] Subprocess fallback works on bad import  
- [x] Robust logging: CLI, config, results  
- [x] Edge-case unit tests (`test_pipeline.py`)  
- [x] Graceful failure handling + reporting  

---

## 🧠 Development Protocol  

> All work must reflect **production-grade discipline**:

1. **Justify every decision.**  
2. **Validate every assumption.**  
3. **Anticipate failure modes.**  
4. **Write testable, composable logic.**  
5. **Document uncertainties or TODOs.**  
6. **Summarize outcomes cleanly in logs + CLI.**

No shortcuts. No hallucinations. Only rigor.

