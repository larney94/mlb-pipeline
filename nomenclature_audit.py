import os
import re
import sys
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

# CONFIGURABLE
PROJECT_ROOT = Path(__file__).resolve().parent
FILE_EXTS = {".py", ".yaml", ".yml", ".md", ".txt"}
FUZZY_THRESHOLD = 0.74  # Similarity ratio for grouping names
EXCLUDE_DIRS = {"venv_mlb", "venv", ".git", "logs", "outputs", "__pycache__", "tests"}

# Patterns to extract keys, paths, CLI flags, etc.
KEY_PATTERNS = [
    # cfg.key, cfg['key'], cfg["key"], cfg.get('key')
    re.compile(r'cfg[.\[]["\']?([a-zA-Z0-9_]+)["\']?'),
    re.compile(r'config[.\[]["\']?([a-zA-Z0-9_]+)["\']?'),
    re.compile(r'outputs[.\[]["\']?([a-zA-Z0-9_]+)["\']?'),
    re.compile(r'inputs[.\[]["\']?([a-zA-Z0-9_]+)["\']?'),
    re.compile(r'llm[.\[]["\']?([a-zA-Z0-9_]+)["\']?'),
    # YAML: key: value
    re.compile(r'^\s*([a-zA-Z0-9_]+)\s*:', re.MULTILINE),
    # Any file path in code
    re.compile(r'["\']([^\s"\']+\.(?:csv|parquet|txt|md|yaml|yml|json|log))["\']')
]

# For variable/function/class names in Python
PY_ID_PATTERN = re.compile(r'^(def|class)\s+([a-zA-Z_][a-zA-Z0-9_]*)|([a-zA-Z_][a-zA-Z0-9_]*)\s*=', re.MULTILINE)

found = defaultdict(set)      # name/term -> set(files)
all_paths = defaultdict(set)  # path literal -> set(files)
py_symbols = defaultdict(set) # function/class/var -> set(files)

# ---- Scan all files ----
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

    # Keys, config accesses, etc.
    for pat in KEY_PATTERNS:
        for m in pat.findall(text):
            for val in (m if isinstance(m, (tuple, list)) else [m]):
                val = val.strip()
                if val and 1 < len(val) < 64:
                    if val.endswith((".csv", ".parquet", ".txt", ".md", ".yaml", ".yml", ".json", ".log")):
                        all_paths[val].add(str(path))
                    else:
                        found[val.lower()].add(str(path))

    # Python function/class/var names
    if path.suffix == ".py":
        for match in PY_ID_PATTERN.findall(text):
            symbol = match[1] or match[2]
            if symbol and 1 < len(symbol) < 64:
                py_symbols[symbol].add(str(path))

# ---- Fast Fuzzy Grouping ----
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

# ---- Report ----
def print_heading(title):
    print("\n" + "="*min(len(title), 80))
    print(title)
    print("="*min(len(title), 80) + "\n")

print_heading("NOMENCLATURE & ARTIFACT CONSISTENCY AUDIT REPORT")

print_heading("1. Fuzzy-Matched Naming/Path Clusters (Potential Synonyms/Drift)")
for group in clusters:
    print(f"• {', '.join(sorted(group))}")
    for name in group:
        sources = sorted(found.get(name, set()) | all_paths.get(name, set()))
        for f in sources:
            print(f"    ↳ {name} in {f}")
    print("-" * 60)

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

# Optional: exit nonzero if suspicious drift detected (for CI)
if clusters:
    print(f"⚠️  {len(clusters)} clusters of potentially duplicate/ambiguous names detected.")
    sys.exit(1)
else:
    sys.exit(0)
