import os
import re
import sys
import requests
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

# ==================== CONFIGURABLE SECTION ====================

PROJECT_ROOT = Path(__file__).resolve().parent
FILE_EXTS = {".py", ".yaml", ".yml", ".md", ".txt"}
FUZZY_THRESHOLD = 0.74
EXCLUDE_DIRS = {"venv_mlb", "venv", ".git", "logs", "outputs", "__pycache__", "tests"}

# ---- LLM SETTINGS ----
LLM_ENDPOINT = "http://localhost:11434/v1/chat/completions"  # DeepSeek or Llama3 via Ollama
LLM_MODEL = "deepseek-coder"  # Or "llama3", or "deepseek-coder:6.7b", etc
LLM_API_KEY = None            # Only needed for hosted API (OpenRouter, etc)

# ================ END CONFIGURABLE SECTION ====================

KEY_PATTERNS = [
    re.compile(r'cfg[.\[]["\']?([a-zA-Z0-9_]+)["\']?'),
    re.compile(r'config[.\[]["\']?([a-zA-Z0-9_]+)["\']?'),
    re.compile(r'outputs[.\[]["\']?([a-zA-Z0-9_]+)["\']?'),
    re.compile(r'inputs[.\[]["\']?([a-zA-Z0-9_]+)["\']?'),
    re.compile(r'llm[.\[]["\']?([a-zA-Z0-9_]+)["\']?'),
    re.compile(r'^\s*([a-zA-Z0-9_]+)\s*:', re.MULTILINE),
    re.compile(r'["\']([^\s"\']+\.(?:csv|parquet|txt|md|yaml|yml|json|log))["\']')
]
PY_ID_PATTERN = re.compile(r'^(def|class)\s+([a-zA-Z_][a-zA-Z0-9_]*)|([a-zA-Z_][a-zA-Z0-9_]*)\s*=', re.MULTILINE)

found = defaultdict(set)
all_paths = defaultdict(set)
py_symbols = defaultdict(set)

for path in PROJECT_ROOT.rglob("*"):
    if not path.is_file():
        continue
    if any(part in EXCLUDE_DIRS for part in path.parts):
        continue
    if path.suffix not in FILE_EXTS:
        continue
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        continue

    for pat in KEY_PATTERNS:
        for m in pat.findall(text):
            for val in (m if isinstance(m, (tuple, list)) else [m]):
                val = val.strip()
                if val and 1 < len(val) < 64:
                    if val.endswith((".csv", ".parquet", ".txt", ".md", ".yaml", ".yml", ".json", ".log")):
                        all_paths[val].add(str(path))
                    else:
                        found[val.lower()].add(str(path))

    if path.suffix == ".py":
        for match in PY_ID_PATTERN.findall(text):
            symbol = match[1] or match[2]
            if symbol and 1 < len(symbol) < 64:
                py_symbols[symbol].add(str(path))

from collections import defaultdict

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio() > FUZZY_THRESHOLD

def fast_make_clusters(names):
    buckets = defaultdict(list)
    for name in names:
        key = (len(name), name[0])
        buckets[key].append(name)

    clusters = []
    used = set()
    for bucket in buckets.values():
        for i, n1 in enumerate(bucket):
            if n1 in used:
                continue
            cluster = {n1}
            for n2 in bucket[i+1:]:
                if n2 in used:
                    continue
                if similar(n1, n2):
                    cluster.add(n2)
                    used.add(n2)
            used.add(n1)
            if len(cluster) > 1:
                clusters.append(cluster)
    return clusters

clusters = fast_make_clusters(found.keys() | all_paths.keys())

def print_heading(title):
    print("\n" + "="*min(len(title), 80))
    print(title)
    print("="*min(len(title), 80) + "\n")

print_heading("NOMENCLATURE & ARTIFACT CONSISTENCY AUDIT REPORT")

