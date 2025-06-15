"""
IO-level helpers for the MLB pipeline.

⏩  This thin wrapper simply re-exports:
    • resolve_output_path  – from utils.cli_utils
    • ensure_dir           – from utils.logging_utils

Keeping this alias module lets legacy code import
`utils.io_utils` without duplicating logic.
"""

from pathlib import Path
from utils.cli_utils import resolve_output_path  # path + overwrite-policy helper
from utils.logging_utils import ensure_dir       # safe directory creation

# Optional local shorthand wrappers (identical signatures)
def resolve_output_path_shim(path: str | Path, policy: str) -> Path:
    """
    Backwards-compatibility shim so older code that imported
    `utils.io_utils.resolve_output_path` continues to work.
    """
    return resolve_output_path(path, policy)


def ensure_dir_shim(path: str | Path):
    """
    Alias to the canonical ensure_dir from logging_utils.
    """
    ensure_dir(Path(path))
