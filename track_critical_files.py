import os
from pathlib import Path
from typing import Set

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR
MANIFEST_FILE = BASE_DIR / "critical_files.txt"

# Filters for extra files
EXCLUDE_DIRS = {
    "venv_mlb", "venv", ".git", "__pycache__",
    "logs", "outputs", "tests", "templates", ".ipynb_checkpoints"
}

EXCLUDE_FILES = {
    ".gitignore", "README_pipeline.md", "requirements.txt", "requirements-freeze.txt",
    "pytest.ini", "track_critical_files.py", "test_output.txt",
    "config.yaml", "critical_files.txt", "__init__.py"
}

EXCLUDE_EXTENSIONS = {".pdf", ".zip", ".md", ".txt"}


def load_manifest() -> Set[str]:
    """Load list of critical files from manifest file."""
    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Missing manifest file: {MANIFEST_FILE}")
    with open(MANIFEST_FILE, "r") as f:
        return {
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        }


def scan_project(root: Path) -> Set[str]:
    """Scan the repo and return all files not excluded by rule."""
    found = set()
    for path in root.rglob("*"):
        if path.is_file():
            rel_path = path.relative_to(root).as_posix()
            parts = path.relative_to(root).parts

            if any(part in EXCLUDE_DIRS for part in parts):
                continue
            if rel_path in EXCLUDE_FILES:
                continue
            if Path(rel_path).suffix in EXCLUDE_EXTENSIONS:
                continue

            found.add(rel_path)
    return found


def main():
    expected = load_manifest()
    actual = scan_project(PROJECT_ROOT)

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    if missing:
        print("❌ Missing critical files:")
        for f in missing:
            print(f"  - {f}")

    if extra:
        print("⚠️ Extra files found (untracked by manifest):")
        for f in extra:
            print(f"  - {f}")

    if not missing and not extra:
        print("✅ All critical files are present and accounted for.")

    if missing:
        exit(1)


if __name__ == "__main__":
    main()