print_heading("1. Fuzzy-Matched Naming/Path Clusters (Potential Synonyms/Drift)")
with open("nomenclature_clusters.md", "w", encoding="utf-8") as cluster_file:
    cluster_file.write("# Naming & Artifact Cluster Summary\n\n")
    for group in clusters:
        cluster_line = f"- {' | '.join(sorted(group))}\n"
        print(cluster_line, end="")
        cluster_file.write(cluster_line)
        for name in group:
            sources = sorted(found.get(name, set()) | all_paths.get(name, set()))
            for f in sources:
                source_line = f"    ↳ {name} in {f}\n"
                print(source_line, end="")
                cluster_file.write(source_line)
        print("-" * 60)
        cluster_file.write("-" * 60 + "\n")

print_heading("2. All Unique Key/Path/Config Terms Found")
for name, files in sorted(found.items()):
    print(f"{name:40} | {len(files):2} files")
    for f in sorted(files):
        print(f"    ↳ {f}")

print_heading("3. All Data/Output File Paths Found")
for pth, files in sorted(all_paths.items()):
    print(f"{pth:50} | {len(files):2} files")
    for f in sorted(files):
        print(f"    ↳ {f}")

print_heading("4. All Python Function/Class/Variable Names")
for sym, files in sorted(py_symbols.items()):
    print(f"{sym:40} | {len(files):2} files")
    for f in sorted(files):
        print(f"    ↳ {f}")

print_heading("5. Recommendations & Action Items")
print("- Review each cluster for unintentional synonyms (e.g. outputs.dir vs outputs.root, context_features vs context_features_base).")
print("- Canonicalize each concept: pick ONE spelling, update everywhere.")
print("- Consider adding a constants.py for artifact names/keys.")
print("- Regenerate this audit after every big refactor or config change.")

print("\n🏁 Audit complete. Review above for drift or naming risks.\n")

# LLM Section: Query DeepSeek with clusters report for recommendations

def query_llm_with_clusters(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        audit_text = f.read()

    # --- REFINED PROMPT: FORCE USE OF REAL PROJECT NAMES ---
    prompt = f"""
You are a world-class ML pipeline codebase reviewer and refactoring expert.
Below is a summary of **actual naming clusters from my codebase**. Each cluster contains variable, config key, or artifact names that appear to represent the same concept but are spelled differently in different files.

Your job:
1. For each cluster, choose and recommend the single best canonical name, using the *real* names shown (do NOT use generic, placeholder, or example names).
2. For each current name in each cluster, write a concrete Python refactor script to rename ALL occurrences of the old name to the canonical name everywhere in the codebase.
   - For variables, config keys, and function names: use Python with `fileinput` and regex, or shell `sed` if you prefer.
   - For filenames or directory names: use Python `os.rename` or `Path.rename`.
3. Write a Markdown table:
   - Cluster
   - All current names in the cluster (as they appear in my files)
   - Canonical name (must be from the actual names, not invented)
   - Python or bash code block for refactoring *using only these real names*
   - Any warning if a name is dangerously ambiguous or could cause a bug
4. End with a TODO checklist for the refactor.
5. ***Absolutely do NOT use any made-up names or URLs. Only use the names exactly as they appear below.***

Below are my real project naming clusters:

{audit_text}
"""

    headers = {}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a meticulous, expert codebase refactorer."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    print("⏳ Querying DeepSeek LLM for naming recommendations...\n")

    resp = requests.post(LLM_ENDPOINT, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    response_content = resp.json()
    llm_reply = response_content["choices"][0]["message"]["content"]
    print(llm_reply)

    with open("naming_llm_advice.md", "w", encoding="utf-8") as out:
        out.write(llm_reply)
    print("\n✅ LLM recommendations written to naming_llm_advice.md")

# If clusters found, query LLM for advice!
if clusters:
    query_llm_with_clusters("nomenclature_clusters.md")
    sys.exit(1)
else:
    sys.exit(0)
