"""
Project-wide helper utilities for
✅ CLI override handling
✅ Output-path resolution
✅ Lightweight type/structure safety

All pipeline modules are expected to:

    >>> from utils.cli_utils import apply_cli_overrides, resolve_output_path
    >>> cfg = apply_cli_overrides(cfg, overrides=args.set)   # --set key=value [...]
    >>> output_file = resolve_output_path(cfg['outputs']['foo'], cfg.overwrite_policy)

This file purposefully contains **zero** third-party dependencies beyond the
standard library + PyYAML (already used in utils.config).  It is therefore
safe to import in any execution environment (scripts, tests, CI).

Author: Pipeline-Core Team · 2025-06
"""

from __future__ import annotations
import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Sequence, Union

import yaml  # PyYAML – already required by utils.config
from utils.logging_utils import get_rotating_logger

_LOG = logging.getLogger(__name__)
LOGGER = logging.getLogger("overwrite_policy")

# --------------------------------------------------------------------------- #
# Generic helpers
# --------------------------------------------------------------------------- #
def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _set_dotted(cfg: Dict[str, Any], dotted_key: str, value: Any) -> None:
    """Create nested keys on‐the‐fly and set the final value."""
    keys = dotted_key.split(".")
    target = cfg
    for key in keys[:-1]:
        if key not in target or not isinstance(target[key], dict):
            target[key] = {}
        target = target[key]
    target[keys[-1]] = value


def _get_base_outputs_dir(cfg: Dict[str, Any]) -> Path | None:
    outputs = cfg.get("outputs", {})
    if isinstance(outputs, dict):
        base = outputs.get("dir")
        if base:
            return Path(base).expanduser().resolve()
    return None


# --------------------------------------------------------------------------- #
# 🔑  Pydantic-safe CLI override merge
# --------------------------------------------------------------------------- #
def apply_cli_overrides(
    cfg,                          # Pydantic BaseModel *or* plain dict
    overrides: Sequence[str] | None = None,
):
    """
    Merge dotted KEY=VALUE overrides into `cfg`.

    * Works with Pydantic v1/v2 or plain nested dicts.
    * Returns the **same type** as provided (BaseModel or dict).
    """
    if not overrides:
        return cfg

    if hasattr(cfg, "model_dump"):          # Pydantic v2
        raw_dict = cfg.model_dump(mode="python")
    elif hasattr(cfg, "dict"):              # Pydantic v1
        raw_dict = cfg.dict()
    else:                                   # Already a dict
        raw_dict = cfg

    merged = yaml.safe_load(yaml.safe_dump(raw_dict))  # deep copy via YAML

    for raw in overrides:
        if "=" not in raw:
            raise ValueError(f"--set override must be KEY=VALUE (got '{raw}')")
        dotted_key, raw_val = raw.split("=", 1)
        try:
            parsed_val = yaml.safe_load(raw_val)
        except Exception:
            parsed_val = raw_val
        _LOG.debug("CLI override: %s = %r", dotted_key, parsed_val)
        _set_dotted(merged, dotted_key, parsed_val)

    if not isinstance(cfg, dict):
        return cfg.__class__(**merged)      # type: ignore[arg-type]
    return merged


# ----------------------------------------------------------------------------
# Logger used by overwrite-policy tests
# ----------------------------------------------------------------------------
LOGGER = logging.getLogger("overwrite_policy")

# ----------------------------------------------------------------------------
# Overwrite-policy resolver
# ----------------------------------------------------------------------------
def resolve_output_path(path: Union[str, Path], policy: str) -> Path:
    """Return absolute path, enforcing overwrite-policy (`force|warn|error`)."""
    path = Path(os.path.expandvars(os.path.expanduser(str(path)))).resolve()
    policy = policy.strip().lower()

    if path.exists():
        if policy == "error":
            raise FileExistsError(f"{path} already exists and overwrite policy = error")
        if policy == "warn":
            LOGGER.warning("%s already exists — overwriting (policy=warn)", path)
        elif policy != "force":
            raise ValueError(f"Invalid overwrite policy: {policy}")
    return path


# --------------------------------------------------------------------------- #
# Parse --set flags from arbitrary argv list
# --------------------------------------------------------------------------- #
def extract_set_overrides(argv: List[str] | None = None) -> List[str]:
    argv = argv or sys.argv[1:]
    overrides: List[str] = []
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--set":
            if idx + 1 >= len(argv):
                raise ValueError("--set flag provided without KEY=VALUE")
            overrides.append(argv[idx + 1])
            idx += 2
        elif token.startswith("--set="):
            overrides.append(token[len("--set="):])
            idx += 1
        else:
            idx += 1
    return overrides


# --------------------------------------------------------------------------- #
# Simple helper: should we write a file, based on overwrite_policy?
# --------------------------------------------------------------------------- #
def handle_overwrite(output_path: str | Path, cfg: dict) -> bool:
    output_path = Path(output_path)
    policy = cfg.get("overwrite_policy", "error").strip().lower()

    if output_path.exists():
        if policy == "error":
            raise FileExistsError(f"{output_path} exists (overwrite_policy=error)")
        if policy == "warn":
            LOGGER.warning("%s exists — skipping (overwrite_policy=warn)", output_path)
            return False
        if policy == "force":
            LOGGER.info("%s exists — overwriting (overwrite_policy=force)", output_path)
            return True
        raise ValueError(f"Invalid overwrite_policy: {policy}")
    return True


# --------------------------------------------------------------------------- #
# ✅ Canonical CLI Parser for All Modules
# --------------------------------------------------------------------------- #
def parse_cli_args():
    parser = argparse.ArgumentParser(description="Pipeline CLI Entry")
    parser.add_argument("--config-path", type=str, default="config.yaml", help="Path to YAML config")
    parser.add_argument("--overwrite-policy", type=str, choices=["force", "warn", "error"], help="One-time overwrite behavior")
    parser.add_argument("--set", nargs="*", default=[], help="Override config values using dotted keys (e.g. pipeline.concurrency=2)")
    parser.add_argument("--modules", type=str, help="Comma-separated module list A,B,C,...")
    parser.add_argument("--start-from", type=str, help="Run modules from this point forward (inclusive)")
    parser.add_argument("--stop-after", type=str, help="Stop execution after this module (inclusive)")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of parallel workers")
    parser.add_argument("--continue-on-failure", action="store_true", help="Continue running if a module fails")
    parser.add_argument("--dry-run", action="store_true", help="Plan-only mode (don’t run modules)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (skip live calls)")
    return parser.parse_args()
