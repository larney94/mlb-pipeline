"""
Project-wide helper utilities for
✅ CLI override handling
✅ Output-path resolution
✅ Lightweight type/structure safety

All pipeline modules are expected to:

    >>> from utils.cli_utils import apply_cli_overrides, resolve_output_path
    >>> cfg = apply_cli_overrides(cfg, overrides=args.set)          # --set key=value [...]
    >>> output_file = resolve_output_path(cfg['outputs']['foo'], cfg)

This file purposefully contains **zero** third-party dependencies beyond the
standard library + `PyYAML` (already used in utils.config).  It is therefore
safe to import in any execution environment (scripts, tests, CI).

Author: Pipeline-Core Team · 2025-06
"""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

from typing import Dict, Any, List, Sequence, Union
from utils.logging_utils import get_rotating_logger


import yaml  # PyYAML – already required by utils.config

_LOG = logging.getLogger(__name__)
LOGGER = get_rotating_logger("cli_utils")


# --------------------------------------------------------------------------- #
# Helper: dotted-path set/get for nested dicts
# --------------------------------------------------------------------------- #
def _set_dotted(cfg: Dict[str, Any], dotted_key: str, value: Any) -> None:
    """Set `cfg["a"]["b"]["c"] = value` given 'a.b.c'."""
    keys = dotted_key.split(".")
    target = cfg
    for key in keys[:-1]:
        if key not in target or not isinstance(target[key], dict):
            target[key] = {}
        target = target[key]
    target[keys[-1]] = value


def _get_base_outputs_dir(cfg: Dict[str, Any]) -> Path | None:
    # Optional helper – spec says outputs.dir is the catch-all base
    outputs = cfg.get("outputs", {})
    if isinstance(outputs, dict):
        base = outputs.get("dir")
        if base:
            return Path(base).expanduser().resolve()
    return None


# --------------------------------------------------------------------------- #
# Public helpers
# --------------------------------------------------------------------------- #
def apply_cli_overrides(
    cfg: Dict[str, Any],
    overrides: Sequence[str] | None = None,
) -> Dict[str, Any]:
    """
    Merge `--set KEY=VALUE` CLI options into a *copy* of the loaded config.

    Parameters
    ----------
    cfg : dict
        Parsed YAML config (already validated by utils.config.load_config).
    overrides : Sequence[str] | None
        Typically `args.set` from your CLI parser, each item in form `a.b.c=value`.

    Returns
    -------
    dict
        Mutated *copy* of the input config containing overrides.

    Notes
    -----
    • Values are parsed with `yaml.safe_load` so that `"123"` → int(123),
      `"true"` → bool(True), etc., matching YAML typing rules.
    • Invalid `KEY=VALUE` strings raise `ValueError`.
    """
    if not overrides:
        return cfg

    merged = yaml.safe_load(yaml.safe_dump(cfg))  # deep copy via yaml round-trip

    for raw in overrides:
        if "=" not in raw:
            raise ValueError(f"--set override must be KEY=VALUE (got '{raw}')")
        dotted_key, raw_val = raw.split("=", 1)
        try:
            parsed_val = yaml.safe_load(raw_val)
        except Exception:  # pragma: no cover
            parsed_val = raw_val  # fall back to string
        _LOG.debug("CLI override: %s = %r", dotted_key, parsed_val)
        _set_dotted(merged, dotted_key, parsed_val)

    return merged


def resolve_output_path(
    maybe_path: Union[str, os.PathLike],
    cfg: Dict[str, Any],
    create_dir: bool = True,
) -> Path:
    """
    Resolve an output path relative to `cfg['outputs']['dir']`
    (if given and `maybe_path` is not already absolute).

    Examples
    --------
    >>> resolve_output_path('gamelogs', cfg)
    PosixPath('/abs/path/to/outputs/gamelogs')

    • Expands `~` and environment variables.
    • Ensures parent directory exists when `create_dir=True`.
    """
    path = Path(os.path.expandvars(os.path.expanduser(str(maybe_path))))
    if not path.is_absolute():
        base = _get_base_outputs_dir(cfg)
        if base:
            path = base / path
    path = path.resolve()
    if create_dir:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path



# --------------------------------------------------------------------------- #
# Convenience: parse --set from argv for scripts without Typer/Click
# --------------------------------------------------------------------------- #
def extract_set_overrides(argv: List[str] | None = None) -> List[str]:
    """
    Utility to pull all occurrences of `--set KEY=VALUE` from raw `sys.argv`.

    Returns list of just the "KEY=VALUE" components.
    """
    argv = argv or sys.argv[1:]
    overrides: List[str] = []
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--set":
            try:
                overrides.append(argv[idx + 1])
            except IndexError:
                raise ValueError("--set flag provided without following KEY=VALUE")
            idx += 2
        elif token.startswith("--set="):  # support GNU style
            overrides.append(token[len("--set=") :])
            idx += 1
        else:
            idx += 1
    return overrides


# --------------------------------------------------------------------------- #
# Overwrite policy logic — used across all modules
# --------------------------------------------------------------------------- #
def handle_overwrite(output_path: str | Path, cfg: dict) -> bool:
    """
    Returns True if the file can be written based on the overwrite policy.
    - error → raise FileExistsError
    - warn  → skip and log warning
    - force → allow overwrite
    """
    output_path = Path(output_path)
    policy = cfg.get("overwrite_policy", "error")

    if output_path.exists():
        if policy == "error":
            raise FileExistsError(f"{output_path} exists and overwrite_policy=error")
        elif policy == "warn":
            LOGGER.warning(f"{output_path} exists — skipping due to overwrite_policy=warn")
            return False
        elif policy == "force":
            LOGGER.info(f"{output_path} exists — overwriting due to overwrite_policy=force")
            return True
        else:
            raise ValueError(f"Invalid overwrite_policy: {policy}")
    return True

